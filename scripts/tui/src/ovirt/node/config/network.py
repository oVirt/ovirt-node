#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# network.py - Copyright (C) 2012 Red Hat, Inc.
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
from ovirt.node import utils, base
from ovirt.node.utils import AugeasWrapper as Augeas
import logging
import os
import glob

"""
Some convenience functions related to networking
"""


LOGGER = logging.getLogger(__name__)


def iface(iface):
    """Retuns the config of an iface

    Args:
        iface: Interface to retrieve the config for
    Returns:
        A dict of (nic-name, nic-infos-dict)
    """
    LOGGER.debug("Getting configuration for '%s'" % iface)
    Augeas.force_reload()

    info = {}

    aug = Augeas()
    filepath = "/etc/sysconfig/network-scripts/ifcfg-%s" % iface
    augdevicepath = "/files%s" % filepath

    if not os.path.exists(filepath):
        LOGGER.debug("No config file %s" % filepath)

    # Type
    info["type"] = aug.get(augdevicepath + "/TYPE", True)

    # Bootprotocol
    info["bootproto"] = aug.get(augdevicepath + "/BOOTPROTO", True)

    # IPV4
    for p in ["IPADDR", "NETMASK", "GATEWAY"]:
        info[p.lower()] = aug.get(augdevicepath + "/" + p, True)

    # FIXME IPv6

    # Parent bridge
    info["bridge"] = aug.get(augdevicepath + "/BRIDGE", True)

    # VLAN
    info["is_vlan"] = aug.get(augdevicepath + "/VLAN", True) is not None
    name_says_vlan = "." in iface
    if info["is_vlan"] != name_says_vlan:
        LOGGER.warning("NIC config says the device is a VLAN, but the name" +
                       "doesn't reflect that: %s (%s vs %s)" % (iface,
                       info["is_vlan"], name_says_vlan))

    if info["is_vlan"] is True:
        parts = iface.split(".")
        vlanid = parts[-1:][0]
        info["vlanid"] = vlanid
        info["vlan_parent"] = ".".join(parts[:-1])

        info["type"] = "vlan"
        LOGGER.debug("Found VLAN %s on %s" % (str(vlanid), iface))
    else:
        info["vlanid"] = None

    return info


def _aug_get_or_set(augpath, new_servers=None):
    """Get or set some servers
    """
    aug = Augeas()

    servers = []
    for path in aug.match(augpath):
        servers.append(aug.get(path))

    if new_servers:
        itempath = lambda idx: "%s[%d]" % (augpath, idx + 1)
        for idx, server in enumerate(new_servers):
            LOGGER.debug("Setting server: %s" % server)
            aug.set(itempath(idx), server)
        if len(servers) > len(new_servers):
            LOGGER.debug("Less servers than before, removing old ones")
            for idx in range(len(servers) + 1, len(new_servers)):
                aug.remove(itempath(idx))
    return servers


def nameservers(new_servers=None):
    """Get or set DNS servers

    >>> import ovirt.node.utils.process as p
    >>> stdout = p.pipe("egrep '^nameserver' /etc/resolv.conf | wc -l")
    >>> len(nameservers()) == int(stdout)
    True
    """
    augpath = "/files/etc/resolv.conf/nameserver"
    return _aug_get_or_set(augpath, new_servers)


def timeservers(new_servers=None):
    """Get or set timeservers in the config files
    """
    augpath = "/files/etc/ntp.conf/server"
    return _aug_get_or_set(augpath, new_servers)


def hostname(new_hostname=None):
    """Get or set the current hostname in the config files
    """
    aug = utils.AugeasWrapper()
    augpath = "/files/etc/sysconfig/network/HOSTNAME"
    sys_hostname = None
    if new_hostname:
        aug.set(augpath, new_hostname)
        sys_hostname = utils.network.hostname(new_hostname)
    cfg_hostname = aug.get(augpath)

    if sys_hostname and (sys_hostname != cfg_hostname):
        # A trivial check: Check that the configured hostname equals the
        # configured one (only check if we are configuring a new hostname)
        raise RuntimeError(("A new hostname was configured (%s) but the " +
                            "systems hostname (%s) wasn't set accordingly.") %
                           (cfg_hostname, sys_hostname))

    return cfg_hostname


class Ifcfg(base.Base):
    """Object to access ifcfg-%ifname
    """
    bridge = None
    type = None
    bootproto = None
    ipaddr = None
    netmask = None
    gateway = None
    vlan = None
    device = None
    hwaddr = None
    onboot = None

    def __init__(self, iface):
        self.iface = iface
        self.aug = Augeas()
        self.load_properties()

    def load_properties(self):
        Augeas.force_reload()
        for p in ["bridge", "type", "bootproto", "ipaddr", "netmask",
                  "gateway", "vlan", "device", "onboot", "hwaddr"]:
            self.__dict__[p] = self.ifcfg_property(p.upper())

    def ifcfg_property(self, name):
        filepath = "/etc/sysconfig/network-scripts/ifcfg-%s" % self.iface
        augdevicepath = "/files%s" % filepath

        value = None
        if os.path.exists(filepath):
            value = self.aug.get("%s/%s" % (augdevicepath, name), True)
        else:
            LOGGER.debug("No config file %s" % filepath)

        return value


def ifaces():
    """Returns all configured ifaces
    """
    ifaces = []
    filepath = "/etc/sysconfig/network-scripts/ifcfg-"
    for fn in glob.glob("%s*" % filepath):
        iface = fn[len(filepath):]
        ifaces.append(iface)
    return ifaces


def node_bridge():
    """Return the configured bridge

    Returns:
        Ifname of a configured bridge or None if none is configured
    """
    bridge = None
    for iface in ifaces():
        nic = Ifcfg(iface)
        if nic.type == u"Bridge":
            bridge = iface
            break
    return bridge


def node_bridge_slave():
    """Returns the interface which is the slave of the configfured bridge
    """
    slave = None
    bridge = node_bridge()
    if bridge:
        for iface in ifaces():
            nic = Ifcfg(iface)
            if nic.bridge == bridge:
                slave = iface
                break
    return slave
