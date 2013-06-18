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
from ovirt.node import base, utils
from ovirt.node.utils import process
import os
import logging
import rpm
import system_config_keyboard.keyboard
import time
import subprocess

"""
A module to access system wide stuff
e.g. services, reboot ...
"""


LOGGER = logging.getLogger(__name__)


def reboot():
    """Reboot the system
    """
    process.call("reboot")


def async_reboot(delay=3):
    reboot_task = Reboot()
    reboot_task.reboot(delay)


def poweroff():
    """Poweroff the system
    """
    process.call("poweroff")


def is_efi():
    """If the system is booted in (U)EFI mode
    """
    return os.path.exists("/sys/firmware/efi")


def cpu_details():
    """Return details for the CPU of this machine, virt related
    """
    from ovirtnode.ovirtfunctions import cpu_details
    return cpu_details()


def has_hostvg():
    """Determin if a HostVG is present on this system (indicates an existing
    installation)
    """
    return os.path.exists("/dev/HostVG")


def which(file):
    ret = None
    if os.path.abspath(file) and os.path.exists(file):
        ret = file
    else:
        for dir in os.environ["PATH"].split(":"):
            f = os.path.join(dir, file)
            if os.path.exists(f) and os.access(f, os.X_OK):
                ret = f
                break
    if ret is None:
        raise RuntimeError("Cannot find command '%s'" % file)
    return ret


def service(name, cmd, check=True):
    """Convenience wrapper to handle service interactions
    """
    try:
        kwargs = {"shell": False,
                  "stderr": process.PIPE}
        r = process.check_output(["service", name, cmd], **kwargs)
    except process.CalledProcessError as e:
        r = e.returncode
        LOGGER.exception("Service: %s" % e.output)
        if do_raise:
            raise
    return r


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
        self.kbd.set(layout)
        self.kbd.write()
        self.kbd.activate()
        utils.process.check_call("localectl set-keymap %s" % layout)

    def reactivate(self):
        self.kbd.activate()

    def get_current(self):
        return self.kbd.get()


class BootInformation(base.Base):
    """Provide informations about this boot
    """
    def __init__(self):
        self._model = defaults.Installation()
        super(BootInformation, self).__init__()

    def is_installation(self):
        #ovirtfunctions.is_install()
        return self._model.retrieve()["install"] is True

    def is_auto_installation(self):
        #ovirtfunctions.is_auto_install()
        cmdline = utils.fs.get_contents("/proc/cmdline")
        return "BOOTIF" in cmdline and ("storage_init" in cmdline or
                                        "ovirt_init" in cmdline)

    def is_upgrade(self):
        #ovirtfunctions.is_upgrade()
        return self._model.retrieve()["upgrade"] is True


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
                subprocess.call(cmd, close_fds=True)
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
