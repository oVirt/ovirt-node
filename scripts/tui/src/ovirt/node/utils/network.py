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


import os.path
import logging
import re

from ovirt.node.utils import AugeasWrapper as Augeas
import ovirt.node.utils.process as process

LOGGER = logging.getLogger(__name__)


#
# Try to use NM if available
#
_nm_client = None
try:
    from gi.repository import NetworkManager, NMClient
    import socket
    import struct
    NetworkManager
    _nm_client = NMClient.Client.new()
except Exception as e:
    LOGGER.warning("NetworkManager support disabled: " +
                   "NM Client not found (%s)" % e)
import gudev


class UnknownNicError(Exception):
    pass


def _query_udev_ifaces():
    client = gudev.Client(['net'])
    devices = client.query_by_subsystem("net")
    return [d.get_property("INTERFACE") for d in devices]


def _nm_ifaces():
    return [d.get_iface() for d in _nm_client.get_devices()]


def is_nm_managed(iface):
    """Wether an intreface is managed by NM or not (if it's running)
    """
    return _nm_client and iface in _nm_ifaces()


def all_ifaces():
    return _query_udev_ifaces()


def iface_informations(ifaces, with_live=False):
    """Retuns all system NICs (via udev)

    >>> infos = _collect_nic_informations(_query_udev_ifaces())
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
                "vendor": d.get_property("ID_VENDOR_FROM_DATABASE") \
                          or "unkown",
                "devtype": d.get_property("DEVTYPE") or "unknown",
                "devpath": d.get_property("DEVPATH")
               }

        infos[info["name"]] = info

    # Check if we cover all req. NICs
    unknown_ifaces = (set(ifaces) - set(infos))
    if unknown_ifaces != set():
        raise Exception("Couldn't gather informations for unknown NICs: %s" %
                        unknown_ifaces)

    _infos = {}
    for name, info in {k: v for k, v in infos.items() if k in ifaces}.items():
        LOGGER.debug("Getting additional information for '%s'" % name)

        # Driver
        driver_symlink = "/sys/class/net/%s/device/driver" % name
        driver = "unknown"
        if os.path.islink(driver_symlink):
            try:
                driver = os.path.basename(os.readlink(driver_symlink))
            except Exception as e:
                LOGGER.warning(("Exception %s while reading driver " +
                                "of '%s' from '%s'") % (e, name,
                                                        driver_symlink))
        info["driver"] = driver

        hwaddr = "unkown"
        with open("/sys/class/net/%s/address" % name) as macfile:
            hwaddr = macfile.read().strip()
        info["hwaddr"] = hwaddr

        aug = Augeas()
        augbasepath = "/files/etc/sysconfig/network-scripts/ifcfg-%s"
        augdevicepath = augbasepath % name

        # Type
        info["type"] = aug.get(augdevicepath + "/TYPE")
        if os.path.exists("/sys/class/net/%s/bridge" % name):
            info["type"] = "bridge"

        # Bootprotocol
        info["bootproto"] = aug.get(augdevicepath + "/BOOTPROTO")
        for p in ["IPADDR", "NETMASK", "GATEWAY"]:
            info[p.lower()] = aug.get(augdevicepath + "/" + p)

        # FIXME IPv6

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

        if with_live:
            info.update(_collect_live_informations(name))

        _infos[name] = info

    return _infos


def _collect_live_informations(iface):
    LOGGER.debug("Gathering live informations for '%s'" % iface)
    info = {}

    # Current IP addresses
    info["addresses"] = nic_ip_addresses(iface)

    # Current link state
    info["link_detected"] = nic_link_detected(iface)

    return info


def relevant_ifaces(filter_bridges=True, filter_vlans=True):
    """Retuns relevant system NICs (via udev)

    Filters out
    - loop
    - bonds
    - vnets
    - bridges
    - sit
    - vlans

    >>> "lo" in relevant_ifaces()
    False

    >>> "eth0" in relevant_ifaces() or "em1" in relevant_ifaces()
    True

    Args:
        filter_bridges: If bridges shall be filtered out too
        filter_vlans: If vlans shall be filtered out too
    Returns:
        List of strings, the NIC names
    """
    valid_name = lambda n: not ( \
            n == "lo" or \
            n.startswith("bond") or \
            n.startswith("sit") or \
            n.startswith("vnet") or \
            n.startswith("tun") or \
            n.startswith("wlan") or \
            (filter_vlans and ("." in n)))
    valid_props = lambda i, p: (filter_bridges and (p["type"] == "bridge"))

    relevant_ifaces = [iface for iface in all_ifaces() if valid_name(iface)]
#    relevant_ifaces = {iface: props for iface, props \
#                     in _collect_nic_informations(relevant_ifaces).items() \
#                     if valid_props(iface, props)}

    irrelevant_names = set(all_ifaces()) - set(relevant_ifaces)
    LOGGER.debug("Irrelevant interfaces: %s" % irrelevant_names)
    LOGGER.debug("Relevant interfaces: %s" % relevant_ifaces)

    return relevant_ifaces


def node_nics(with_live=False):
    """Returns Node's NIC model.
    This squashes nic, bridge and vlan informations.

    >>> node_nics() != None
    True
    """
    all_nics = relevant_ifaces(filter_bridges=False, filter_vlans=False)
    all_nics = iface_informations(all_nics, with_live)

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
            for k in ["bootproto", "ipaddr", "netmask", "gateway"]:
                if k in bridge:
                    info[k] = bridge[k]
        node_nics[name] = info

    for name in vlans:
        info = all_nics[name]
        if info["vlanid"]:
            node_nics[info["parent"]]["vlanid"] = info["vlanid"][0]

    LOGGER.debug("Node NICs: %s" % node_nics)

    return node_nics


def node_bridge(with_live=False):
    """Returns the main bridge of this node

    Returns:
        Bridge of this node
    """

    all_nics = relevant_ifaces(filter_bridges=False, filter_vlans=False)
    all_nics = iface_informations(all_nics, with_live)

    bridges = [nic for nic, info in all_nics.items() \
               if info["type"] == "bridge"]

    if len(bridges) != 1:
        LOGGER.warning("Expected exactly one bridge: %s" % bridges)

    return bridges[0]


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


def nic_link_detected(iface):
    """Determin if L1 is up on a given interface

    >>> nic_link_detected("lo")
    True

    >>> iface = all_ifaces()[0]
    >>> cmd = "ip link set dev {dev} up ; ip link show {dev}".format(dev=iface)
    >>> has_carrier = "LOWER_UP" in process.pipe(cmd, without_retval=True)
    >>> has_carrier == nic_link_detected(iface)
    True

    Args:
        iface: The interface to be checked
    Returns:
        True if L1 (the-link-is-up) is detected (depends on driver support)
    """

    if iface not in all_ifaces():
        raise UnknownNicError("Unknown network interface: '%s'" % iface)

    if is_nm_managed(iface):
        try:
            device = _nm_client.get_device_by_iface(iface)
            if device:
                return device.get_carrier()
        except:
            LOGGER.debug("Failed to retrieve carrier with NM")

    # Fallback
    has_carrier = False
    try:
        with open("/sys/class/net/%s/carrier" % iface) as c:
            content = c.read()
            has_carrier = "1" in content
    except:
        LOGGER.debug("Carrier down for %s" % iface)
    return has_carrier


def nic_ip_addresses(iface, families=["inet", "inet6"]):
    """Get IP addresses for an iface

    FIXME NM client.get_device_by_iface(iface).get_ip?_config()
    """
    if iface not in all_ifaces():
        raise UnknownNicError("Unknown network interface: '%s'" % iface)

    addresses = {f: None for f in families}

    if False: # FIXME to hackish to convert addr - is_nm_managed(iface):
        device = _nm_client.get_device_by_iface(iface)
        LOGGER.debug("Got '%s' for '%s'" % (device, iface))
        if device:
            for family, cfgfunc, sf in [
                ("inet", device.get_ip4_config, socket.AF_INET),
                ("inet6", device.get_ip6_config, socket.AF_INET6)]:
                cfg = cfgfunc()
                if not cfg:
                    LOGGER.debug("No %s configuration for %s" % (family,
                                                                 iface))
                    break
                addrs = cfg.get_addresses()
                addr = addrs[0].get_address() if len(addrs) > 0 else None
                addresses[family] = _nm_address_to_str(sf, addr) if addr \
                                                                 else None
        return addresses

    # Fallback
    cmd = "ip -o addr show {dev}".format(dev=iface)
    for line in process.pipe(cmd, without_retval=True).split("\n"):
        token = re.split("\s+", line)
        if re.search("\sinet[6]?\s", line):
            addresses[token[2]] = token[3]

    return addresses


def _nm_address_to_str(family, ipaddr):
    if family == socket.AF_INET:
        packed = struct.pack('L', ipaddr)
    elif family == socket.AF_INET6:
        packed = ipaddr
    return socket.inet_ntop(family, packed)


def networking_status(iface=None):
    status = "Not connected"

    iface = iface or node_bridge()
    addresses = nic_ip_addresses(iface)
    has_address = any([a != None for a in addresses.values()])

    if nic_link_detected(iface) and has_address:
        status = "Connected"

    summary = (status, iface, addresses)
    LOGGER.debug(summary)
    return summary
