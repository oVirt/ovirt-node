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

import gudev
import os.path
import logging
from ovirt.node.utils import AugeasWrapper as Augeas

LOGGER = logging.getLogger(__name__)


def _query_udev_nics():
    client = gudev.Client(['net'])
    devices = client.query_by_subsystem("net")
    return [d.get_property("INTERFACE") for d in devices]


def all_nics():
    """Retuns all system NICs (via udev)

    >>> "lo" in all_nics()
    True

    Returns:
        Dict with NIC (name, info) mappings for all known NICS
    """
    return _collect_nic_informations(_query_udev_nics())


def _collect_nic_informations(nics):
    """Collects all NIC relevant informations for a list of NICs

    >>> infos = _collect_nic_informations(_query_udev_nics())
    >>> "lo" in infos
    True
    >>> "driver" in infos["lo"]
    True
    >>> infos["lo"]["driver"]
    'unknown'

    Args:
        nics: List of NIC names
    Returns:
        A dict of (nic-name, nic-infos-dict)
    """
    infos = {}

    client = gudev.Client(['net'])
    for d in client.query_by_subsystem("net"):
#        assert d.has_property("ID_VENDOR_FROM_DATABASE"), \
#                "udev informations are incomplete (udevadm re-trigger?)"

        info = {"name": d.get_property("INTERFACE"),
                "vendor": d.get_property("ID_VENDOR_FROM_DATABASE") or "unkown",
                "devtype": d.get_property("DEVTYPE") or "unknown",
                "devpath": d.get_property("DEVPATH")
               }

        infos[info["name"]] = info

    # Check if we cover all req. NICs
    unknown_nics = (set(nics) - set(infos))
    if unknown_nics != set():
        raise Exception("Couldn't gather informations for unknown NICs: %s" %
                        unknown_nics)

    for name, info in infos.items():
        LOGGER.debug("Getting additional information for '%s'" % name)

        # Driver
        driver_symlink = "/sys/class/net/%s/device/driver" % name
        driver = "unknown"
        if os.path.islink(driver_symlink):
            try:
                driver = os.path.basename(os.readlink(driver_symlink))
            except Exception as e:
                LOGGER.warning("Exception while reading driver " +
                               "of '%s' from '%s'" % (name, driver_symlink))
        infos[name]["driver"] = driver


        hwaddr = "unkown"
        with open("/sys/class/net/%s/address" % name) as macfile:
            hwaddr = macfile.read().strip()
        infos[name]["hwaddr"] = hwaddr

        aug = Augeas()
        augbasepath = "/files/etc/sysconfig/network-scripts/ifcfg-%s"
        augdevicepath = augbasepath % name

        # Bootprotocol
        info["type"] = aug.get(augdevicepath + "/TYPE")
        if os.path.exists("/sys/class/net/%s/bridge" % name):
            info["type"] = "bridge"

        # Bootprotocol
        info["bootproto"] = aug.get(augdevicepath + "/BOOTPROTO")

        # Parent bridge
        info["bridge"] = aug.get(augdevicepath + "/BRIDGE")

        # VLAN
        info["is_vlan"] = aug.get(augdevicepath + "/VLAN") is not None
        if info["is_vlan"] != "." in name:
            LOGGER.warning("NIC config says VLAN, name doesn't reflect " + \
                           "that: %s" % name)
        if info["is_vlan"]:
            parts = name.split(".")
            info["vlanid"] = parts[-1:]
            info["parent"] = ".".join(parts[:-1])

            info["type"] = "vlan"


    return infos


def relevant_nics(filter_bridges=True, filter_vlans=True):
    """Retuns relevant system NICs (via udev)

    Filters out
    - loop
    - bonds
    - vnets
    - bridges
    - sit
    - vlans

    >>> "lo" in relevant_nics()
    False

    >>> "eth0" in relevant_nics() or "em1" in relevant_nics()
    True

    Args:
        filter_bridges: If bridges shall be filtered out too
        filter_vlans: If vlans shall be filtered out too
    Returns:
        List of strings, the NIC names
    """
    is_irrelevant = lambda n, p: ( \
            n == "lo" or \
            n.startswith("bond") or \
            n.startswith("sit") or \
            n.startswith("vnet") or \
            n.startswith("tun") or \
            n.startswith("wlan") or \
            (("." in n) and filter_vlans) or \
            ((p["type"] == "bridge") and filter_bridges))

    relevant_nics = {n: p for n, p in all_nics().items() \
                          if not is_irrelevant(n, p)}

    irrelevant_names = set(all_nics().keys()) - set(relevant_nics.keys())
    LOGGER.debug("Irrelevant interfaces: %s" % irrelevant_names)

    return relevant_nics


def node_nics():
    """Returns Node's NIC model.
    This squashes nic, bridge and vlan informations.

    >>> node_nics() != None
    True
    """
    all_nics = relevant_nics(filter_bridges=False, filter_vlans=False)

    bridges = [nic for nic, info in all_nics.items() \
               if info["type"] == "bridge"]
    vlans = [nic for nic, info in all_nics.items() \
             if info["type"] == "vlan"]
    nics = [nic for nic, info in all_nics.items() \
            if info["name"] not in bridges + vlans]

    LOGGER.debug("Bridges: %s" % bridges)
    LOGGER.debug("VLANs: %s" % vlans)
    LOGGER.debug("NICs: %s" % nics)

    node_nics = {}
    for name in nics:
        info = all_nics[name]
        if info["bridge"]:
            bridge = all_nics[info["bridge"]]
            info["bootproto"] = bridge["bootproto"]
        node_nics[name] = info

    for name in vlans:
        info = all_nics[name]
        if info["vlanid"]:
            node_nics[info["parent"]]["vlanid"] = info["vlanid"][0]

    LOGGER.debug("Node NICs: %s" % node_nics)

    return node_nics


def _aug_get_or_set(augpath, new_servers=None):
    """Get or set some servers
    """
    aug = Augeas()

    servers = []
    for path in aug.match(augpath):
        servers.append(aug.get(path))

    if new_servers:
        itempath = lambda idx: "%s[%d]" % (augpath, idx+1)
        for idx, server in enumerate(new_servers):
            aug.set(itempath(idx), server)
        if len(servers) > len(new_servers):
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
