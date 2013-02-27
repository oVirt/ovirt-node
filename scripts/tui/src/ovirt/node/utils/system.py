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
from ovirt.node.config import defaults
from ovirt.node.utils import process
import os.path
import rpm
import system_config_keyboard.keyboard

"""
A module to access system wide stuff
e.g. services, reboot ...
"""


def reboot():
    """Reboot the system
    """
    process.call("reboot")


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
    """
    def __init__(self):
        super(Keyboard, self).__init__()
        self.kbd = system_config_keyboard.keyboard.Keyboard()

    def available_layouts(self):
        self.kbd.read()
        layoutgen = ((details[0], kid)
                     for kid, details in self.kbd.modelDict.items())
        layouts = [(kid, name) for name, kid in sorted(layoutgen)]
        return layouts

    def set_layout(self, layout):
        self.kbd.set(layout)
        self.kbd.write()
        self.kbd.activate()
        utils.process.check_call("localectl set-keymap %s" % layout)

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
