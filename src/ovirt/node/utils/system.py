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
from ovirt.node import base, utils, log
from ovirt.node.utils import process
from ovirt.node.utils.fs import File
from ovirt.node.utils.console import CaptureOutput
import glob
import os
import re
import rpm
import subprocess
import sys
import system_config_keyboard.keyboard
import time

"""
A module to access system wide stuff
e.g. services, reboot ...
"""


LOGGER = log.getLogger(__name__)


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


def is_python_2_6():
    """If the system is running on Python 2.6
    """
    return sys.version_info[:2] == (2, 6)


def is_rescue_mode():
    """If the system is running in rescue mode
    """
    return any(arg in open("/proc/cmdline").read().split() for arg
               in ["rescue", "S", "single", "1"])


def cpu_details():
    """Return details for the CPU of this machine, virt related
    """
    from ovirtnode.ovirtfunctions import cpu_details
    return cpu_details()


def has_hostvg():
    """Determine if a HostVG is present on this system (indicates an existing
    installation)
    """
    return os.path.exists("/dev/HostVG")


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
        with open(self.CPE_FILE, "r") as f:
            cpe_uri = f.read().strip()
            self.logger.debug("Read CPE URI: %s" % cpe_uri)
            cpe_parts = cpe_uri.split(":")
            self.logger.debug("Parsed CPE parts: %s" % cpe_parts)
            if cpe_parts[0] != "cpe":
                raise RuntimeError("Can not parse CPE string in %s" %
                                   self.CPE_FILE)
            self.VENDOR, self.PRODUCT, self.VERSION = cpe_parts[2:5]

    def is_fedora(self):
        """Determin if this system is a fedora system
        """
        return self.VENDOR.lower() == "fedoraproject"

    def is_el(self):
        """Determin if this system is an "enterprise linux" (RHEL, CentOS)
        """
        return self.VENDOR.lower() == "redhat"


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
            process.call(["partprobe"] + [x for x in glob.glob("/dev/mapper/*")
                                          if not re.match(r'.*\/control$', x)],
                         stdout=DEVNULL, stderr=DEVNULL)
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
                                               "-L", label], stderr=DEVNULL)

            fs = Filesystem(label, device)

        except process.CalledProcessError as e:
            LOGGER.debug("Failed to resolve disks: %s" % e.cmd, exc_info=True)
        return fs

    def _tokens(self):
        tokens = process.check_output(["blkid", "-o", "export", self.device])
        return parse_varfile(tokens)

    def label(self):
        return self._tokens().get("LABEL", None)

    def mountpoints(self):
        targets = process.check_output(["findmnt", "-o", "target", "-n",
                                        self.device]).split("\n")
        return [Mount(t.strip()) for t in targets]


class Mount(base.Base):
    """A class to find the base mount point for a path and handle mounting
    that filesystem for access
    """

    def __init__(self, path):
        if os.path.ismount(path):
            self.path = path
        else:
            raise RuntimeError("Must be called with a mount point")

    def remount(self, rw=False):
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
            self.logger.exception("Can't remount %s on %s!" % (device,
                                                               self.path))

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
        while not os.path.ismount(path):
            path = os.path.dirname(path)
        return Mount(path)


class Bootloader(base.Base):
    """Figures out where grub.conf can be found and which bootloader is used"""

    @staticmethod
    def is_grub2():
        # If grub2 exists on the image, assume we're using it
        return os.path.exists("/sbin/grub2-install")

    @staticmethod
    def find_grub_cfg():
        cfg_path = None

        if Filesystem.by_label("Boot"):
            cfg_path = "/boot/grub/grub.conf"
        elif os.path.ismount("/dev/.initramfs/live"):
            if not Bootloader.is_grub2():
                cfg_path = "/dev/.initramfs/live/grub/grub.conf"
            else:
                cfg_path = "/dev/.initramfs/live/grub2/grub.cfg"
        elif os.path.ismount("/run/initramfs/.live"):
            cfg_path = "/liveos/grub/grub.conf"

        else:
            raise RuntimeError("Failed to find the path for grub.[cfg|conf]")
        return File(cfg_path)

    class Arguments(base.Base):

        def __init__(self):
            self.__handle = Bootloader.find_grub_cfg()
            self.__mount = Mount.find_by_path(self.__handle.filename)
            self.items = self.__get_arguments()

        def __str__(self):
            return str(self.items)

        def __get_lines(self):
            lines = [line for line in self.__handle]
            return lines

        def __get_arguments(self):
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

        def __getitem__(self, key):
            if re.match(r'^(.*?)=', key):
                argument = re.match(r'^(.*?)=', key).groups()[0]
                #flags = re.match(r'^.*?=(.*)', key).groups()[0]
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

        def keys(self):
            return self.items.keys()

        def values(self):
            return self.items.values()

        def has_key(self, key):
            return key in self.items

        def __len__(self):
            return len(self.items)

        def __delitem__(self, key):
            self.update_args(self, key, True)

        def update(self, changes):
            for k, v in changes:
                self.__setitem__(k, v)

        def __contains__(self, key):
            return key in self.items

        def update_args(self, arg, remove=False):
            replacement = arg
            # Check if it's parameterized
            if '=' in arg:
                arg = re.match(r'^(.*?)=.*', arg).groups()[0]
            self.__mount.remount(rw=True)
            lines = self.__get_lines()
            grub_cfg = ""
            for line in lines:
                if re.match(r'.*?\s%s' % arg, line):
                    if remove:
                        line = re.sub(r' %s(=.*?\s?)?' % arg, '', line)
                    else:
                        if arg != replacement:
                            line = re.sub(r'%s(=.*?\s?)?' % arg, ' %s ' %
                                          replacement, line)
                elif re.match(r'^.*?vmlinuz', line):
                    # Not in the kernel line. Add it.
                    line = line.strip() + " %s\n" % replacement
                grub_cfg += line
            File(self.__handle.filename).write(grub_cfg, "w")
            self.__mount.remount(rw=False)

        def remove_args(self, arg):
            self.update_args(arg, remove=True)
