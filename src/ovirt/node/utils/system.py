#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# system.py - Copyright (C) 2012 Red Hat, Inc.
# Written by Fabian Deutsch <fabiand@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.
"""
A module to access system wide stuff
e.g. services, reboot ...
"""

import logging
import os
import re
import shlex
import subprocess
import sys
import time
from contextlib import contextmanager

import rpm
import system_config_keyboard.keyboard

from ovirt.node import base, utils
from ovirt.node.utils import process, parse_varfile
from ovirt.node.utils.fs import File
from ovirt.node.utils.process import check_output, check_call


LOGGER = logging.getLogger(__name__)


def reboot():
    """Reboot the system
    """
    process.call(["reboot"])


def async_reboot(delay=3):
    reboot_task = Reboot()
    reboot_task.reboot(delay)


def poweroff():
    """Poweroff the system
    """
    process.call(["poweroff"])


def is_efi():
    """If the system is booted in (U)EFI mode
    """
    return os.path.exists("/sys/firmware/efi")


def mount_efi(target="/liveos/efi"):
    """Mount the EFI config partition
    """
    if os.path.ismount(target):
        return True
    if is_iscsi() or Filesystem.by_label("Boot"):
        efi_part = Filesystem.by_label("Boot").device
    else:
        efi_part = Filesystem.by_label("Root").device

    # Get the first partition on the disk
    efi_part = efi_part[:-1] + "1"

    if not os.path.exists(target):
        if not process.check_call(["mkdir", "-v", "-p", target]):
            LOGGER.exception("Unable to create mount target for EFI "
                             "partition")
            raise RuntimeError("Unable to create mount target for EFI "
                               "partition")
    Mount(target, efi_part, "vfat").mount()


def is_iscsi():
    """If the system is iSCSI
    """
    from ovirt.node.config import defaults

    if defaults.Installation().retrieve()["iscsi_install"]:
        return True


def is_pxe():
    """If the system is PXE booted
    """
    return "BOOTIF" in kernel_cmdline_arguments()


def is_python_2_6():
    """If the system is running on Python 2.6
    """
    return sys.version_info[:2] == (2, 6)


def is_min_el(minver):
    """Check if el and min version minver
    """
    return SystemRelease().is_min_el(minver)


def is_max_el(maxver):
    """Check if el and max version maxver
    """
    return SystemRelease().is_max_el(maxver)


def is_rescue_mode():
    """If the system is running in rescue mode
    """
    return any(arg in open("/proc/cmdline").read().split() for arg
               in ["rescue", "S", "single", "1"])


def is_reinstall(_c=None):
    """is the system is in reinstalling mode

    >>> is_reinstall("foo bar reinstall z")
    True
    >>> is_reinstall("foo bar reinstall=1 z")
    True
    >>> is_reinstall("foo bar reinstall=0 z")
    False

    >>> is_reinstall("foo bar firstboot")
    True
    >>> is_reinstall("foo bar firstboot=1 z")
    True
    >>> is_reinstall("foo bar firstboot=0 z")
    False

    We are also conservative, if contradiction assume False:

    >>> is_reinstall("reinstall=1 firstboot=0 z")
    False

    >>> is_reinstall("foo bar z")
    False
    """
    flags = ["firstboot", "reinstall"]
    cmdline = kernel_cmdline_arguments(_c)

    is_given = any(f in cmdline for f in flags)
    not_denies = all(cmdline.get(f, 1) != "0" for f in flags)

    return (is_given and not_denies)


def node_version():
    """Return the version of the ovirt-node package
    This is the package version at runtime
    """
    return RpmPackage("ovirt-node").nvr().version


def _parse_lscpu(data):
    """Parse the lines of the lscpu output

    >>> data = \"\"\"
    ... Architecture:          x86_64
    ... CPU op-mode(s):        32-bit, 64-bit
    ... Byte Order:            Little Endian
    ... CPU(s):                4
    ... On-line CPU(s) list:   0-3
    ... Thread(s) per core:    2
    ... Core(s) per socket:    2
    ... Socket(s):             1
    ... NUMA node(s):          1
    ... Vendor ID:             GenuineIntel
    ... CPU family:            6
    ... Model:                 42
    ... Model name:            Intel(R) Core(TM) i7-2620M CPU @ 2.70GHz
    ... Stepping:              7
    ... CPU MHz:               1094.976
    ... BogoMIPS:              5382.47
    ... Virtualization:        VT-x
    ... L1d cache:             32K
    ... L1i cache:             32K
    ... L2 cache:              256K
    ... L3 cache:              4096K
    ... NUMA node0 CPU(s):     0-3
    ... \"\"\"
    >>> _parse_lscpu(data)
    {'CPU(s)': '4', 'L1d cache': '32K', 'CPU op-mode(s)': '32-bit, 64-bit', \
'NUMA node0 CPU(s)': '0-3', 'L2 cache': '256K', 'L1i cache': '32K', \
'Model name': 'Intel(R) Core(TM) i7-2620M CPU @ 2.70GHz', 'CPU MHz': \
'1094.976', 'Core(s) per socket': '2', 'Thread(s) per core': '2', \
'On-line CPU(s) list': '0-3', 'Socket(s)': '1', 'Architecture': 'x86_64', \
'Model': '42', 'Vendor ID': 'GenuineIntel', 'CPU family': '6', 'L3 cache': \
'4096K', 'BogoMIPS': '5382.47', 'Virtualization': 'VT-x', 'Stepping': '7', \
'Byte Order': 'Little Endian', 'NUMA node(s)': '1'}
    """
    cpu = {}
    for line in data.splitlines():
        if not line.strip():
            continue
        k, v = line.split(":", 1)
        cpu[k.strip()] = v.strip()
    return cpu


