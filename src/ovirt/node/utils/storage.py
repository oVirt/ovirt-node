#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# storage.py - Copyright (C) 2012 Red Hat, Inc.
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

from ovirt.node import base
from ovirt.node.utils.fs import File
import os


class iSCSI(base.Base):
    """A class to deal with some external iSCSI related functionality
    """
    def initiator_name(self, initiator_name=None):
        try:
            import ovirtnode.iscsi as oiscsi
            if initiator_name:
                oiscsi.set_iscsi_initiator(initiator_name)
            return oiscsi.get_current_iscsi_initiator_name()
        except ImportError as e:
            self.logger.warning("Failed on import: %s" % e)


class NFSv4(base.Base):
    """A class to deal some external NFSv4 related functionality

    >>> import shutil
    >>> tmpcfg = "/tmp/idmapd.conf"
    >>> shutil.copy(NFSv4.configfilename, tmpcfg)
    >>> n = NFSv4()
    >>> n.configfilename = tmpcfg
    >>> n.domain("")
    >>> n.domain()
    >>> n.domain("abc")
    'abc'
    >>> n.domain()
    'abc'
    >>> n.domain("bar")
    'bar'
    """
    configfilename = "/etc/idmapd.conf"

    def domain(self, domain=None):
        """Get or set the domain
        Domain is None: Just retrieve the name
        Domain is "": Comment out the Domain directive
        (else): Set Domain to domain
        """
        if domain is not None:
            self.__set_domain(domain)
        return self.__get_domain()

    def __set_domain(self, domain):
        cfg = File(self.configfilename)

        if domain:
            # Uncomment Domain line and set new domain
            cfg.sub(r"^[#]?Domain =.*", "Domain = %s" % domain)
        else:
            # Comment out Domain line
            cfg.sub(r"^[#]?(Domain =.*)", r"#\1")

    def __get_domain(self):
        nfs_config = File(self.configfilename)
        matches = nfs_config.findall("^Domain = (.*)")
        return matches[0] if matches else None


class Devices(base.Base):
    """A class to retrieve available storage devices
    """
    _fake_devices = None
    _cached_live_disk_name = None

    def __init__(self, fake=False):
        super(Devices, self).__init__()
        if fake:
            self._fake_devices = {}
            for n in range(1, 4):
                args = ["%s%s" % (k, n) for k in "path", "bus", "name", "size",
                        "desc", "serial", "model"]
                self._fake_devices[args[1]] = Device(*tuple(args))
        else:
            import ovirtnode.storage
            self._storage = ovirtnode.storage.Storage()

    def live_disk_name(self):
        """get the device name of the live-media we are booting from
        BEWARE: Because querying this is so expensive we cache this result
                Assumption: Live disk name does not change
        """
        if self._cached_live_disk_name:
            return self._cached_live_disk_name

        from ovirtnode.ovirtfunctions import get_live_disk
        name = get_live_disk()
        if not "/dev/mapper" in name:
            # FIXME explain ...
            name = "/dev/%s" % name.rstrip('0123456789')
        self._cached_live_disk_name = name
        return name

    def get_all(self):
        """Get all available storage devices attached to this system
        """
        if self._fake_devices:
            return self._fake_devices
        from ovirtnode.ovirtfunctions import translate_multipath_device
        dev_names, disk_dict = self._storage.get_udev_devices()
        devices = {}
        for _dev in dev_names:
            dev = translate_multipath_device(_dev)
            self.logger.debug("Checking device %s (%s)" % (dev, _dev))
            if dev in devices:
                self.logger.warning("Device is already in dict: %s" % dev)
                continue
            if dev not in disk_dict:
                self.logger.warning("Device in names but not in dict: " +
                                    "%s" % dev)
                continue
            if dev == self.live_disk_name():
                self.logger.info("Ignoring device " +
                                 "%s it's the live media" % dev)
                continue
            infos = disk_dict[dev].split(",", 5)
            device = Device(dev, *infos)
            device.name = os.path.basename(device.name).replace(" ", "")
            device.name = translate_multipath_device(device.name)
            if device.name in devices:
                self.logger.debug("Device with same name already " +
                                  "exists: %s" % device.name)
            devices[device.path] = device
        return devices

    def translate_device_name(self, dev):
        from ovirtnode.ovirtfunctions import translate_multipath_device
        return translate_multipath_device(dev)


class Device(base.Base):
    """Wrapps the information about a udev storage device
    """
    path = None
    bus = None
    name = None
    size = None
    desc = None
    serial = None
    model = None

    def __init__(self, path, bus, name, size, desc, serial, model):
        super(Device, self).__init__()
        vals = [path, bus, name, size, desc, serial, model]
        props = ["path", "bus", "name", "size", "desc", "serial", "model"]
        for prop, val in zip(props, vals):
            self.__dict__[prop] = val


class Swap(base.Base):
    def calculcate_default_size(self, overcommit):
        from ovirtnode.ovirtfunctions import calculate_swap_size
        return calculate_swap_size(overcommit)
