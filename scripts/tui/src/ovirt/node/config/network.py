#!/usr/bin/python
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

"""
Some convenience functions related to networking
"""


import logging

from ovirt.node.utils import AugeasWrapper as Augeas

LOGGER = logging.getLogger(__name__)


def iface(iface):
    """Retuns the config of an iface

    Args:
        iface: Interface to retrieve the config for
    Returns:
        A dict of (nic-name, nic-infos-dict)
    """
    LOGGER.debug("Getting configuration for '%s'" % iface)

    info = {}

    aug = Augeas()
    augbasepath = "/files/etc/sysconfig/network-scripts/ifcfg-%s"
    augdevicepath = augbasepath % iface

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
        LOGGER.warning("NIC config says the device is a VLAN, but the name" + \
                       "doesn't reflect that: %s (%s vs %s)" % (iface,
                                                            info["is_vlan"],
                                                            name_says_vlan))

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

    >>> len(nameservers()) > 0
    True
    """
    augpath = "/files/etc/resolv.conf/nameserver"
    return _aug_get_or_set(augpath, new_servers)


def timeservers(new_servers=None):
    """Get or set TIME servers

    >>> len(nameservers()) > 0
    True
    """
    augpath = "/files/etc/ntp.conf/server"
    return _aug_get_or_set(augpath, new_servers)