def cpu_details():
    """Return details for the CPU of this machine
    """
    fields = ["Model name", "Architecture", "CPU MHz", "Virtualization",
              "CPU(s)", "Socket(s)",
              "Core(s) per socket", "Thread(s) per core"]

    data = process.pipe(["lscpu"])
    cpu = _parse_lscpu(data)

    # Fallback for some values
    cpuinfo = _parse_lscpu(File("/proc/cpuinfo").read())
    cpu["Model name"] = \
        cpu.get("Model name", "") or cpuinfo.get("model name", "")

    cpu_details = ("%s: %s" % (f, cpu.get(f, "(Unknown)")) for f in fields)

    return "\n".join(cpu_details)


def has_hostvg():
    """Determine if a HostVG is present on this system (indicates an existing
    installation)
    """
    return os.path.exists("/dev/HostVG")


def kernel_cmdline_arguments(cmdline=None):
    """Return the arguments of the currently booted kernel
    """
    cmdline = cmdline or File("/proc/cmdline").read()
    return _parse_cmdline_args(cmdline)


def _parse_cmdline_args(cmdline):
    """Parse the cmdline like we do it in the initfunctions

    >>> sorted_args = lambda txt: sorted(_parse_cmdline_args(txt).items())
    >>> sorted_args("a=1 b=2 c")
    [('a', '1'), ('b', '2'), ('c', 'c')]
    >>> sorted_args("a=1=2")
    [('a', '1=2')]
    >>> sorted_args("rd.lvm.lv=foo/bar")
    [('rd.lvm.lv', 'foo/bar')]
    >>> sorted_args("title='foo bar'")
    [('title', 'foo bar')]
    >>> sorted_args("a")
    [('a', 'a')]
    """
    args_list = shlex.split(cmdline)
    args = {}

    for arg in args_list:
        key = value = arg
        if "=" in arg:
            key, value = arg.split("=", 1)
        args[key] = value

    return args


def which(cmd):
    """Simulates the behavior of which

    Args:
        cmd: The cmd to be found in PATH

    Returns:
        The cmd with the absolute path if it was found in any path given in
        $PATH. Otherwise None (if not found in any path in $PATHS).
    """
    ret = None
    if os.path.isabs(cmd):
        if File(cmd).exists():
            ret = cmd
    else:
        for dirname in os.environ["PATH"].split(":"):
            fn = os.path.join(dirname, cmd)
            if File(fn).exists() and File(fn).access(os.X_OK):
                ret = fn
                break
    return ret


def service(name, cmd, do_raise=True):
    """Convenience wrapper to handle service interactions
    """
    try:
        kwargs = {"shell": False,
                  "stderr": process.PIPE}
        r = process.check_output(["service", name, cmd], **kwargs)
    except process.CalledProcessError as e:
        r = e.returncode
        LOGGER.debug("Service cmd failed: %s %s" % (name, cmd), exc_info=True)
        LOGGER.debug("Service output: %s" % e.output)
        if do_raise:
            raise
    return r


def has_systemd():
    """Determine if the system has systemd available.
    """
    try:
        __import__("systemd")
    except:
        return False
    return True


def journal(unit=None, this_boot=True):
    """Convenience function to access the journal
    """
    cmd = ["journalctl"]
    if unit:
        cmd += ["--unit", unit]
    if this_boot:
        cmd += ["--this-boot"]
    return process.pipe(cmd)


def copy_dir_if_not_exist(orig, target):
    """function to copy missing directories from one location to another
    should only be used when syncing a directory structure from iso
    to disk like /var/log
    use case -- upgrade adds some service which logs to /var/log/<service>
    need to have the directory created, but it's not on iso upgrade
    """
    for f in os.listdir(orig):
        if os.path.isdir("%s/%s" % (orig, f)):
            if not os.path.exists("%s/%s" % (target, f)):
                process.call("cp -av %s/%s %s &>/dev/null" % (orig, f,
                                                              target),
                             shell=True)
            else:
                copy_dir_if_not_exist("%s/%s" % (orig, f), "%s/%s" % (target,
                                                                      f))


