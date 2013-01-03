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
    """
    def domain(self, domain=None):
        import ovirtnode.network as onet
        if domain:
            onet.set_nfsv4_domain(domain)
        return onet.get_current_nfsv4_domain()


class Devices(base.Base):
    """A class to retrieve available storage devices
    """
    def __init__(self, fake=False):
        super(Devices, self).__init__()
        if fake:
            self._devices = {
            "name": Device("bus", "name", "size", "desc", "serial", "model")
            }
        else:
            import ovirtnode.storage
            self._storage = ovirtnode.storage.Storage()

    def get_all(self):
        if self._devices:
            return self._devices
        from ovirtnode.ovirtfunctions import translate_multipath_device
        dev_names, disk_dict = self._storage.get_udev_devices()
        devices = {}
        for dev in dev_names:
            dev = translate_multipath_device(dev)
            if dev in devices:
                self.logger.warning("Device is already in dict: %s" % dev)
                continue
            if dev not in disk_dict:
                self.logger.warning("Device in names but not in dict: " +
                                    "%s" % dev)
                continue
            if dev == self.live_disk:
                self.logger.info("Ignoring device " +
                                 "%s it's the live media" % dev)
                continue
            infos = disk_dict[dev].split(",", 5)
            device = Device(*infos)
            device.name = os.path.basename(device.name).replace(" ", "")
            device.name = translate_multipath_device(device.name)
            if device.name in devices:
                self.logger.debug("Device with same name already " +
                                  "exists: %s" % device.name)
            devices[device.name] = device


class Device(base.Base):
    """Wrapps the information about a udev storage device
    """
    bus = None
    name = None
    size = None
    desc = None
    serial = None
    model = None

    def __init__(self, bus, name, size, desc, serial, model):
        super(Device, self).__init__()
        vals = [bus, name, size, desc, serial, model]
        props = ["bus", "name", "size", "desc", "serial", "model"]
        for prop, val in zip(props, vals):
            self.__dict__[prop] = val
