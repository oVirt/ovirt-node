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
from ovirt.node import base, utils, config
import glob
import gudev
import logging
import os.path
import ovirt.node.config.network
import ovirt.node.utils.fs
import ovirt.node.utils.process as process
import re
import socket
import struct

"""
Some convenience functions related to networking
"""

LOGGER = logging.getLogger(__name__)

#
# Try to use NM if available
# FIXME we need to migrte to GUdev at some poit to make it really work
#
_nm_client = None
try:
    # pylint: disable-msg=E0611
    from gi.repository import NetworkManager, NMClient  # @UnresolvedImport
    # pylint: enable-msg=E0611
    NetworkManager
    _nm_client = NMClient.Client.new()
    LOGGER.info("NetworkManager support via GI (fast-path)")
except Exception as e:
    LOGGER.info("NetworkManager support disabled: " +
                "NM Client not found (%s)" % e)


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

def is_configured():
    return any(key["bootproto"] is not None for key in node_nics().values())

def iface_information(iface, with_slow=True):
    """Retuns all system NICs (via udev)

    FIXME move into NIC

    Args:
        nics: List of NIC names
    Returns:
        A dict of (nic-name, nic-infos-dict)
    """
    info = None

    client = gudev.Client(['net'])
    for d in client.query_by_subsystem("net"):
#        assert d.has_property("ID_VENDOR_FROM_DATABASE"), \
#                "udev informations are incomplete (udevadm re-trigger?)"

        uinfo = {"name": d.get_property("INTERFACE"),
                 "vendor": d.get_property("ID_VENDOR_FROM_DATABASE")
                 or "unkown",
                 "devtype": d.get_property("DEVTYPE") or "unknown",
                 "devpath": d.get_property("DEVPATH")
                 }

        if uinfo["name"] == iface:
            info = uinfo

    assert info, "Unknown nic %s" % iface

    LOGGER.debug("Getting live information for '%s'" % iface)

    # Driver
    driver_symlink = "/sys/class/net/%s/device/driver" % iface
    driver = "unknown"
    if os.path.islink(driver_symlink):
        try:
            driver = os.path.basename(os.readlink(driver_symlink))
        except Exception as e:
            LOGGER.warning(("Exception %s while reading driver " +
                            "of '%s' from '%s'") % (e, iface, driver_symlink))
    info["driver"] = driver

    # Hwaddr
    hwaddr = "unkown"
    hwfilename = "/sys/class/net/%s/address" % iface
    hwaddr = ovirt.node.utils.fs.get_contents(hwfilename).strip()
    info["hwaddr"] = hwaddr

    # Check bridge
    if os.path.exists("/sys/class/net/%s/bridge" % iface):
        info["type"] = "bridge"

    # Check vlan
    if len(glob.glob("/proc/net/vlan/%s" % iface)) > 0:
        info["type"] = "vlan"

    if "type" not in info:
        devtype = info["devtype"]
        LOGGER.warning(("Type of %s still unknown, using devtype " +
                        "%s") % (iface, devtype))
        info["type"] = devtype

    if with_slow:
        info.update(_slow_iface_information(iface))

    return info


def _slow_iface_information(iface):
    info = {}

    nic = NIC(iface)
    # Current IP addresses
    info["addresses"] = nic.ip_addresses()

    # Current link state
    info["link_detected"] = nic.has_link()

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
    valid_name = lambda n: not (n == "lo" or
                                n.startswith("bond") or
                                n.startswith("sit") or
                                n.startswith("vnet") or
                                n.startswith("tun") or
                                n.startswith("wlan") or
                                n.startswith("virbr") or
                                (filter_vlans and ("." in n)))
# FIXME!!!
#    valid_props = lambda i, p: (filter_bridges and (p["type"] != "bridge"))

    relevant_ifaces = [iface for iface in all_ifaces() if valid_name(iface)]
#    relevant_ifaces = {iface: iface_information(iface) for iface \
#                       in relevant_ifaces \
#                       if valid_props(iface, iface_information(iface, False))}

    irrelevant_names = set(all_ifaces()) - set(relevant_ifaces)
    LOGGER.debug("Irrelevant interfaces: %s" % irrelevant_names)
    LOGGER.debug("Relevant interfaces: %s" % relevant_ifaces)

    return relevant_ifaces