@contextmanager
def mounted_boot(source="/liveos"):
    """Used to mount /boot
    Normally /boot is from the /liveos mountpoint, but sometimes it's
    elsewhere, thus we have source
    """

    LOGGER.info("Mounting %r to /boot" % source)

    if source == "/liveos":
        import ovirtnode.ovirtfunctions as ofunc
        ofunc.mount_liveos()

        if not os.path.ismount("/liveos"):
            raise RuntimeError("Failed to mount /liveos")

    liveos = Mount(source)
    boot = Mount(device=source, path="/boot")

    liveos.remount(rw=True)
    boot.mount("bind")

    if not os.path.ismount("/boot"):
        raise RuntimeError("Failed to mount /boot")

    try:
        # Now run something in this context
        yield
    except Exception as e:
        LOGGER.warn("An error appeared while "
                    "interacting with /boot: %s" % e)
        raise
    finally:
        boot.umount()
        liveos.umount()

    LOGGER.info("Successfully unmounted /liveos and /boot")


class Syslog(base.Base):
    aug = utils.AugeasWrapper()

    def __get_index(self):
        index = None
        m = self.aug.match("/files/etc/rsyslog.conf/*/action/hostname")
        group = m[0] if m else None
        pat = re.compile(r'.*?entry\[(\d+)\].*')
        if group:
            index = int(pat.sub(r'\1', group))
        elif self.aug.get("/augeas/files/etc/rsyslog.conf/error"):
            self.logger.error("Augeas could not parse rsyslog.conf. "
                              "Please check "
                              "/augeas/files/etc/rsyslog.conf/error "
                              "with augtool")
            raise RuntimeError("Augeas could not parse rsyslog.conf")
        else:
            group = \
                self.aug.match('/files/etc/rsyslog.conf/entry[last()]/*')[0]
            index = int(pat.sub(r'\1', group)) + 1
        return index

    def clear_config(self):
        self.logger.info("Clearing rsyslog config")
        sel = self.aug.match("/files/etc/rsyslog.conf/entry[%d]" %
                             self.__get_index())
        self.aug.remove_many(sel)

    def configure(self, server, port):
        # I know this doesn't make any sense, but augeas is incredibly
        # finicky about the lenses, and if these aren't inserted in exactly
        # the right order, it will fail
        config = [{"/selector/facility": "*"},
                  {"/selector/level": "*"},
                  {"/action/hostname": server},
                  {"/action/port": port}]

        path = "/files/etc/rsyslog.conf/entry[%d]" % self.__get_index()
        for i in config:
            for k, v in i.items():
                k = path + k
                self.aug.set(k, v, do_save=False)
        try:
            self.aug.save()
        except:
            self.logger.error("Augeas failed to save values, check "
                              "lenses versus values")
            self.logger.error(self.aug.get_many(self.aug.match("%s/*/*" %
                                                               path)))
            self.logger.error(self.aug.get_many(self.aug.match(
                "/augeas/files/etc/rsyslog.conf/error/*")))
            self.logger.error(self.aug.get_many(self.aug.match(
                "/augeas/files/etc/rsyslog.conf/error/*/*")))
            raise RuntimeError("Augeas failed to save rsyslog.conf")


class NVR(object):
    """Simple clas to parse and compare NVRs

    >>> nvr = NVR.parse("ovirt-node-1.2.3-4.el6")
    >>> nvr.name
    'ovirt-node'
    >>> nvr.version
    '1.2.3'
    >>> nvr.release
    '4.el6'

    >>> nvr_new = NVR.parse("ovirt-node-1.2.3-5.el6")
    >>> nvr < nvr_new
    True

    >>> nvr_new = NVR.parse("ovirt-node-2.2.3-4.el6")
    >>> nvr < nvr_new
    True
    """
    name = None
    version = None
    release = None

    @staticmethod
    def parse(nvr):
        if not nvr.strip():
            raise RuntimeError("No package NVR to parse: %s" % nvr)
        o = NVR()
        try:
            nvrtuple = re.match("^(^.*)-([^-]*)-([^-]*)$", nvr).groups()
        except:
            raise RuntimeError("Failed to parse NVR: %s" % nvr)
        if not nvrtuple:
            raise RuntimeError("Failed to parse nvr: %s" % nvr)
        o.name, o.version, o.release = nvrtuple
        return o

    def __cmp__(self, other):
        if not self.name == other.name:
            raise RuntimeError("NVRs for different names: %s %s"
                               % (self.name, other.name))
        this_version = (None, self.version, self.release)
        other_version = (None, other.version, other.release)
        return rpm.labelCompare(this_version,  # @UndefinedVariable
                                other_version)

    def __str__(self):
        return "%s-%s-%s" % (self.name, self.version, self.release)


class RpmPackage(base.Base):
    """Provide access to some rpm meta informations
    """

    name = None

    def __init__(self, name):
        super(RpmPackage, self).__init__()
        self.name = name

    def _raw_nvr(self):
        cmd = ["rpm", "-q", self.name]
        nvr = process.pipe(cmd).strip().split("\n")
        self.logger.debug("Found build: %s" % nvr)
        if len(nvr) != 1:
            raise RuntimeError("Failed to retrieve nvr for %s: %s" %
                               (self.name, nvr))
        return nvr[0]

    def nvr(self):
        return NVR.parse(self._raw_nvr())


