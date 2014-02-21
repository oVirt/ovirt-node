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
from ovirt.node import base, utils, config, valid, log
from ovirt.node.config.network import NicConfig
from ovirt.node.utils import fs
from ovirt.node.utils.fs import File
import glob
import gudev
import os.path
import ovirt.node.utils.fs
import ovirt.node.utils.process as process
import re
import socket
import struct
import shlex

"""
Some convenience functions related to networking
"""

LOGGER = log.getLogger(__name__)

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
    LOGGER.debug("NetworkManager support via GI (fast-path)")
except Exception as e:
    LOGGER.debug("NetworkManager support disabled: " +
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
    """A list of all network interfaces discovered by udev

    Returns:
        A list of all returned ifaces (names)
    """
    return _query_udev_ifaces()


class UdevNICInfo(base.Base):
    """Gather NIC infos form udev
    """
    _client = gudev.Client(['net'])
    _cached_device = None

    ifname = None

    def __init__(self, iface):
        super(UdevNICInfo, self).__init__()
        self.ifname = iface

    @property
    def _udev_device(self):
        if not self._cached_device:
            for d in self._client.query_by_subsystem("net"):
                if d.get_property("INTERFACE") == self.ifname:
                    self._cached_device = d

        if not self._cached_device:
            self.logger.debug("udev has no infos for %s" % self.ifname)

        return self._cached_device

    def __get_property(self, name):
        return self._udev_device.get_property(name) if self.exists() \
            else None

    def exists(self):
        return self._udev_device is not None

    @property
    def name(self):
        return self.__get_property("INTERFACE")

    @property
    def vendor(self):
        vendor = self.__get_property("ID_VENDOR_FROM_DATABASE")
        if not vendor:
            # fallback method for older udev versions
            try:
                dpath = self.__get_property("DEVPATH")
                pci_addr = dpath.split("/")[-3]
                cmd = ["lspci", "-m", "-s", pci_addr]
                lspci_out = process.pipe(cmd, check=True)
                # shelx needs str not unicode
                vendor = shlex.split(str(lspci_out))[2]
            except:
                self.logger.debug("Failed to fetch vendor name for %s" % dpath,
                                  exc_info=True)
        return vendor

    @property
    def devtype(self):
        return self.__get_property("DEVTYPE")

    @property
    def devpath(self):
        return self.__get_property("DEVPATH")


class SysfsNICInfo(base.Base):
    """Gather NIC infos fom sysfs
    """
    ifname = None

    def __init__(self, ifname):
        super(SysfsNICInfo, self).__init__()
        self.ifname = ifname

    def exists(self):
        return os.path.exists("/sys/class/net/%s" % self.ifname)

    @property
    def driver(self):
        driver_symlink = "/sys/class/net/%s/device/driver" % self.ifname
        driver = "unknown"
        if os.path.islink(driver_symlink):
            try:
                driver = os.path.basename(os.readlink(driver_symlink))
            except Exception as e:
                self.logger.warning(("Exception %s while reading driver " +
                                     "of '%s' from '%s'") % (e, self.ifname,
                                                             driver_symlink))
        return driver

    @property
    def hwaddr(self):
        hwaddr = None
        if self.exists():
            hwfilename = "/sys/class/net/%s/address" % self.ifname
            hwaddr = ovirt.node.utils.fs.get_contents(hwfilename).strip()
        return hwaddr

    @property
    def systype(self):
        systype = "ethernet"

        if self.is_vlan():
            # Check if vlan
            systype = "vlan"

        elif self.is_bridge():
            # Check if bridge
            systype = "bridge"

        return systype

    def is_vlan(self):
        return len(glob.glob("/proc/net/vlan/%s" % self.ifname)) > 0

    def is_bridge(self):
        return os.path.exists("/sys/class/net/%s/bridge" % self.ifname)


class NIC(base.Base):
    """Offers an API tp common NIC related functions is also a model for any
    logical NIC.
    """
    ifname = None
    vendor = None
    driver = None
    hwaddr = None
    typ = None
    config = None

    def __init__(self, ifname):
        super(NIC, self).__init__()
        self.ifname = ifname

        self._udevinfo = UdevNICInfo(self.ifname)
        self.vendor = self._udevinfo.vendor

        self._sysfsinfo = SysfsNICInfo(self.ifname)
        self.driver = self._sysfsinfo.driver
        self.hwaddr = self._sysfsinfo.hwaddr

        self.config = NicConfig(ifname)
        self.typ = self._udevinfo.devtype or self._sysfsinfo.systype

    def exists(self):
        """If this NIC currently exists in the system

        >>> NIC("lo").exists()
        True
        """
        return self.ifname in all_ifaces()

    def is_configured(self):
        """If there is a configuration for this NIC
        """
        ipv4_configured = self.config.bootproto or self.config.ipaddr
        ipv6_configured = (self.config.dhcpv6c or self.config.ipv6_autoconf or
                           self.config.ipv6addr)
        return ipv4_configured or ipv6_configured

    def has_link(self):
        """Determin if L1 is up on a given interface

        >>> NIC("lo").has_link()
        True

        Args:
            ifname: The interface to be checked
        Returns:
            True if L1 (the-link-is-up) is detected (depends on driver support)
        """

        if not self.exists():
            raise UnknownNicError("Unknown network interface: '%s'" %
                                  self.ifname)

        if is_nm_managed(self.ifname):
            try:
                device = _nm_client.get_device_by_iface(self.ifname)
                if device:
                    return device.get_carrier()
            except:
                LOGGER.debug("Failed to retrieve carrier with NM")

        # Fallback
        has_carrier = False
        i = 5
        while i > 0:
            try:
                cmd = "ip link set dev {ifname} up".format(ifname=self.ifname)
                process.check_call(cmd, shell=True)
            except process.CalledProcessError:
                LOGGER.debug("Failed to set dev %s link up" % self.ifname)
            try:
                content = File("/sys/class/net/%s/carrier" % self.ifname).\
                    read()
                has_carrier = "1" in content
            except:
                LOGGER.debug("Carrier down for %s" % self.ifname)
            if not has_carrier:
                import time
                time.sleep(1)
                i -= 1
            else:
                break
        return has_carrier

    def ipv4_address(self):
        return self.ip_addresses(["inet"])["inet"]

    def ipv6_address(self):
        return self.ip_addresses(["inet6"])["inet6"]

    def ip_addresses(self, families=["inet", "inet6"]):
        """Get IP addresses for an ifname

        FIXME NM _client.get_device_by_iface(ifname).get_ip?_config()
        """
        if not self.exists():
            raise UnknownNicError("Unknown network interface: '%s'" %
                                  self.ifname)

        addresses = dict((f, IPAddress(None, None)) for f in families)

        if False:
            # FIXME to hackish to convert addr - is_nm_managed(ifname):
            device = _nm_client.get_device_by_iface(self.ifname)
            LOGGER.debug("Got '%s' for '%s'" % (device, self.ifname))
            if device:
                for family, cfgfunc, sf in [("inet", device.get_ip4_config,
                                             socket.AF_INET),
                                            ("inet6", device.get_ip6_config,
                                             socket.AF_INET6)]:
                    cfg = cfgfunc()
                    if not cfg:
                        LOGGER.debug("No %s configuration for %s" %
                                     (family, self.ifname))
                        break
                    addrs = cfg.get_addresses()
                    addr = addrs[0].get_address() if len(addrs) > 0 else None
                    addresses[family] = _nm_address_to_str(sf, addr) if addr \
                        else None
            return addresses

        # Fallback
        cmd = "ip -o addr show {ifname}".format(ifname=self.ifname)
        for line in process.pipe(cmd, shell=True).split("\n"):
            matches = re.search("\s(inet[6]?)\s(.+)/([^\s]+)"
                                ".*scope ([^\s]+).*", line)
            if matches and matches.groups():
                family, addr, mask, scope = matches.groups()
                if family not in families:
                    continue
                if family == "inet":
                    mask = calcDottedNetmask(mask)
                if scope == "global" or addresses[family].address is None:
                    addresses[family] = IPAddress(addr, mask, scope)

        return addresses

    def has_vlans(self):
        """If this nic has associated vlan ids
        """
        return len(self.vlanids()) > 0

    def is_vlan(self):
        """if this nic is a vlan nic
        """
        vlans = Vlans()
        return vlans.is_vlan_device(self.ifname)

    def vlanids(self):
        """Return all vlans of this nic
        """
        vlans = Vlans()
        return vlans.vlans_for_nic(self.ifname)

    def identify(self):
        """Flash the lights of this NIC to identify it
        """
        utils.process.call(["ethtool", "--identify", self.ifname, "10"])

    def __str__(self):
        return self.build_str(["ifname"])

    def __repr__(self):
        return self.__str__()


class BridgedNIC(NIC):
    """A class to handle the legacy/default bridge-setup used by Node
    """
    bridge_nic = None
    slave_nic = None

    def __init__(self, snic):
        super(BridgedNIC, self).__init__(snic.ifname)
        self.slave_nic = snic
        self.bridge_nic = NIC(snic.config.bridge)
        self.config = self.bridge_nic.config

    def exists(self):
        return self.bridge_nic.exists()

    def is_configured(self):
        return self.bridge_nic.is_configured()

    def has_link(self):
        return self.slave_nic.has_link()

    def ipv4_address(self):
        return self.bridge_nic.ipv4_address()

    def ipv6_address(self):
        return self.bridge_nic.ipv6_address()

    def ip_addresses(self, families=["inet", "inet6"]):
        return self.bridge_nic.ip_addresses(families=families)

    def is_vlan(self):
        return self.slave_nic.is_vlan()

    def has_vlans(self):
        return self.slave_nic.has_vlans()

    def vlanids(self):
        return self.slave_nic.vlanids()

    def identify(self):
        self.slave_nic.identify()

    def __str__(self):
        pairs = {"bridge": self.bridge_nic,
                 "slave": self.slave_nic}
        return self.build_str(["ifname"], additional_pairs=pairs)


class TaggedNIC(NIC):
    """A class to provide easy access to tagged NICs
    """
    vlan_nic = None
    parent_nic = None

    def __init__(self, parent_nic, vlanid):
        """A unified API for tagged NICs
        Args:
            vnic: A NIC instance pointing to the tagged part of a device
        """
        slave_ifname = "%s.%s" % (parent_nic.ifname, vlanid)
        super(TaggedNIC, self).__init__(parent_nic.ifname)
        self.parent_nic = parent_nic
        self.vlan_nic = NIC(slave_ifname)
        self.config = self.vlan_nic.config

    @staticmethod
    def _parent_and_vlanid_from_name(ifname):
        """Parse parent and vlanid from a ifname

        >>> TaggedNIC._parent_and_vlanid_from_name("ens1.0")
        ('ens1', '0')

        Args:
            ifname
        Returns:
            A tuple (parent ifname, vlanid)
        """
        parts = ifname.split(".")
        return (".".join(parts[:-1]), parts[-1:][0])

    def exists(self):
        return self.vlan_nic.exists()

    def is_configured(self):
        return self.vlan_nic.is_configured()

    def ipv4_address(self):
        return self.vlan_nic.ipv4_address()

    def ipv6_address(self):
        return self.vlan_nic.ipv6_address()

    def ip_addresses(self, families=["inet", "inet6"]):
        return self.vlan_nic.ip_addresses(families=families)

    def is_vlan(self):
        return True

    def has_vlans(self):
        raise RuntimeError("Nested tagging is not allowed. Is it?")

    def identify(self):
        self.parent_nic.identify()

    def __str__(self):
        pairs = {"vlan": self.vlan_nic.ifname,
                 "parent": self.ifname}
        return self.build_str(["ifname"], additional_pairs=pairs)


class BondedNIC(NIC):
    """A class to provide easy access to bonded NICs
    """
    slave_nics = None

    def __init__(self, master_nic, slave_nics=[]):
        """Handle snic like beeing a slave of a bond device
        """
        super(BondedNIC, self).__init__(master_nic.ifname)
        self.slave_nics = [NIC(n) for n in slave_nics]

    def identify(self):
        for slave in self.slave_nics:
            slave.identify()

    def __str__(self):
        return self.build_str(["ifname", "slave_nics"])


class NodeNetwork(base.Base):
    def all_ifnames(self):
        return all_ifaces()

    def relevant_ifnames(self, filter_bridges=True, filter_vlans=True,
                         filter_bonds=True):
        all_ifaces = self.all_ifnames()
        relevant_ifaces = self._filter_on_ifname(all_ifaces, filter_vlans,
                                                 filter_bonds, filter_bridges)
        irrelevant_names = set(all_ifaces) - set(relevant_ifaces)
        LOGGER.debug("Irrelevant interfaces: %s" % irrelevant_names)
        LOGGER.debug("Relevant interfaces: %s" % relevant_ifaces)

        return relevant_ifaces

    def _filter_on_ifname(self, ifnames, filter_vlans=True,
                          filter_bonds=True, filter_bridges=True):
        """Retuns relevant system NICs (via udev)

        Filters out
        - loop
        - bonds
        - vnets
        - bridges
        - sit
        - vlans
        - phy (wireless device)

        >>> names = ["bond007", "sit1", "vnet11", "tun0", "wlan1", "virbr0"]
        >>> names += ["ens1", "eth0", "phy0", "p1p7", "breth0", "ens1.42"]
        >>> model = NodeNetwork()
        >>> model._filter_on_ifname(names)
        ['ens1', 'eth0', 'p1p7']

        >>> model._filter_on_ifname(names, filter_bonds=False)
        ['bond007', 'ens1', 'eth0', 'p1p7']

        >>> model._filter_on_ifname(names, filter_bridges=False)
        ['ens1', 'eth0', 'p1p7', 'breth0']

        >>> model._filter_on_ifname(names, filter_vlans=False)
        ['ens1', 'eth0', 'p1p7', 'ens1.42']

        Args:
            filter_bridges: If bridges shall be filtered out too
            filter_vlans: If vlans shall be filtered out too
        Returns:
            List of strings, the NIC names
        """
        return [n for n in ifnames if not (n == "lo" or
                                           (filter_bonds and
                                            n.startswith("bond")) or
                                           (filter_bridges and
                                            n.startswith("br")) or
                                           (filter_vlans and
                                            ("." in n)) or
                                           n.startswith("sit") or
                                           n.startswith("vnet") or
                                           n.startswith("tun") or
                                           n.startswith("wlan") or
                                           n.startswith("virbr") or
                                           n.startswith("phy"))]

    def build_nic_model(self, ifname):
        mnet = config.defaults.Network().retrieve()
        mlayout = config.defaults.NetworkLayout().retrieve()
        mbond = config.defaults.NicBonding().retrieve()

        bootif, vlanid = mnet["iface"], mnet["vlanid"]
        bond_name, bond_slaves = mbond["name"], mbond["slaves"]
        layout = mlayout["layout"]

        nic = NIC(ifname)
        self.logger.debug("Building model for: %s" % nic)

        if ifname == bond_name:
            self.logger.debug(" Is bond master")
            nic = BondedNIC(nic, bond_slaves)

        if ifname == bootif:
            self.logger.debug(" Is bootif")
            if vlanid:
                self.logger.debug(" Has tag")
                nic = TaggedNIC(nic, vlanid)

            if layout == "bridged":
                self.logger.debug(" Is bridged")
                nic = BridgedNIC(nic)

        if ifname in bond_slaves:
            nic = None

        self.logger.debug("Concluded Model: %s" % nic)

        return nic

    def nics(self):
        """
        >>> model = NodeNetwork()
        """
        nics = [NIC(ifname) for ifname
                in self.relevant_ifnames(filter_vlans=True,
                                         filter_bonds=False,
                                         filter_bridges=True)]

        bridges = [nic for nic in nics if nic.typ == "bridge"]
        vlans = [nic for nic in nics if nic.typ == "vlan"]
        nics = [nic for nic in nics if nic not in bridges + vlans]

        self.logger.debug("Bridges: %s" % bridges)
        self.logger.debug("VLANs: %s" % vlans)
        self.logger.debug("NICs: %s" % nics)

        candidates = {}

        for nic in nics + vlans:
            candidate = self.build_nic_model(nic.ifname)
            if candidate:
                candidates[candidate.ifname] = candidate

        self.logger.debug("Candidates: %s" % candidates)

        return candidates

    def configured_nic(self):
        """Return the (probably) primary NIC of this system
        We identify it by looking if a config exists
        """
        candidate = None
        candidates = NodeNetwork().nics()
        for nic in candidates.values():
            if nic.is_configured():
                candidate = nic
                break
        return candidate

    def is_configured(self):
        """The NodeNetwork is either configered when we or a mgmt instance
        configured it
        """
        mgmtInterface = config.defaults.Management().retrieve()[
            "managed_ifnames"]
        return any([self.configured_nic(), mgmtInterface])


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
        cmd = ["ip", "route", "list"]
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


def networking_status(ifname=None):
    status = "Unknown"
    addresses = {}

    try:
        nn = NodeNetwork()
        nic = nn.build_nic_model(ifname) if ifname else nn.configured_nic()

        if nic and nic.exists():
            status = "Not connected"

            if nic:
                ifname = nic.ifname
                addresses = nic.ip_addresses()
                has_address = any(a is not None for a in addresses.values())

                if nic.has_link():
                    status = "Connected (Link only, no IP)"
                if has_address:
                    status = "Connected"
    except UnknownNicError:
        LOGGER.exception("Assume broken nic configuration")

    summary = (status, ifname, addresses)
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
    def __init__(self, address, netmask=None, scope=None):
        self.address = address
        self.netmask = netmask
        self.scope = scope

    def __str__(self):
        txt = str(self.address)
        if valid.IPv6Address().validate(txt):
            txt = "[%s]" % txt
        return txt

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
        utils.process.call(["hostname", new_hostname])
    return utils.process.pipe(["hostname"]).strip()


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


class Vlans(base.Base):
    """A class to offer a convenience api to the vconfig file
    """
    cfgfilename = "/proc/net/vlan/config"

    def parse_cfg(self):
        if not os.path.exists(self.cfgfilename):
            raise RuntimeError("vlans ain't enabled.")

        vlans = {}
        try:
            data = File(self.cfgfilename)
            data_block = False
            for line in data:
                if line.startswith("Name-Type"):
                    data_block = True
                    continue
                if not data_block:
                    continue
                vdev, vid, hdev = [field.strip()
                                   for field in line.split("|")]
                if not hdev in vlans:
                    vlans[hdev] = []
                vlans[hdev].append((vdev, vid))
        except IOError as e:
            self.logger.warning("Could not read vlan config: %s" %
                                e.message)

        return vlans

    def vlans_for_nic(self, ifname):
        """return the vlans of the nic ifname
        """
        return [vid
                for _, vid in self.parse_cfg().get(ifname, [])]

    def nic_for_vlan_device(self, vifname):
        nic = None
        for hdev, vdevid in self.parse_cfg().items():
            if vifname in (vdev for vdev, _ in vdevid):
                nic = hdev
                break
        return nic

    def is_vlan_device(self, vifname):
        """Check if ifname is a vlan device
        The vlan device is actually the virtual nic, not the master
        """
        return self.nic_for_vlan_device(vifname) is not None

    def all_vlan_devices(self):
        """Return all vlan devices
        """
        all_devices = []
        for vdevid in self.parse_cfg().values():
            all_devices += [vdev for vdev, _ in vdevid]
        return all_devices

    def delete(self, ifname):
        if not self.is_vlan_device(ifname):
            raise RuntimeError("Can no delete '%s', is no vlan device" %
                               ifname)
        process.call(["vconfig", "rem", ifname])


class Bridges(base.Base):
    def ifnames(self):
        return [os.path.basename(os.path.dirname(g)) for g
                in glob.glob("/sys/class/net/*/bridge")]

    def is_bridge(self, ifname):
        return SysfsNICInfo(ifname).is_bridge()

    def delete(self, ifname):
        if not self.is_bridge(ifname):
            raise RuntimeError("Can no delete '%s', is no bridge" % ifname)
        process.call(["ip", "link", "set", "dev", ifname, "down"])
        process.call(["brctl", "delbr", ifname])


class Bonds(base.Base):
    """Convenience API to access some bonding related stuff
    """
    bonding_masters_filename = "/sys/class/net/bonding_masters"

    def is_enabled(self):
        """If bonding is enabled
        """
        return fs.File(self.bonding_masters_filename).exists()

    def ifnames(self):
        """Return the ifnames of all bond devices
        """
        ifnames = []
        if self.is_enabled():
            ifnames = fs.File(self.bonding_masters_filename).read().split()
        return ifnames

    def is_bond(self, ifname):
        """Determins if ifname is a bond device
        """
        return ifname in self.ifnames()

    def delete_all(self):
        """Deletes all bond devices
        """
        for master in self.ifnames():
            self.delete(master)

    def delete(self, mifname):
        """Delete one bond master
        """
        if not self.is_bond(mifname):
            raise RuntimeError("Can no delete '%s', it is no bond master" %
                               mifname)
        #process.call(["ip", "link", "set", "dev", mifname, "down"])
        #process.call(["ip", "link", "delete", mifname, "type", "bond"])
        fs.File(self.bonding_masters_filename).write("-%s" % mifname)