def node_nics():
    """Returns Node's NIC model.
    This squashes nic, bridge and vlan informations.

    All valid NICs of the system are returned, live and cfg informations merged
    into one dict.
    A NIC is "Configured" if itself or a vlan child is a member of a bridge.
    If a NIC is configured, merge the info+cfg of the bridge into the slave.
    If the slave is a vlan NIC set the vlanidof the parent device according to
    this vlan NICs id.

    >>> node_nics() != None
    True
    """
    all_ifaces = relevant_ifaces(filter_bridges=False, filter_vlans=False)
    all_infos = {i: iface_information(i) for i in all_ifaces}
    all_cfgs = {i: ovirt.node.config.network.iface(i) for i in all_ifaces}

    bridges = [nic for nic, info in all_infos.items()
               if info["type"] == "bridge"]
    vlans = [nic for nic, info in all_infos.items()
             if info["type"] == "vlan"]
    nics = [nic for nic, info in all_infos.items()
            if info["name"] not in bridges + vlans]

    LOGGER.debug("Bridges: %s" % bridges)
    LOGGER.debug("VLANs: %s" % vlans)
    LOGGER.debug("NICs: %s" % nics)

    node_infos = {}
    slaves = []
    # Build dict with all NICs
    for iface in nics:
        LOGGER.debug("Adding physical NIC: %s" % iface)
        info = all_infos[iface]
        info.update(all_cfgs[iface])
        node_infos[iface] = info
        if info["bridge"]:
            LOGGER.debug("Physical NIC '%s' is slave of '%s'" %
                         (iface, info["bridge"]))
            slaves.append(iface)

    # Merge informations of VLANs into parent
    for iface in vlans:
        info = all_infos[iface]
        info.update(all_cfgs[iface])
        parent = info["vlan_parent"]
        LOGGER.debug("Updating VLANID of '%s': %s" % (parent, info["vlanid"]))
        node_infos[parent]["vlanid"] = info["vlanid"]
        if info["bridge"]:
            LOGGER.debug("VLAN NIC '%s' is slave of '%s'" %
                         (iface, info["bridge"]))
            slaves.append(iface)

    for slave in slaves:
        info = all_infos[slave]
        info.update(all_cfgs[slave])
        bridge = info["bridge"]
        LOGGER.debug("Found slave for bridge '%s': %s" % (bridge, slave))
        bridge_cfg = all_cfgs[bridge]
        dst = slave
        if info["is_vlan"]:
            dst = info["vlan_parent"]
        for k in ["bootproto", "ipaddr", "netmask", "gateway"]:
            LOGGER.debug("Merging cfg %s from bridge %s into device %s" %
                         (k, bridge, slave))
            node_infos[dst][k] = bridge_cfg[k] if k in bridge_cfg else None

    LOGGER.debug("Node NICs: %s" % node_infos)

    return node_infos


class NIC(base.Base):
    def __init__(self, iface):
        self.iface = iface
        super(NIC, self).__init__()

    def exists(self):
        """If this NIC currently exists in the system
        """
        return self.iface in all_ifaces()

    def has_link(self):
        """Determin if L1 is up on a given interface

        >>> NIC("lo").has_link()
        True

        >>> iface = all_ifaces()[0]
        >>> cmd = "ip link set dev {dev} up ;"
        >>> cmd += "ip link show {dev}".format(dev=iface)
        >>> has_carrier = "LOWER_UP" in process.pipe(cmd)
        >>> has_carrier == NIC(iface).has_link()
        True

        Args:
            iface: The interface to be checked
        Returns:
            True if L1 (the-link-is-up) is detected (depends on driver support)
        """

        if not self.exists():
            raise UnknownNicError("Unknown network interface: '%s'" %
                                  self.iface)

        if is_nm_managed(self.iface):
            try:
                device = _nm_client.get_device_by_iface(self.iface)
                if device:
                    return device.get_carrier()
            except:
                LOGGER.debug("Failed to retrieve carrier with NM")

        # Fallback
        has_carrier = False
        try:
            with open("/sys/class/net/%s/carrier" % self.iface) as c:
                content = c.read()
                has_carrier = "1" in content
        except:
            LOGGER.debug("Carrier down for %s" % self.iface)
        return has_carrier

    def ipv4_address(self):
        return self.ip_addresses(["inet"])["inet"]

    def ipv6_address(self):
        return self.ip_addresses(["inet6"])["inet6"]

    def ip_addresses(self, families=["inet", "inet6"]):
        """Get IP addresses for an iface

        FIXME NM client.get_device_by_iface(iface).get_ip?_config()
        """
        if not self.exists():
            raise UnknownNicError("Unknown network interface: '%s'" %
                                  self.iface)

        addresses = {f: (None, None) for f in families}

        if False:
            # FIXME to hackish to convert addr - is_nm_managed(iface):
            device = _nm_client.get_device_by_iface(self.iface)
            LOGGER.debug("Got '%s' for '%s'" % (device, self.iface))
            if device:
                for family, cfgfunc, sf in [("inet", device.get_ip4_config,
                                             socket.AF_INET),
                                            ("inet6", device.get_ip6_config,
                                             socket.AF_INET6)]:
                    cfg = cfgfunc()
                    if not cfg:
                        LOGGER.debug("No %s configuration for %s" %
                                     (family, self.iface))
                        break
                    addrs = cfg.get_addresses()
                    addr = addrs[0].get_address() if len(addrs) > 0 else None
                    addresses[family] = _nm_address_to_str(sf, addr) if addr \
                        else None
            return addresses

        # Fallback
        cmd = "ip -o addr show {iface}".format(iface=self.iface)
        for line in process.pipe(cmd).split("\n"):
            token = re.split("\s+", line)
            if re.search("\sinet[6]?\s", line):
                addr, mask = token[3].split("/")
                family = token[2]
                if family == "inet":
                    mask = calcDottedNetmask(mask)
                addresses[family] = IPAddress(addr, mask)

        return addresses

    def vlanid(self):
        vlanids = []
        vcfg = "/proc/net/vlan/config"
        pat = re.compile("([0-9]+)\s*\|\s*%s$" % self.iface)
        if os.path.exists(vcfg):
            try:
                with open(vcfg) as f:
                    for line in f:
                        r = pat.search(line)
                        if r:
                            vlanids.append(r.groups[0])
            except IOError as e:
                self.logger.warning("Could not read vlan config: %s" %
                                    e.message)
        if len(vlanids) > 1:
            self.logger.info("Found more than one (expected) vlan: %s" %
                             vlanids)
        return vlanids[0] if vlanids else None

    def __str__(self):
        return "<NIC iface='%s' at %s" % (self.iface, hex(id(self)))