class SystemRelease(base.Base):
    """Informations about the OS based on /etc/system-release-cpe

    Use openscap_api.cpe.name_new(str) from openscap-python for an official
    way.
    """
    CPE_FILE = "/etc/system-release-cpe"

    VENDOR = None
    PRODUCT = None
    VERSION = None

    def __init__(self):
        super(SystemRelease, self).__init__()
        self.load()

    def load(self):
        """Parse the CPE FILE
        """
        cpe_uri = self.cpe()
        self.logger.debug("Read CPE URI: %s" % cpe_uri)
        cpe_parts = cpe_uri.split(":")
        self.logger.debug("Parsed CPE parts: %s" % cpe_parts)
        if cpe_parts[0] != "cpe":
            raise RuntimeError("Can not parse CPE string in %s" %
                               self.CPE_FILE)
        self.VENDOR, self.PRODUCT, self.VERSION = cpe_parts[2:5]

    def cpe(self):
        """Return the CPE URI
        """
        return File(self.CPE_FILE).read().strip()

    def is_fedora(self):
        return self.VENDOR.lower() == "fedoraproject"

    def is_centos(self):
        return self.VENDOR.lower() == "centos"

    def is_redhat(self):
        return self.VENDOR.lower() == "redhat"

    def is_el(self):
        """Determin if this system is an "enterprise linux" (RHEL, CentOS)
        """
        return self.VENDOR.lower() == "redhat" or \
            self.VENDOR.lower() == "centos"

    def is_min_el(self, minversion):
        """Determin if this system is an EL and at min version minversion
        """
        return (self.is_el() and float(self.VERSION) >= minversion)

    def is_max_el(self, maxversion):
        """Determin if this system is an EL and at max version maxversion
        """
        return (self.is_el() and float(self.VERSION) <= maxversion)


class ProductInformation(base.Base):
    """Return oVirt Node product informations
    """
    _version_filename = "/files/etc/default/version"
    PRODUCT_SHORT = None
    VERSION = None
    RELEASE = None

    def __init__(self):
        super(ProductInformation, self).__init__()
        self.load()

    def load(self):
        aug = utils.AugeasWrapper()
        augg = lambda k: aug.get("\n%s/%s\n" % (self._version_filename, k),
                                 strip_quotes=True)

        # read product / version info
        self.PRODUCT_SHORT = augg("PRODUCT_SHORT") or "oVirt"
        self.VERSION = augg("VERSION")
        self.RELEASE = augg("RELEASE")

    def __str__(self):
        return "%s %s-%s" % (self.PRODUCT_SHORT, self.VERSION, self.RELEASE)


class InstallationMedia(base.Base):
    """Informations about the installation media - where the current
    installation is run from
    """
    version = "0"
    release = "0"

    @property
    def full_version(self):
        """Return the full version
        >>> m = InstallationMedia(and_load=False)
        >>> m.version = "1.2"
        >>> m.release = "3"
        >>> m.full_version
        '1.2-3'
        """
        return "%s-%s" % (self.version, self.release)

    @property
    def version_major(self):
        """Return the major version
        >>> m = InstallationMedia(and_load=False)
        >>> m.version = "1.2"
        >>> m.release = "3"
        >>> m.version_major
        '1'
        """
        return self.version.split(".")[0]

    @property
    def version_minor(self):
        """Return the minor version
        >>> m = InstallationMedia(and_load=False)
        >>> m.version = "1.2"
        >>> m.release = "3"
        >>> m.version_minor
        '2'
        """
        return self.version.split(".")[1]

    def __init__(self, and_load=True):
        super(InstallationMedia, self).__init__()
        if and_load:
            self.load()

    def load(self):
        from ovirtnode.ovirtfunctions import get_media_version_number
        data = get_media_version_number()
        if data:
            self.version, self.release = data

    def __str__(self):
        return self.full_version

    def __cmp__(self, other):
        """Compare two medias
        >>> media = InstallationMedia(False)
        >>> media.version, media.release = "2.5", "0"
        >>> media.full_version
        '2.5-0'
        >>> installed = InstalledMedia(False)
        >>> installed.version, installed.release = "2.6", "0"
        >>> installed.full_version
        '2.6-0'
        >>> media < installed
        True
        >>> media == installed
        False
        >>> media > installed
        False
        >>> media.version = "2.6"
        >>> media == installed
        True
        >>> media.release = "1"
        >>> media == installed
        False
        >>> media > installed
        True
        """
        assert InstallationMedia in type(other).mro()
        this_version = ('1', self.version, self.release)
        other_version = ('1', other.version, other.release)
        return rpm.labelCompare(this_version,  # @UndefinedVariable
                                other_version)


class InstalledMedia(InstallationMedia):
    """Informations about the installed media - infos from the image
    """

    def load(self):
        from ovirtnode.ovirtfunctions import get_installed_version_number
        data = get_installed_version_number()
        if data:
            self.version, self.release = data
        else:
            LOGGER.debug("Failed to retrieve installed media " +
                         "version: %s" % data)

    def available(self):
        """Determin if there is an installed media
        """
        return int(self.version_major) > 0


class Keyboard(base.Base):
    """Configure the system wide keyboard layout
    FIXME what is the recommended way to do this on F18+ with localectl
    localectl also stores the changes, so is kbd still needed?
    localectl doesn't offer the descriptive name of the layouts
    """
    def __init__(self):
        super(Keyboard, self).__init__()
        self.kbd = system_config_keyboard.keyboard.Keyboard()
        self.kbd.read()

    def available_layouts(self):
        layoutgen = ((details[0], kbid)
                     for kbid, details in self.kbd.modelDict.items())
        layouts = [(kid, name) for name, kid in sorted(layoutgen)]
        return layouts

    def set_layout(self, layout):
        assert layout
        if has_systemd():
            utils.process.call(["localectl", "set-keymap", layout])
        else:
            self.kbd.set(layout)
            self.kbd.write()
            self.kbd.activate()

    def reactivate(self):
        self.kbd.activate()

    def get_current(self):
        return self.kbd.get()

    def get_current_name(self):
        layout_name = None
        for kid, name in self.available_layouts():
            if kid == self.get_current():
                layout_name = name
                break
        return layout_name


class Reboot(base.Base):
    def simpleDaemon(self, main, args=(), kwargs={}):
        # Default maximum for the number of available file descriptors.
        MAXFD = 1024

        import resource  # Resource usage information.
        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if (maxfd == resource.RLIM_INFINITY):
            maxfd = MAXFD

        pid = os.fork()
        if pid == 0:
            try:
                os.chdir('/')
                os.setsid()
                for fd in range(0, maxfd):
                    try:
                        os.close(fd)
                    except OSError:
                        # ERROR, fd wasn't open to begin with (ignored)
                        pass

                os.open(os.devnull, os.O_RDWR)  # standard input (0)
                os.dup2(0, 1)  # standard output (1)
                os.dup2(0, 2)  # standard error (2)

                if os.fork() != 0:
                    os._exit(0)

                try:
                    main(*args, **kwargs)
                except:
                    import traceback
                    traceback.print_exc()
            finally:
                os._exit(1)

        pid, status = os.waitpid(pid, 0)

        if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
            raise RuntimeError('Daemon not exited properly')

    def delayedReboot(self, reboot, sleepTime):
        time.sleep(sleepTime)
        os.execl(reboot, reboot)

    def reboot(self, delay=3):
        try:
            import daemon
            with daemon.DaemonContext():
                # the following lines are all executed in a background daemon
                time.sleep(delay)
                cmd = which("reboot")
                subprocess.call(cmd, shell=True)
        except:
            self.logger.info("Scheduling Reboot")

            self.simpleDaemon(
                self.delayedReboot,
                (
                    which("reboot"),
                    delay,
                )
            )
            self.logger.info("Reboot Scheduled")


class EFI(base.Base):
    """A simple wrapper around efibootmgr to modify the EFI boot entries
    """
    class BootEntry(base.Base):
        bootnum = None
        label = None
        value = None

        def to_tuple(self):
            return self.bootnum, self.label, self.value

        def __cmp__(self, other):
            return self.to_tuple() == other.to_tuple()

        def __repr__(self):
            return str(self)

        def __str__(self):
            """String representation of a boot entry

            >>> e = EFI.BootEntry()
            >>> e.bootnum, e.label, e.value = (42, "Foo", "Bar")
            >>> str(e) # doctest: +ELLIPSIS
            "<BootEntry bootnum='42' label='Foo' value='Bar' at ...>"
            """
            return self.build_str(["bootnum", "label", "value"])

    def _efibootmgr(self, cmdargs):
        """Run efibootmgr with cmdargs

        >>> e = EFI()
        >>> e._call = lambda c: c
        >>> e._efibootmgr([("verbose", None),
        ...                ("label", "Foo")])
        ['efibootmgr', '--verbose', '--label', 'Foo']
        """
        cmd = ["efibootmgr"]

        for k, v in cmdargs:
            cmd.append("--%s" % k)
            if v is not None:
                cmd.append(str(v))

        self.logger.debug("About to run: %s" % cmd)
        return self._call(cmd)

    def _call(self, cmd):
        return process.check_output(cmd)

    def add_entry(self, label, loader_filename, disk):
        """Add a new EFI boot entry

        Args:
            label: Label to be shown in the EFI boot menu
            loader_filename: Filename of the bootloader (e.g. grub2) to use
            disk: Disk where the bootloader resides on
        """
        self.logger.debug(("Adding EFI boot entry: " +
                           "label=%s, loader=%s, disk=%s") %
                          (label, loader_filename, disk))
        cmdargs = [("verbose", None),
                   ("create", None),
                   ("label", label),
                   ("loader", loader_filename),
                   ("disk", disk)]
        self._efibootmgr(cmdargs)

        return True

    def list_entries(self):
        pat = re.compile("^Boot([0-9a-zA-Z]{4})[\* ] ([^\t]+)\t(.*)$")
        entries = []

        lines = self._efibootmgr([("verbose", None)])

        self.logger.debug("Parsing EFI boot entries from: %s" % lines)

        # Parse the lines
        for line in lines.split("\n"):
            match = pat.search(line)
            if match:
                entry = EFI.BootEntry()
                entry.bootnum, entry.label, entry.value = match.groups()
                entries.append(entry)

        return entries

    def remove_entry(self, entry):
        """Remove an EFI boot entry

        Args:
            entry: An EFI.BootEntry object, can be retrieved with
                   efi.list_entries()
        """
        entry_exists = False

        for other_entry in self.list_entries():
            if other_entry == entry:
                entry_exists = True

        if not entry_exists:
            raise RuntimeError("Tried to remove non-existent " +
                               "EFI boot entry: %s" % entry)

        self.logger.debug("Removing EFI boot entry: %s" % entry)
        self._efibootmgr([("verbose", None),
                          ("bootnum", entry.bootnum),
                          ("delete-bootnum", None)])

        return True