class Routes(base.Base):
    def default(self):
        """Return the default gw of the system
        """
        if _nm_client:
            return self._default_nm()
        return self._default_fallback()

    def _default_fallback(self):
        # Fallback
        gw = None
        cmd = "ip route list"
        for line in process.pipe(cmd).split("\n"):
            token = re.split("\s+", line)
            if line.startswith("default via"):
                gw = token[2]
        return gw

    def _default_nm(self):
        active_connections = _nm_client.get_active_connections()
        default_connection = [c for c in active_connections
                              if c.get_default()][0]
        ip4_config = default_connection.get_ip4_config()
        ip4_gateway = ip4_config.get_addresses()[0].get_gateway()
        return _nm_address_to_str(socket.AF_INET, ip4_gateway)


def _nm_address_to_str(family, ipaddr):
    """Convert the binary representation of NMs IPaddresse into its textual
    representation

    Args:
        family: socket.AF_INET or socket.F_INET6
        ipaddr: The binary (long) representation of the IP
    Returns:
        Textual representation of the binary IP Addr
    """
    if family == socket.AF_INET:
        packed = struct.pack('L', ipaddr)
    elif family == socket.AF_INET6:
        packed = ipaddr
    return socket.inet_ntop(family, packed)


def networking_status(iface=None):
    status = "Not connected"

    iface = iface or config.network.node_bridge()
    addresses = []
    if iface:
        nic = NIC(iface)
        addresses = nic.ip_addresses()
        has_address = any([a is not None for a in addresses.values()])

        if nic.has_link():
            status = "Connected (Link only, no IP)"
        if has_address:
            status = "Connected"

    summary = (status, iface, addresses)
    LOGGER.debug(summary)
    return summary


def calcDottedNetmask(mask):
    """
    http://code.activestate.com/recipes/576483/
    >>> calcDottedNetmask(24)
    '255.255.255.0'
    """
    mask = int(str(mask))
    bits = 0xffffffff ^ (1 << 32 - mask) - 1
    return socket.inet_ntoa(struct.pack('>I', bits))


class IPAddress(base.Base):
    def __init__(self, address, netmask):
        self.address = address
        self.netmask = netmask

    def __str__(self):
        return str(self.address)

    def items(self):
        return (self.address, self.netmask)


def hostname(new_hostname=None):
    """Retrieve/Set the systems hostname

    Args:
        new_hostname: (Optional) new hostname to be set
    Returns:
        The current hostname
    """
    if new_hostname:
        utils.process.call("hostname %s" % new_hostname)
    return utils.process.pipe("hostname").strip()


# http://git.fedorahosted.org/cgit/smolt.git/diff/?
# id=aabd536e21f362f7bac18a2dbc1a55cbdb9ae385
def reset_resolver():
    '''Attempt to reset the system hostname resolver.
    returns 0 on success, or -1 if an error occurs.'''
    import ctypes
    try:
        resolv = ctypes.CDLL("libresolv.so.2")
        r = resolv.__res_init()
    except (OSError, AttributeError):
        print "Warning: could not find __res_init in libresolv.so.2"
        r = -1
    return r