class Filesystem(base.Base):
    """A class for finding and handling filesystems"""
    device = None

    def __init__(self, device):
        self.device = device

    @staticmethod
    def _flush():
        """Let all pending operations finish and flush anything to any disks
        E.g. iscsi etc

        pipe() is used to capture the output of the calls
        """
        # Don't litter the screen with output, so get a handle to /dev/null
        with open(os.devnull, 'wb') as DEVNULL:
            process.call(["udevadm", "settle"], stdout=DEVNULL, stderr=DEVNULL)

    @staticmethod
    def by_label(label):
        """Determines whether a filesystem with a given label is present on
        this system
        """
        fs = None
        try:
            Filesystem._flush()
            with open(os.devnull, 'wb') as DEVNULL:
                device = process.check_output(["blkid", "-c", "/dev/null",
                                               "-L", label], stderr=DEVNULL
                                              ).strip()

            fs = Filesystem(device)

        except process.CalledProcessError as e:
            LOGGER.debug("Failed to resolve disks: %s" % e.cmd, exc_info=True)
        return fs

    @staticmethod
    def by_partlabel(partlabel):
        """Determines whether a filesystem with a given partlabel is present on
        this system
        """
        fs = None

        try:
            Filesystem._flush()
            with open(os.devnull, 'wb') as DEVNULL:
                device = process.check_output(["blkid", "-c", "/dev/null",
                                               "-o", "device", "-l", "-t",
                                               "PARTLABEL=%s" % partlabel],
                                              stderr=DEVNULL).strip()

            fs = Filesystem(device)

        except process.CalledProcessError as e:
            LOGGER.debug("Failed to resolve disks: %s" % e.cmd, exc_info=True)

        return fs

    def _tokens(self):
        tokens = process.check_output(["blkid", "-o", "export", self.device])
        return parse_varfile(tokens)

    def label(self):
        return self._tokens().get("LABEL", None)

    def mountpoints(self):
        try:
            targets = process.check_output(["findmnt", "-o", "target", "-n",
                                            self.device]).strip().split("\n")
            return [Mount(t.strip()) for t in targets]
        except process.CalledProcessError:
            return []


class Mount(base.Base):
    """A class to find the base mount point for a path and handle mounting
    that filesystem for access
    """

    def __init__(self, path, device=None, fstype=None):
        self.path = path
        self.fstype = fstype
        self.device = device

    def remount(self, rw=False):
        if not os.path.ismount(self.path):
            LOGGER.exception("%s is not a mount point" % self.path)
            raise RuntimeError("%s is not a mount point" % self.path)

        # EL6 won't let you remount if it's not in mtab or fstab
        # So we'll parse /proc/mounts ourselves to find it
        device = self._find_device()
        try:
            if rw:
                utils.process.check_call(["mount", "-o", "rw,remount",
                                          device, self.path])
            else:
                utils.process.check_call(["mount", "-o", "ro,remount",
                                          device, self.path])
        except:
            LOGGER.exception("Can't remount %s on %s!" % (device,
                                                          self.path))

    def mount(self, options=None):
        if not self.device:
            LOGGER.exception("Can't mount without a device specified")
            raise RuntimeError("No device was specified when Mount() "
                               "was initialized")

        args = ["mount", "-t", self.fstype if self.fstype else "auto"]
        if options:
            args += ["-o" + options]
        args += [self.device, self.path]

        try:
            utils.process.check_call(args)
        except:
            LOGGER.exception("Can't mount %s on %s" % (self.device,
                             self.path))

    def umount(self):
        if not self.path:
            LOGGER.exception("Can't umount without a path specified")
            raise RuntimeError("No path was specified when Mount() "
                               "was initialized")

        try:
            utils.process.check_output(["umount", self.path])

        except subprocess.CalledProcessError as e:
            LOGGER.warn("Can't umount %s: %s" % (self.path, e.output),
                        exc_info=True)

    def _find_device(self):
        try:
            return process.check_output(["findmnt", "-o", "SOURCE", "-n",
                                         self.path]).strip()
        except:
            raise RuntimeError("Couldn't find mount device for %s" % self.path)

    def __repr__(self):
        return "Mount(%s)" % self.path

    def __str__(self):
        return self.path

    @staticmethod
    def find_by_path(path):
        """Find the mountpoint for a specific path recursively
        """
        while not os.path.ismount(path):
            path = os.path.dirname(path)
        return Mount(path)


class Bootloader(base.Base):
    """Figures out where grub.conf can be found and which bootloader is used

    FIXME This really needs a doctest because it is messing with the boot
    config
    """

    @staticmethod
    def is_grub2():
        # If grub2 exists on the image, assume we're using it
        return os.path.exists("/sbin/grub2-install")

    @staticmethod
    def find_grub_cfg():
        cfg_path = None

        if os.path.ismount("/dev/.initramfs/live"):
            if Bootloader.is_grub2():
                cfg_path = "/dev/.initramfs/live/grub2/grub.cfg"
            else:
                cfg_path = "/dev/.initramfs/live/grub/grub.conf"
        elif os.path.ismount("/run/initramfs/.live"):
            cfg_path = "/liveos/grub/grub.conf"
        elif Filesystem.by_label("Boot"):
            cfg_path = "/boot/grub/grub.conf"

        else:
            raise RuntimeError("Failed to find the path for grub.[cfg|conf]")

        cfg = File(cfg_path)

        if not cfg.exists():
            raise RuntimeError("Grub config file does not exist: %s" %
                               cfg.filename)

        return cfg

    class Arguments(base.Base):

        def __init__(self, dry=False, path=None):
            if not dry:
                if not path:
                    self.__handle = Bootloader.find_grub_cfg()
                else:
                    self.__handle = File(path)
                self.__mount = Mount.find_by_path(self.__handle.filename)
                self.items = self.__get_arguments()

        def __str__(self):
            return str(self.items)

        def __get_lines(self):
            lines = [line for line in self.__handle]
            return lines

        def __get_arguments(self, kernel=None):
            if not kernel:
                kernel = [line for line in self.__get_lines() if
                          re.match(r'[^#].*?vmlinuz', line)][0]
                kernel = re.sub(r'^\s*?(kernel|linux)\s+?\/vmlinuz.*?\s+', '',
                                kernel)
            params = {}
            for param in kernel.split():
                match = re.match(r'(.*?)=(.*)', param)
                if match:
                    params[match.groups()[0]] = match.groups()[1]
                else:
                    params[param] = True
            self.items = params
            return params

        def dry_arguments(self, line):
            if "vmlinuz" not in line:
                line = "vmlinuz " + line
            return self.__get_arguments(kernel=line)

        def __getitem__(self, key):
            if re.match(r'^(.*?)=', key):
                argument = re.match(r'^(.*?)=', key).groups()[0]
                # flags = re.match(r'^.*?=(.*)', key).groups()[0]
                if argument in self.items:
                    return self.items[argument]
            elif key in self.items:
                return self.items[key]
            else:
                raise KeyError

        def __setitem__(self, key, value):
            if value is True:
                self.update_args(key)
            else:
                self.update_args("%s=%s" % (key, value))

        def get(self, key, alt=None):
            return self.items.get(key, alt)

        def keys(self):
            return self.items.keys()

        def values(self):
            return self.items.values()

        def has_key(self, key):
            return key in self.items

        def __len__(self):
            return len(self.items)

        def __delitem__(self, key):
            self.update_args(key, True)

        def update(self, changes):
            for k, v in changes:
                self.__setitem__(k, v)

        def __contains__(self, key):
            return key in self.items

        def update_args(self, arg, remove=False):
            self.__mount.remount(rw=True)
            grub_cfg = self._parse_config(self.__get_lines(), arg, remove)
            File(self.__handle.filename).write(grub_cfg, "w")
            self.__mount.remount(rw=False)

        def remove_args(self, arg):
            self.update_args(arg, remove=True)

        def _parse_config(self, lines, arg, remove):
            """Parses and modifies the passed grub config

            >>> cfg = ["head", " kernel /vmlinuz0 arg1 foo=bar arg2", "tail"]
            >>> b = Bootloader.Arguments(dry=True)
            >>> split_args = lambda x: filter(None, x.split('\\n'))
            >>> parse_cfg = lambda cfg, arg, remove: split_args(
            ...                 b._parse_config(cfg, arg, remove))
            >>> parsed_args = lambda arg, remove: parse_cfg(cfg, arg, remove)
            >>> parsed_args("foo=bar", True)
            ['head', ' kernel /vmlinuz0 arg1 arg2', 'tail']
            >>> parsed_args("foo=oof", False)
            ['head', ' kernel /vmlinuz0 arg1 foo=oof arg2', 'tail']
            >>> parsed_args("new", False)
            ['head', ' kernel /vmlinuz0 arg1 foo=bar arg2 new', 'tail']

            >>> def closed_args(cfg):
            ...     cfg = [cfg]
            ...     def closure(arg, remove):
            ...         cfg[0] = parse_cfg(cfg[0], arg, remove)
            ...         return cfg[0]
            ...     return closure
            >>> modified_args = closed_args(cfg)

            >>> modified_args("foo=oof", False)
            ['head', ' kernel /vmlinuz0 arg1 foo=oof arg2', 'tail']
            >>> modified_args('foo=qq', False)
            ['head', ' kernel /vmlinuz0 arg1 foo=qq arg2', 'tail']
            >>> modified_args('foo', True)
            ['head', ' kernel /vmlinuz0 arg1 arg2', 'tail']
            >>> modified_args('qq=qux', False)
            ['head', ' kernel /vmlinuz0 arg1 arg2 qq=qux', 'tail']
            >>> modified_args('qq=xuq', False)
            ['head', ' kernel /vmlinuz0 arg1 arg2 qq=xuq', 'tail']
            >>> modified_args('qq', True)
            ['head', ' kernel /vmlinuz0 arg1 arg2', 'tail']
            """

            replacement = arg
            # Check if it's parameterized
            if '=' in arg:
                arg = re.match(r'^(.*?)=.*', arg).groups()[0]

            grub_cfg = ""
            for line in lines:
                if re.match(r'.*?\s%s' % arg, line):
                    if remove:
                        line = re.sub(r'%s(=.*?)?(\s|$)' % arg, '', line)
                    else:
                        if arg != replacement:
                            line = re.sub(r'%s(=.*?)?(\s|$)' % arg, '%s ' %
                                          replacement, line)
                elif re.match(r'^.*?vmlinuz', line):
                    # Not in the kernel line. Add it.
                    line = line.rstrip() + " %s\n" % replacement
                line = line.rstrip() + "\n"
                grub_cfg += line
            return grub_cfg


class LVM(base.Base):
    """A convenience class for querying LVM volume groups
    and their associated attributes
    """

    def vgs(self):
        """Return a list of VG instances for each VG on the host
        """
        return [LVM.VG(n) for n in self._query_vgs("vg_name")]

    class VG(base.Base):
        """Wrapper around the 'lvm vgs' command
        """
        def __init__(self, name):
            self.name = name

        @property
        def tags(self):
            """Retrieve all tags associated to a VG
            """
            return LVM._query_vgs("tags", self.name)

        @property
        def pv_names(self):
            """Rerieve all PV names of a VG
            """
            return LVM._query_vgs("pv_name", self.name)

    @classmethod
    def _query_vgs(self, option, pv=None):
        cmd = ["lvm", "vgs", "--noheadings", "-o", option]

        if pv:
            cmd.append(pv)

        out = process.check_output(cmd).strip()
        vgs = None

        # If not VGs are found, just simulate an empty list of VGs
        if "No volume groups found" in out:
            vgs = []
        else:
            vgs = [x.strip() for x in out.split("\n")]

        return vgs


class Initramfs(base.Base):
    """This class shall wrap the logic needed to rebuild the initramfs

    The main obstacle is mounting the correct paths.
    Furthermore we are taking care that now orphans are left over.

    Args:
        dracut_chroot: Path for dracut chroot
        boot_source: Source where to take /boot from
    """
    dracut_chroot = None
    boot_source = None

    def __init__(self, dracut_chroot="/", boot_source=None):
        self.dracut_chroot = dracut_chroot
        self.boot_source = boot_source

    def try_unlink(self, path):
        try:
            os.unlink(path)
        except OSError as e:
            LOGGER.warn("Failed to remove %r: %s", path, e)

    def _generate_new_initramfs(self, new_initrd, kver):
        LOGGER.info("Generating new initramfs "
                    "%r for kver %s (this can take a while)" %
                    (new_initrd, kver))
        rd_stdout = ""
        try:
            argv = ["chroot", self.dracut_chroot,
                    "dracut", "--kver", kver, new_initrd]
            LOGGER.debug("Calling: %s" % argv)

            rd_stdout = check_output(argv, stderr=process.STDOUT)
        except:
            LOGGER.warn("dracut failed to generate the initramfs")
            LOGGER.warn("dracut output: %s" % rd_stdout)
            self.try_unlink(new_initrd)
            raise

    def _install_new_initramfs(self, new_initrd, pri_initrd):
        LOGGER.info("Installing the new initramfs "
                    "%r to %r" % (new_initrd, pri_initrd))

        backup_initrd = "/var/tmp/initrd0.img.backup"

        try:
            check_call(["cp", pri_initrd, backup_initrd])
        except:
            LOGGER.error("Failed to create the backupfile")
            # Still trying to unlink, maybe setting attrs failed
            self.try_unlink(backup_initrd)
            raise

        try:
            check_call(["mv", new_initrd, pri_initrd])
            # Only remove the backup in case that the new on got installed
            self.try_unlink(backup_initrd)
        except:
            LOGGER.error("Failed to put the new initrd in place")
            LOGGER.error(" Please cleanup manually")
            LOGGER.error(" Backup: %r" % backup_initrd)
            LOGGER.error(" initrd location: %r" % pri_initrd)
            self.try_unlink(new_initrd)
            raise

    def rebuild(self, kver):
        pri_initrd = "/boot/initrd0.img"
        new_initrd = "/var/tmp/initrd0.img.new"

        LOGGER.info("Preparing to regenerate the initramfs")
        LOGGER.info("The regenreation will overwrite the "
                    "existing")
        LOGGER.info("Rebuilding for kver: %s" % kver)

        with mounted_boot(source=self.boot_source):
            self._generate_new_initramfs(new_initrd, kver)
            self._install_new_initramfs(new_initrd, pri_initrd)

        LOGGER.info("Initramfs regenration completed successfully")

# vim: set sts=4 et:
