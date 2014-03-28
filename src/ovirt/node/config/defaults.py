#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# defaults.py - Copyright (C) 2012 Red Hat, Inc.
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
from ovirt.node import base, exceptions, valid, utils, config, log
from ovirt.node.config.network import NicConfig
from ovirt.node.exceptions import InvalidData
from ovirt.node.utils import storage, process, fs, AugeasWrapper, console, \
    system
from ovirt.node.utils.fs import ShellVarFile, File
from ovirt.node.utils.network import NIC, Bridges, Bonds
import glob
import os

"""
Classes and functions related to model of the configuration of oVirt Node.

Node is writing it's configuration into one central configuration file
(OVIRT_NODE_DEFAULTS_FILENAME) afterwards all actual configurations files are
created based on this file. This module provides an high level to this model.

There are classes for all components which can be configured through that
central configuration file.
Each class (for a component) can have a configure and apply_config method. Look
at the NodeConfigFileSection for more informations.

Each class should implement a configure method, mainly to define all the
required arguments (or keys).
"""

LOGGER = log.getLogger(__name__)

OVIRT_NODE_DEFAULTS_FILENAME = "/etc/default/ovirt"


def exists():
    """Determin if the defaults file exists
    """
    return os.path.exists(OVIRT_NODE_DEFAULTS_FILENAME)


class NodeConfigFile(ShellVarFile):
    """NodeConfigFile is a specififc interface to some configuration file
    with a specififc syntax
    """
    def __init__(self, filename=None):
        filename = filename or OVIRT_NODE_DEFAULTS_FILENAME
        if filename == OVIRT_NODE_DEFAULTS_FILENAME \
           and not fs.File(filename).exists():
            raise RuntimeError("Node config file does not exist: %s" %
                               filename)
        super(NodeConfigFile, self).__init__(filename, create=True)


class NodeConfigFileSection(base.Base):
    none_value = None
    keys = []
    raw_file = None

    def __init__(self, filename=None):
        super(NodeConfigFileSection, self).__init__()
        self.raw_file = NodeConfigFile(filename)

    def update(self, *args, **kwargs):
        """This function set's the correct entries in the defaults file for
        that specififc subclass.
        Is expected to call _map_config_and_update_defaults()
        """
        raise NotImplementedError

    def transaction(self):
        """This method returns a transaction which needs to be performed
        to activate the defaults config (so e.g. update cfg files and restart
        services).

        This can be used to update the UI when the transaction has many steps
        """
        raise NotImplementedError

    def commit(self, *args, **kwargs):
        """This method updates the to this subclass specific configuration
        files according to the config keys set with configure.

        A shortcut for:
        tx = obj.ransaction()
        tx()
        """
        tx = self.transaction()
        return tx()

    def _args_to_keys_mapping(self, keys_to_args=False):
        """Map the named arguments of th eupdate() method to the CFG keys

        Returns:
            A dict mapping an argname to it's cfg key (or vice versa)
        """
        func = self.update.wrapped_func
        # co_varnames contains all args within the func, the args are kept
        # at the beginning of the list, that's why we slice the varnames list
        # (start after self until the number of args)
        argnames = func.func_code.co_varnames[1:func.func_code.co_argcount]
        assert len(argnames) == len(self.keys), "argnames (%s) != keys (%s)" %\
            (argnames, self.keys)
        mapping = zip(self.keys, argnames) if keys_to_args else zip(argnames,
                                                                    self.keys)
        return dict(mapping)

    def retrieve(self):
        """Returns the config keys of the current component

        Returns:
            A dict with a mapping (arg, value).
            arg corresponds to the named arguments of the subclass's
            configure() method.
        """
        keys_to_args = self._args_to_keys_mapping(keys_to_args=True)
        cfg = self.raw_file.get_dict()
        model = {}
        for key in self.keys:
            value = cfg[key] if key in cfg else self.none_value
            model[keys_to_args[key]] = value
        assert len(keys_to_args) == len(model)
        return model

    def clear(self, keys=None):
        """Remove the configuration for this item
        """
        keys = keys or self.keys
        cfg = self.raw_file.get_dict()
        to_be_deleted = dict((k, None) for k in keys)
        cfg.update(to_be_deleted)
        self.raw_file.update(cfg, remove_empty=True)

    def _map_config_and_update_defaults(self, *args, **kwargs):
        assert len(args) == 0
        assert (set(self.keys) ^ set(kwargs.keys())) == set(), \
            "Keys: %s, Args: %s" % (self.keys, kwargs)
        new_dict = dict((k.upper(), v) for k, v in kwargs.items())
        self.raw_file.update(new_dict, remove_empty=True)

    @staticmethod
    def map_and_update_defaults_decorator(func):
        """
        FIXME Use some kind of map to map between args and env_Vars
              this would alsoallow kwargs

        >>> class Foo(object):
        ...     keys = None
        ...     def _map_config_and_update_defaults(self, *args, **kwargs):
        ...         return kwargs
        ...     @NodeConfigFileSection.map_and_update_defaults_decorator
        ...     def meth(self, a, b, c):
        ...         assert type(a) is int
        ...         assert type(b) is int
        ...         return {"OVIRT_C": "c%s" % c}
        >>> foo = Foo()
        >>> foo.keys = ("OVIRT_A", "OVIRT_B", "OVIRT_C")
        >>> foo.meth(1, 2, 3)
        {'OVIRT_A': 1, 'OVIRT_B': 2, 'OVIRT_C': 'c3'}
        """
        def wrapper(self, *args, **kwargs):
            if kwargs:
                # if kwargs are given it is interpreted as an update
                # so existing values which are not given in the kwargs are kept
                arg_to_key = self._args_to_keys_mapping()
                update_kwargs = self.retrieve()
                update_kwargs.update(dict((k, v) for k, v in kwargs.items()
                                          if k in update_kwargs.keys()))
                kwargs = update_kwargs
                new_cfg = dict((arg_to_key[k], v) for k, v
                               in update_kwargs.items())
            else:
                if len(self.keys) != len(args):
                    raise Exception("There are not enough arguments given " +
                                    "for %s of %s" % (func, self))
                new_cfg = dict(zip(self.keys, args))
            custom_cfg = func(self, *args, **kwargs) or {}
            assert type(custom_cfg) is dict, "%s must return a dict" % func
            new_cfg.update(custom_cfg)
            return self._map_config_and_update_defaults(**new_cfg)
        wrapper.wrapped_func = func
        return wrapper


class Network(NodeConfigFileSection):
    """Sets network stuff
    - OVIRT_BOOTIF
    - OVIRT_IP_ADDRESS, OVIRT_IP_NETMASK, OVIRT_IP_GATEWAY
    - OVIRT_VLAN

    >>> from ovirt.node.utils import fs
    >>> n = Network(fs.FakeFs.File("dst"))
    >>> _ = n.update("eth0", None, "10.0.0.1", "255.0.0.0", "10.0.0.255",
    ...          "20")
    >>> data = sorted(n.retrieve().items())
    >>> data[:3]
    [('bootproto', None), ('gateway', '10.0.0.255'), ('iface', 'eth0')]
    >>> data[3:]
    [('ipaddr', '10.0.0.1'), ('netmask', '255.0.0.0'), ('vlanid', '20')]

    >>> n.clear()
    >>> data = sorted(n.retrieve().items())
    >>> data[:3]
    [('bootproto', None), ('gateway', None), ('iface', None)]
    >>> data[3:]
    [('ipaddr', None), ('netmask', None), ('vlanid', None)]
    """
    keys = ("OVIRT_BOOTIF",
            "OVIRT_BOOTPROTO",
            "OVIRT_IP_ADDRESS",
            "OVIRT_IP_NETMASK",
            "OVIRT_IP_GATEWAY",
            "OVIRT_VLAN")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, iface, bootproto, ipaddr=None, netmask=None, gateway=None,
               vlanid=None):
        if bootproto not in ["dhcp", None]:
            raise exceptions.InvalidData("Unknown bootprotocol: %s" %
                                         bootproto)
        (valid.IPv4Address() | valid.Empty(or_none=True))(ipaddr)
        (valid.IPv4Address() | valid.Empty(or_none=True))(netmask)
        (valid.IPv4Address() | valid.Empty(or_none=True))(gateway)

    def configure_no_networking(self, iface=None):
        """Can be used to disable all networking
        """
        #iface = iface or self.retrieve()["iface"]
        #name = iface + "-DISABLED"
        # FIXME why should we use ifname-DISABLED here?
        self.update(None, None, None, None, None, None)

    def configure_dhcp(self, iface, vlanid=None):
        """Can be used to configure NIC iface on the vlan vlanid with DHCP
        """
        self.update(iface, "dhcp", None, None, None, vlanid)

    def configure_static(self, iface, ipaddr, netmask, gateway, vlanid):
        """Can be used to configure a static IP on a NIC
        """
        self.update(iface, None, ipaddr, netmask, gateway, vlanid)

    def transaction(self):
        """Return all transactions to re-configure networking
        """
        services = ["network", "ntpd", "ntpdate", "rpcbind", "nfslock",
                    "rpcidmapd", "rpcgssd"]

        def do_services(cmd, services):
            with console.CaptureOutput():
                for name in services:
                    system.service(name, cmd, False)

        class StopNetworkServices(utils.Transaction.Element):
            title = "Stop network services"

            def commit(self):
                do_services("stop", services)

        class RemoveConfiguration(utils.Transaction.Element):
            title = "Remove existing configuration"

            def commit(self):
                self._remove_devices()
                self._remove_ifcfg_configs()

            def _remove_devices(self):
                process.call(["killall", "dhclient"])

                vlans = utils.network.Vlans()
                vifs = vlans.all_vlan_devices()
                self.logger.debug("Attempting to delete all vlans: %s" % vifs)
                for vifname in vifs:
                    vlans.delete(vifname)
                    if NicConfig(vifname).exists():
                        NicConfig(vifname).delete()

                # FIXME we are removing ALL bridges
                bridges = Bridges()
                for bifname in bridges.ifnames():
                    bridges.delete(bifname)
                    if NicConfig(bifname).exists():
                        NicConfig(bifname).delete()

                bonds = Bonds()
                if bonds.is_enabled():
                    bonds.delete_all()

            def _remove_ifcfg_configs(self):
                pat = NicConfig.IfcfgBackend.filename_tpl % "*"
                remaining_ifcfgs = glob.glob(pat)
                self.logger.debug("Attemtping to remove remaining ifcfgs: %s" %
                                  remaining_ifcfgs)
                pcfg = fs.Config()
                for fn in remaining_ifcfgs:
                    pcfg.delete(fn)

        class WriteConfiguration(utils.Transaction.Element):
            title = "Write new configuration"

            def commit(self):
                m = Network().retrieve()
                aug = AugeasWrapper()

                needs_networking = False

                bond = NicBonding().retrieve()
                if bond["slaves"]:
                    NicBonding().transaction().commit()
                    needs_networking = True

                if m["iface"]:
                    self.__write_config()
                    needs_networking = True

                self.__write_lo()

                aug.set("/files/etc/sysconfig/network/NETWORKING",
                        "yes" if needs_networking else "no")

                fs.Config().persist("/etc/sysconfig/network")
                fs.Config().persist("/etc/hosts")

            def __write_config(self):
                m = Network().retrieve()

                topology = NetworkLayout().retrieve()["layout"]
                with_bridge = (topology == "bridged")

                mbond = NicBonding().retrieve()

                bridge_ifname = "br%s" % m["iface"]
                vlan_ifname = "%s.%s" % (m["iface"], m["vlanid"])

                nic_cfg = NicConfig(m["iface"])
                nic_cfg.device = m["iface"]
                nic_cfg.onboot = "yes"

                # Only assign a hwaddr if it's not a bond
                if mbond["name"] != m["iface"]:
                    nic_cfg.hwaddr = NIC(m["iface"]).hwaddr

                if m["vlanid"]:
                    # Add a tagged interface
                    vlan_cfg = NicConfig(vlan_ifname)
                    vlan_cfg.device = vlan_ifname
                    vlan_cfg.vlan = "yes"
                    vlan_cfg.onboot = "yes"
                    if with_bridge:
                        vlan_cfg.bridge = bridge_ifname
                    else:
                        self.__assign_ip_config(vlan_cfg)
                    vlan_cfg.save()
                else:
                    if with_bridge:
                        nic_cfg.bridge = bridge_ifname
                    else:
                        # No vlan and no bridge: So assign IP to NIC
                        self.__assign_ip_config(nic_cfg)

                if with_bridge:
                    # Add a bridge
                    bridge_cfg = NicConfig(bridge_ifname)
                    self.__assign_ip_config(bridge_cfg)
                    bridge_cfg.device = bridge_ifname
                    bridge_cfg.delay = "0"
                    bridge_cfg.type = "Bridge"
                    bridge_cfg.save()

                nic_cfg.save()

            def __write_lo(self):
                cfg = NicConfig("lo")
                cfg.device = "lo"
                cfg.ipaddr = "127.0.0.1"
                cfg.netmask = "255.0.0.0"
                cfg.onboot = "yes"
                cfg.save()

            def __assign_ip_config(self, cfg):
                m = Network().retrieve()
                m_dns = Nameservers().retrieve()
                m_ipv6 = IPv6().retrieve()

                cfg.bootproto = m["bootproto"]
                cfg.ipaddr = m["ipaddr"] or None
                cfg.gateway = m["gateway"] or None
                cfg.netmask = m["netmask"] or None
                cfg.onboot = "yes"
                cfg.peerntp = "yes"

                if m_dns["servers"]:
                    cfg.peerdns = "no"

                if m_ipv6["bootproto"]:
                    cfg.ipv6init = "yes"
                    cfg.ipv6forwarding = "no"
                    cfg.ipv6_autoconf = "no"

                if m_ipv6["bootproto"] == "auto":
                    cfg.ipv6_autoconf = "yes"
                elif m_ipv6["bootproto"] == "dhcp":
                    cfg.dhcpv6c = "yes"
                elif m_ipv6["bootproto"] == "static":
                    cfg.ipv6addr = "%s/%s" % (m_ipv6["ipaddr"],
                                              m_ipv6["netmask"])
                    cfg.ipv6_defaultgw = m_ipv6["gateway"]

        class PersistMacNicMapping(utils.Transaction.Element):
            title = "Persist MAC-NIC Mappings"

            def commit(self):
                # Copy the initial net rules to a file that get's not
                # overwritten at each boot, rhbz#773495
                rulesfile = "/etc/udev/rules.d/70-persistent-net.rules"
                newrulesfile = "/etc/udev/rules.d/71-persistent-node-net.rules"
                if File(rulesfile).exists():
                    process.check_call(["cp", rulesfile, newrulesfile])
                    fs.Config().persist(newrulesfile)

        class StartNetworkServices(utils.Transaction.Element):
            title = "Start network services"

            def commit(self):
                do_services("start", services)
                utils.AugeasWrapper.force_reload()
                utils.network.reset_resolver()

        tx = utils.Transaction("Applying new network configuration")
        tx.append(StopNetworkServices())
        tx.append(RemoveConfiguration())
        tx.append(WriteConfiguration())
        tx.append(PersistMacNicMapping())
        tx.append(StartNetworkServices())
        return tx


class NicBonding(NodeConfigFileSection):
    """Create a bonding device
    - OVIRT_BOND

    >>> from ovirt.node.utils import fs
    >>> n = NicBonding(fs.FakeFs.File("dst"))
    >>> _ = n.update("bond0", ["ens1", "ens2", "ens3"], "mode=4")
    >>> data = sorted(n.retrieve().items())
    >>> data[:2]
    [('name', 'bond0'), ('options', 'mode=4')]
    >>> data [2:]
    [('slaves', ['ens1', 'ens2', 'ens3'])]
    """
    keys = ("OVIRT_BOND_NAME",
            "OVIRT_BOND_SLAVES",
            "OVIRT_BOND_OPTIONS")

    # Set some sane defaults if not options are diven
    # https://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/
    # tree/Documentation/networking/bonding.txt#n153
    default_options = "mode=balance-rr miimon=100"

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, name, slaves, options):
        if name is not None and not name.startswith("bond"):
            raise InvalidData("Bond ifname must start with 'bond'")
        if slaves is not None and type(slaves) is not list:
            raise InvalidData("Slaves must be a list")

        options = options or self.default_options
        return {"OVIRT_BOND_SLAVES": ",".join(slaves) if slaves else None,
                "OVIRT_BOND_OPTIONS": options if name else None}

    def retrieve(self):
        cfg = super(NicBonding, self).retrieve()
        cfg.update({"slaves": (cfg["slaves"].split(",") if cfg["slaves"]
                               else [])})
        return cfg

    def configure_no_bond(self):
        """Remove all bonding
        """
        return self.update(None, None, None)

    def configure_8023ad(self, name, slaves):
        return self.update(name, slaves, "mode=4")

    def transaction(self):
        bond = NicBonding().retrieve()
        if not bond["options"]:
            bond["options"] = self.default_options

        class RemoveConfigs(utils.Transaction.Element):
            title = "Clean potential bond configurations"

            def commit(self):
                net = Network()
                mnet = net.retrieve()
                if mnet["iface"] and mnet["iface"].startswith("bond"):
                    net.configure_no_networking()

                for ifname in NicConfig.list():
                    cfg = NicConfig(ifname)
                    if cfg.master:
                        self.logger.debug("Removing master from %s" % ifname)
                        cfg.master = None
                        cfg.slave = None
                        cfg.save()
                    elif ifname.startswith("bond"):
                        self.logger.debug("Removing master %s" % ifname)
                        cfg.delete()

                Bonds().delete_all()

        class WriteSlaveConfigs(utils.Transaction.Element):
            title = "Writing bond slaves configuration"

            def commit(self):
                m = Network().retrieve()
                if m["iface"] in bond["slaves"]:
                    raise RuntimeError("Bond slave can not be used as " +
                                       "primary device")

                for slave in bond["slaves"]:
                    slave_cfg = NicConfig(slave)
                    slave_cfg.hwaddr = NIC(slave).hwaddr
                    slave_cfg.device = slave
                    slave_cfg.slave = "yes"
                    slave_cfg.master = bond["name"]
                    slave_cfg.onboot = "yes"
                    slave_cfg.save()

        class WriteMasterConfig(utils.Transaction.Element):
            title = "Writing bond master configuration"

            def commit(self):
                if bond["options"]:
                    cfg = NicConfig(bond["name"])
                    cfg.device = bond["name"]
                    cfg.onboot = "yes"
                    cfg.type = "Bond"
                    cfg.bonding_opts = bond["options"]

                    cfg.save()

        tx = utils.Transaction("Writing bond configuration")
        if bond["slaves"]:
            tx.append(WriteMasterConfig())
            tx.append(WriteSlaveConfigs())
        else:
            tx.append(RemoveConfigs())
        return tx


class NetworkLayout(NodeConfigFileSection):
    """Sets the network topology
    - OVIRT_NETWORK_TOPOLOGY

    >>> from ovirt.node.utils import fs
    >>> n = NetworkLayout(fs.FakeFs.File("dst"))
    >>> _ = n.update("bridged")
    >>> sorted(n.retrieve().items())
    [('layout', 'bridged')]
    """
    keys = ("OVIRT_NETWORK_LAYOUT",)

    # The BOOTIF NIC is configured directly
    LAYOUT_DIRECT = "direct"

    # bridged way, a bridge is created for BOOTIF
    LAYOUT_BRIDGED = "bridged"

    known_layouts = [LAYOUT_DIRECT,
                     LAYOUT_BRIDGED]

    default_layout = LAYOUT_DIRECT

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, layout=None):
        assert layout in self.known_layouts + [None]

    def configure_bridged(self):
        return self.update("bridged")

    def configure_direct(self):
        return self.update("direct")

    def configure_default(self):
        return self.update(None)


class IPv6(NodeConfigFileSection):
    """Sets IPv6 network stuff
    - OVIRT_IPV6 (static, auto, dhcp)
    - OVIRT_IPV6_ADDRESS
    - OVIRT_IPV6_NETMASK
    - OVIRT_IPV6_GATEWAY

    >>> from ovirt.node.utils import fs
    >>> n = IPv6(fs.FakeFs.File("dst"))
    >>> _ = n.update("auto", "11::22", "42", "11::44")
    >>> data = sorted(n.retrieve().items())
    >>> data[0:3]
    [('bootproto', 'auto'), ('gateway', '11::44'), ('ipaddr', '11::22')]
    >>> data[3:]
    [('netmask', '42')]
    """
    keys = ("OVIRT_IPV6",
            "OVIRT_IPV6_ADDRESS",
            "OVIRT_IPV6_NETMASK",
            "OVIRT_IPV6_GATEWAY")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, bootproto, ipaddr, netmask, gateway):
        if bootproto not in ["auto", "static", "none", "dhcp", None]:
            raise exceptions.InvalidData("Unknown bootprotocol: %s" %
                                         bootproto)
        (valid.IPv6Address() | valid.Empty(or_none=True))(ipaddr)
        (valid.Number(bounds=[0, 128]) | valid.Empty(or_none=True))(netmask)
        (valid.IPv6Address() | valid.Empty(or_none=True))(gateway)

    def transaction(self):
        return self.__legacy_transaction()

    def __legacy_transaction(self):
        """The transaction is the same as in the Network class - using the
        legacy stuff.
        This should be rewritten to allow a more fine grained progress
        monitoring.
        """
        tx = Network().transaction()
        return tx

    def disable(self):
        """Can be used to disable IPv6
        """
        self.update(None, None, None, None)

    def configure_dhcp(self):
        """Can be used to configure NIC iface on the vlan vlanid with DHCP
        """
        self.update("dhcp", None, None, None)

    def configure_static(self, address, netmask, gateway):
        """Can be used to configure a static IPv6 IP on a NIC
        """
        self.update("static", address, netmask, gateway)

    def configure_auto(self):
        """Can be used to autoconfigure IPv6 on a NIC
        """
        self.update("auto", None, None, None)


class Hostname(NodeConfigFileSection):
    """Configure hostname


    >>> from ovirt.node.utils import fs
    >>> n = Hostname(fs.FakeFs.File("dst"))
    >>> hostname = "host.example.com"
    >>> _ = n.update(hostname)
    >>> n.retrieve()
    {'hostname': 'host.example.com'}
    """
    keys = ("OVIRT_HOSTNAME",)

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, hostname):
        (valid.Empty() | valid.FQDNOrIPAddress())(hostname)

    def transaction(self):
        cfg = self.retrieve()
        hostname = cfg["hostname"]

        class UpdateHostname(utils.Transaction.Element):
            title = "Setting hostname"

            def __init__(self, hostname):
                self.hostname = hostname

            def commit(self):
                aug = AugeasWrapper()

                localhost_entry = None
                for entry in aug.match("/files/etc/hosts/*"):
                    if aug.get(entry + "/ipaddr") == "127.0.0.1":
                        localhost_entry = entry
                        break

                if not localhost_entry:
                    raise RuntimeError("Couldn't find entry for localhost")

                # Remove all aliases
                for alias_entry in aug.match(localhost_entry + "/alias"):
                    aug.remove(alias_entry, False)

                # ... and create a new one
                aliases = ["localhost", "localhost.localdomain"]
                if self.hostname:
                    aliases.append(self.hostname)

                for _idx, alias in enumerate(aliases):
                    idx = _idx + 1
                    p = "%s/alias[%s]" % (localhost_entry, idx)
                    aug.set(p, alias, False)

                config.network.hostname(self.hostname)

                fs.Config().persist("/etc/hosts")
                fs.Config().persist("/etc/hostname")
                fs.Config().persist("/etc/sysconfig/network")

                utils.network.reset_resolver()

        tx = utils.Transaction("Configuring hostname")
        tx.append(UpdateHostname(hostname))
        return tx


class Nameservers(NodeConfigFileSection):
    """Configure nameservers

    >>> from ovirt.node.utils import fs
    >>> n = Nameservers(fs.FakeFs.File("dst"))
    >>> servers = ["10.0.0.2", "10.0.0.3"]
    >>> _ = n.update(servers)
    >>> data = n.retrieve()
    >>> all([servers[idx] == s for idx, s in enumerate(data["servers"])])
    True
    >>> _ = n.update([])
    >>> n.retrieve()
    {'servers': None}
    """
    keys = ("OVIRT_DNS",)

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, servers):
        assert type(servers) is list
        # Preparation
        servers = [i.strip() for i in servers]
        servers = [i for i in servers if i not in ["", None]]

        # Validation
        validator = lambda v: valid.FQDNOrIPAddress()
        map(validator, servers)

        # Mangling for the conf file format
        return {"OVIRT_DNS": ",".join(servers) or None
                }

    def retrieve(self):
        """We mangle the original vale a bit for py convenience
        """
        cfg = dict(NodeConfigFileSection.retrieve(self))
        cfg.update({"servers": cfg["servers"].split(",") if cfg["servers"]
                    else None
                    })
        return cfg

    def transaction(self):
        """Derives the nameserver config from OVIRT_DNS

        1. Parse nameservers from defaults
        2. Update resolv.conf
        3. Update ifcfg- (peerdns=no if manual resolv.conf)
        4. Persist resolv.conf

        Args:
            servers: List of servers (str)
        """
        aug = utils.AugeasWrapper()
        m = Nameservers().retrieve()

        tx = utils.Transaction("Configuring DNS")

        servers = []
        if m["servers"]:
            servers = m["servers"]
        else:
            self.logger.debug("No DNS server entry in default config")

        class UpdateResolvConf(utils.Transaction.Element):
            title = "Updating resolv.conf"

            def commit(self):
                # Write resolv.conf any way, sometimes without servers
                comment = ("Please make changes through the TUI " +
                           "or management server. " +
                           "Manual edits to this file will be " +
                           "lost on reboot")
                aug.set("/files/etc/resolv.conf/#comment[1]", comment)
                # Now set the nameservers
                config.network.nameservers(servers)
                utils.fs.Config().persist("/etc/resolv.conf")

                utils.network.reset_resolver()

        class UpdatePeerDNS(utils.Transaction.Element):
            title = "Update PEERDNS statement in ifcfg-* files"

            def commit(self):
                # Set or remove PEERDNS for all ifcfg-*
                for nic in glob.glob("/etc/sysconfig/network-scripts/ifcfg-*"):
                    if "ifcfg-lo" in nic:
                        continue
                    path = "/files%s/PEERDNS" % nic
                    if len(servers) > 0:
                        aug.set(path, "no")
                    else:
                        aug.remove(path)

        # FIXME what about restarting NICs to pickup peerdns?

        tx += [UpdateResolvConf(), UpdatePeerDNS()]

        return tx


class Timeservers(NodeConfigFileSection):
    """Configure timeservers

    >>> from ovirt.node.utils import fs
    >>> n = Timeservers(fs.FakeFs.File("dst"))
    >>> servers = ["10.0.0.4", "10.0.0.5", "0.example.com"]
    >>> _ = n.update(servers)
    >>> data = n.retrieve()
    >>> all([servers[idx] == s for idx, s in enumerate(data["servers"])])
    True
    >>> _ = n.update([])
    >>> n.retrieve()
    {'servers': None}
    """
    keys = ("OVIRT_NTP",)

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, servers):
        assert type(servers) is list
        # Preparation
        servers = [i.strip() for i in servers]
        servers = [i for i in servers if i not in ["", None]]

        # Validation
        validator = lambda v: valid.FQDNOrIPAddress()
        map(validator, servers)

        # Mangling to match the conf file
        return {"OVIRT_NTP": ",".join(servers) or None
                }

    def retrieve(self):
        cfg = dict(NodeConfigFileSection.retrieve(self))
        cfg.update({"servers": cfg["servers"].split(",") if cfg["servers"]
                    else None
                    })
        return cfg

    def transaction(self):
        m = Timeservers().retrieve()

        servers = m["servers"]

        class WriteConfiguration(utils.Transaction.Element):
            title = "Writing timeserver configuration"

            def commit(self):
                aug = AugeasWrapper()

                p = "/files/etc/ntp.conf"
                aug.remove(p, False)
                aug.set(p + "/driftfile", "/var/lib/ntp/drift", False)
                aug.set(p + "/includefile", "/etc/ntp/crypto/pw", False)
                aug.set(p + "/keys", "/etc/ntp/keys", False)
                aug.save()

                config.network.timeservers(servers)

                utils.fs.Config().persist("/etc/ntp.conf")

        class ApplyConfiguration(utils.Transaction.Element):
            title = "Restarting time services"

            def commit(self):
                system.service("ntpd", "stop", False)
                system.service("ntpdate", "start", False)
                system.service("ntpd", "start", False)

        tx = utils.Transaction("Configuring timeservers")
        tx.append(WriteConfiguration())
        tx.append(ApplyConfiguration())
        return tx


class Syslog(NodeConfigFileSection):
    """Configure rsyslog


    >>> from ovirt.node.utils import fs
    >>> n = Syslog(fs.FakeFs.File("dst"))
    >>> server = "10.0.0.6"
    >>> port = "514"
    >>> _ = n.update(server, port)
    >>> sorted(n.retrieve().items())
    [('port', '514'), ('server', '10.0.0.6')]
    """
    keys = ("OVIRT_SYSLOG_SERVER",
            "OVIRT_SYSLOG_PORT")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, server, port):
        (valid.Empty(or_none=True) | valid.FQDNOrIPAddress())(server)
        valid.Port()(port)

    def transaction(self):
        return self.__legacy_transaction()

    def __legacy_transaction(self):
        cfg = dict(self.retrieve())
        server, port = (cfg["server"], cfg["port"])

        class CreateRsyslogConfig(utils.Transaction.Element):
            title = "Setting syslog server and port"

            def commit(self):
                import ovirtnode.log as olog
                olog.ovirt_rsyslog(server, port, "udp")

        tx = utils.Transaction("Configuring syslog")
        tx.append(CreateRsyslogConfig())
        return tx


class Collectd(NodeConfigFileSection):
    """Configure collectd

    >>> from ovirt.node.utils import fs
    >>> n = Collectd(fs.FakeFs.File("dst"))
    >>> server = "10.0.0.7"
    >>> port = "42"
    >>> _ = n.update(server, port)
    >>> sorted(n.retrieve().items())
    [('port', '42'), ('server', '10.0.0.7')]
    """
    keys = ("OVIRT_COLLECTD_SERVER",
            "OVIRT_COLLECTD_PORT")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, server, port):
        valid.FQDNOrIPAddress()(server)
        valid.Port()(port)

    def transaction(self):
        return self.__legacy_transaction()

    def __legacy_transaction(self):
        cfg = dict(self.retrieve())
        server, port = (cfg["server"], cfg["port"])

        class ConfigureCollectd(utils.Transaction.Element):
            title = "Setting collect server and port"

            def commit(self):
                # pylint: disable-msg=E0611
                from ovirt_config_setup import collectd  # @UnresolvedImport
                # pylint: enable-msg=E0611
                if collectd.write_collectd_config(server, port):
                    self.logger.debug("Collectd was configured successfully")
                else:
                    raise exceptions.TransactionError("Failed to configure " +
                                                      "collectd")

        tx = utils.Transaction("Configuring collectd")
        tx.append(ConfigureCollectd())
        return tx


class KDump(NodeConfigFileSection):
    """Configure kdump

    >>> from ovirt.node.utils import fs
    >>> n = KDump(fs.FakeFs.File("dst"))
    >>> nfs_url = "host.example.com:/dst/path"
    >>> ssh_url = "root@host.example.com"
    >>> _ = n.update(nfs_url, ssh_url, True)
    >>> d = sorted(n.retrieve().items())
    >>> d[:2]
    [('local', True), ('nfs', 'host.example.com:/dst/path')]
    >>> d[2:]
    [('ssh', 'root@host.example.com')]
    """
    keys = ("OVIRT_KDUMP_NFS",
            "OVIRT_KDUMP_SSH",
            "OVIRT_KDUMP_LOCAL")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, nfs, ssh, local):
        (valid.Empty(or_none=True) | valid.NFSAddress())(nfs)
        (valid.Empty(or_none=True) | valid.SSHAddress())(ssh)
        (valid.Empty(or_none=True) | valid.Boolean())(local)
        return {"OVIRT_KDUMP_LOCAL": "true" if local else None
                }

    def configure_nfs(self, nfs_location):
        self.update(nfs_location, None, None)

    def configure_ssh(self, ssh_location):
        self.update(None, ssh_location, None)

    def configure_local(self):
        self.update(None, None, True)

    def disable_kdump(self):
        self.update(None, None, None)

    def retrieve(self):
        cfg = dict(NodeConfigFileSection.retrieve(self))
        cfg.update({"local": True if cfg["local"] == "true" else None
                    })
        return cfg

    def transaction(self):
        cfg = dict(self.retrieve())
        nfs, ssh, restore = (cfg["nfs"], cfg["ssh"], cfg["local"])

        class BackupKdumpConfig(utils.Transaction.Element):
            title = "Backing up config files"

            def __init__(self):
                self.backups = utils.fs.BackupedFiles(["/etc/kdump.conf"])
                super(BackupKdumpConfig, self).__init__()

            def commit(self):
                self.backups.create(ignore_existing=True)

        class RestoreKdumpConfig(utils.Transaction.Element):
            title = "Restoring default kdump config"

            def commit(self):
                import ovirtnode.kdump as okdump
                okdump.restore_kdump_config()

        class CreateNfsKdumpConfig(utils.Transaction.Element):
            title = "Creating kdump NFS config"

            def commit(self):
                import ovirtnode.kdump as okdump
                okdump.write_kdump_config(nfs)

        class CreateSshKdumpConfig(utils.Transaction.Element):
            title = "Creating kdump SSH config"

            def commit(self):
                import ovirtnode.kdump as okdump
                from ovirtnode.ovirtfunctions import ovirt_store_config

                okdump.write_kdump_config(ssh)

                kdumpctl_cmd = system.which("kdumpctl")
                if kdumpctl_cmd:
                    cmd = [kdumpctl_cmd, "propagate"]
                else:
                    cmd = ["service", "kdump", "propagate"]

                try:
                    utils.process.check_call(cmd)

                    ovirt_store_config(["/root/.ssh/kdump_id_rsa.pub",
                                        "/root/.ssh/kdump_id_rsa",
                                        "/root/.ssh/known_hosts",
                                        "/root/.ssh/config"])
                except utils.process.CalledProcessError as e:
                    self.logger.warning("Failed to activate KDump with " +
                                        "SSH: %s" % e)

        class RemoveKdumpConfig(utils.Transaction.Element):
            title = "Removing kdump backup"

            def __init__(self, backups):
                self.backups = backups
                super(RemoveKdumpConfig, self).__init__()

            def commit(self):
                from ovirtnode.ovirtfunctions import remove_config

                remove_config("/etc/kdump.conf")
                system.service("kdump", "stop")
                fs.File('/etc/kdump.conf').touch()

                self.backups.remove()

        class RestartKdumpService(utils.Transaction.Element):
            title = "Restarting kdump service"

            def __init__(self, backups):
                self.backups = backups
                super(RestartKdumpService, self).__init__()

            def commit(self):
                from ovirtnode.ovirtfunctions import unmount_config, \
                    ovirt_store_config

                try:
                    system.service("kdump", "restart")
                except utils.process.CalledProcessError as e:
                    self.logger.info("Failure while restarting kdump: %s" % e)
                    unmount_config("/etc/kdump.conf")
                    self.backups.restore("/etc/kdump.conf")
                    system.service("kdump", "restart", do_raise=False)

                    raise RuntimeError("KDump configuration failed, " +
                                       "location unreachable. Previous " +
                                       "configuration was restored.")

                ovirt_store_config("/etc/kdump.conf")
                self.backups.remove()

        tx = utils.Transaction("Configuring kdump")

        backup_txe = BackupKdumpConfig()
        tx.append(backup_txe)

        final_txe = RestartKdumpService(backup_txe.backups)
        if nfs:
            tx.append(CreateNfsKdumpConfig())
        elif ssh:
            tx.append(CreateSshKdumpConfig())
        elif restore in [True, False]:
            tx.append(RestoreKdumpConfig())
        else:
            final_txe = RemoveKdumpConfig(backup_txe.backups)

        tx.append(final_txe)

        return tx


class iSCSI(NodeConfigFileSection):
    """Configure iSCSI

    >>> from ovirt.node.utils import fs
    >>> n = iSCSI(fs.FakeFs.File("dst"))
    >>> _ = n.update("iqn.1992-01.com.example:node",
    ...          "iqn.1992-01.com.example:target", "10.0.0.8", "42")
    >>> data = sorted(n.retrieve().items())
    >>> data[:2]
    [('name', 'iqn.1992-01.com.example:node'), ('target_host', '10.0.0.8')]
    >>> data[2:]
    [('target_name', 'iqn.1992-01.com.example:target'), ('target_port', '42')]
    """
    keys = ("OVIRT_ISCSI_NODE_NAME",
            "OVIRT_ISCSI_TARGET_NAME",
            "OVIRT_ISCSI_TARGET_IP",
            "OVIRT_ISCSI_TARGET_PORT")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, name, target_name, target_host, target_port):
        # FIXME add more validation
        valid.IQN()(name)
        (valid.Empty(or_none=True) | valid.IQN())(target_name)
        (valid.Empty(or_none=True) | valid.FQDNOrIPAddress())(target_host)
        (valid.Empty(or_none=True) | valid.Port())(target_port)

    def transaction(self):
        cfg = dict(self.retrieve())
        initiator_name = cfg["name"]

        class ConfigureIscsiInitiator(utils.Transaction.Element):
            title = "Setting the iSCSI initiator name"

            def commit(self):
                iscsi = utils.storage.iSCSI()
                iscsi.initiator_name(initiator_name)

        tx = utils.Transaction("Configuring the iSCSI Initiator")
        tx.append(ConfigureIscsiInitiator())
        return tx


class Netconsole(NodeConfigFileSection):
    """Configure netconsole

    >>> from ovirt.node.utils import fs
    >>> n = Netconsole(fs.FakeFs.File("dst"))
    >>> server = "10.0.0.9"
    >>> port = "666"
    >>> _ = n.update(server, port)
    >>> sorted(n.retrieve().items())
    [('port', '666'), ('server', '10.0.0.9')]
    """
    keys = ("OVIRT_NETCONSOLE_SERVER",
            "OVIRT_NETCONSOLE_PORT")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, server, port):
        (valid.Empty(or_none=True) | valid.FQDNOrIPAddress())(server)
        valid.Port()(port)

    def transaction(self):
        cfg = dict(self.retrieve())
        server, port = (cfg["server"], cfg["port"])

        class CreateNetconsoleConfig(utils.Transaction.Element):
            title = "Setting netconsole server and port"

            def commit(self):
                import ovirtnode.log as olog
                olog.ovirt_netconsole(server, port)

        tx = utils.Transaction("Configuring netconsole")
        tx.append(CreateNetconsoleConfig())
        return tx


class Logrotate(NodeConfigFileSection):
    """Configure logrotate

    >>> from ovirt.node.utils import fs
    >>> n = Logrotate(fs.FakeFs.File("dst"))
    >>> max_size = "42"
    >>> _ = n.update(max_size)
    >>> n.retrieve().items()
    [('max_size', '42')]
    """
    # FIXME this key is new!
    keys = ("OVIRT_LOGROTATE_MAX_SIZE",)

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, max_size):
        valid.Number([0, None])(max_size)

    def transaction(self):
        cfg = dict(self.retrieve())
        max_size = cfg["max_size"]

        class CreateLogrotateConfig(utils.Transaction.Element):
            title = "Setting logrotate maximum logfile size"

            def commit(self):
                from ovirtnode.ovirtfunctions import ovirt_store_config
                aug = utils.AugeasWrapper()
                aug.set("/files/etc/logrotate.d/ovirt-node/rule/size",
                        max_size)
                ovirt_store_config("/etc/logrotate.d/ovirt-node")

        tx = utils.Transaction("Configuring logrotate")
        tx.append(CreateLogrotateConfig())
        return tx


class Keyboard(NodeConfigFileSection):
    """Configure keyboard

    >>> from ovirt.node.utils import fs
    >>> n = Keyboard(fs.FakeFs.File("dst"))
    >>> layout = "de_DE.UTF-8"
    >>> _ = n.update(layout)
    >>> n.retrieve()
    {'layout': 'de_DE.UTF-8'}
    """
    # FIXME this key is new!
    keys = ("OVIRT_KEYBOARD_LAYOUT",)

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, layout):
        # FIXME Some validation that layout is in the list of available layouts
        pass

    def transaction(self):
        cfg = dict(self.retrieve())
        layout = cfg["layout"]

        class CreateKeyboardConfig(utils.Transaction.Element):
            title = "Setting keyboard layout"

            def commit(self):
                from ovirtnode.ovirtfunctions import ovirt_store_config
                kbd = utils.system.Keyboard()
                kbd.set_layout(layout)
                ovirt_store_config("/etc/vconsole.conf")
                ovirt_store_config("/etc/sysconfig/keyboard")

        tx = utils.Transaction("Configuring keyboard layout")
        tx.append(CreateKeyboardConfig())
        return tx


class NFSv4(NodeConfigFileSection):
    """Configure NFSv4

    >>> from ovirt.node.utils import fs
    >>> n = NFSv4(fs.FakeFs.File("dst"))
    >>> domain = "foo.example"
    >>> _ = n.update(domain)
    >>> n.retrieve().items()
    [('domain', 'foo.example')]
    """
    # FIXME this key is new!
    keys = ("OVIRT_NFSV4_DOMAIN",)

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, domain):
        (valid.Empty() | valid.FQDN())(domain)
        return {"OVIRT_NFSV4_DOMAIN": domain or None
                }

    def transaction(self):
        cfg = dict(self.retrieve())
        domain = cfg["domain"]

        class ConfigureNfsv4(utils.Transaction.Element):
            title = "Setting NFSv4 domain"

            def commit(self):
                nfsv4 = storage.NFSv4()

                # Need to pass "" to disable Domain line
                nfsv4.domain(domain or "")

                fs.Config().persist(nfsv4.configfilename)
                system.service("rpcidmapd", "restart")
                process.call(["nfsidmap", "-c"])

        tx = utils.Transaction("Configuring NFSv4")
        tx.append(ConfigureNfsv4())
        return tx


class SSH(NodeConfigFileSection):
    """Configure SSH

    >>> from ovirt.node.utils import fs
    >>> n = SSH(fs.FakeFs.File("dst"))
    >>> pwauth = True
    >>> num_bytes = "24"
    >>> disable_aesni = True
    >>> _ = n.update(pwauth, num_bytes, disable_aesni)
    >>> sorted(n.retrieve().items())
    [('disable_aesni', True), ('num_bytes', '24'), ('pwauth', True)]
    """
    keys = ("OVIRT_SSH_PWAUTH",
            "OVIRT_USE_STRONG_RNG",
            "OVIRT_DISABLE_AES_NI")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, pwauth, num_bytes, disable_aesni):
        valid.Boolean()(pwauth)
        (valid.Number() | valid.Empty(or_none=True))(num_bytes)
        (valid.Boolean() | valid.Empty(or_none=True))(disable_aesni)
        return {"OVIRT_SSH_PWAUTH": "yes" if pwauth else None,
                "OVIRT_DISABLE_AES_NI": "true" if disable_aesni else None
                }

    def retrieve(self):
        cfg = dict(NodeConfigFileSection.retrieve(self))
        cfg.update({"pwauth": True if cfg["pwauth"] == "yes" else False,
                    "disable_aesni": True if cfg["disable_aesni"] == "true"
                    else False
                    })
        return cfg

    def transaction(self):
        cfg = dict(self.retrieve())
        pwauth, num_bytes, disable_aesni = (cfg["pwauth"], cfg["num_bytes"],
                                            cfg["disable_aesni"])

        ssh = utils.security.Ssh()

        class ConfigurePasswordAuthentication(utils.Transaction.Element):
            title = "Configuring SSH password authentication"

            def commit(self):
                ssh.password_authentication(pwauth)

        class ConfigureStrongRNG(utils.Transaction.Element):
            title = "Configuring SSH strong RNG"

            def commit(self):
                ssh.strong_rng(num_bytes)

        class ConfigureAESNI(utils.Transaction.Element):
            title = "Configuring SSH AES NI"

            def commit(self):
                ssh.disable_aesni(disable_aesni)

        tx = utils.Transaction("Configuring SSH")
        tx.append(ConfigurePasswordAuthentication())
        tx.append(ConfigureStrongRNG())
        tx.append(ConfigureAESNI())
        return tx


class Installation(NodeConfigFileSection):
    """Configure storage
    This is a class to handle the storage parameters used at installation time

    >>> from ovirt.node.utils import fs
    >>> n = Installation(fs.FakeFs.File("dst"))
    >>> kwargs = {"init": ["/dev/sda"], "root_install": "1"}
    >>> _ = n.update(**kwargs)
    >>> data = n.retrieve().items()
    """
    keys = ("OVIRT_INIT",
            "OVIRT_OVERCOMMIT",
            "OVIRT_VOL_ROOT_SIZE",
            "OVIRT_VOL_EFI_SIZE",
            "OVIRT_VOL_SWAP_SIZE",
            "OVIRT_VOL_LOGGING_SIZE",
            "OVIRT_VOL_CONFIG_SIZE",
            "OVIRT_VOL_DATA_SIZE",
            "OVIRT_INSTALL",
            "OVIRT_UPGRADE",
            "OVIRT_INSTALL_ROOT",
            "OVIRT_ROOT_INSTALL",
            "OVIRT_ISCSI_INSTALL"
            )

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, init, overcommit, root_size, efi_size,
               swap_size, logging_size, config_size, data_size, install,
               upgrade, install_root, root_install, iscsi_install):
        # FIXME no checking!
        return {"OVIRT_INIT": ",".join(init),
                "OVIRT_INSTALL_ROOT": "y" if install_root else None,
                "OVIRT_ROOT_INSTALL": "y" if root_install else None,
                "OVIRT_INSTALL": "1" if install else None,
                "OVIRT_UPGRADE": "1" if upgrade else None,
                "OVIRT_ISCSI_INSTALL": "1" if iscsi_install else None}

    def retrieve(self):
        cfg = dict(NodeConfigFileSection.retrieve(self))
        cfg.update({"init": cfg["init"].split(",") if cfg["init"] else [],
                    "install_root": cfg["install_root"] == "y",
                    "root_install": cfg["root_install"] == "y",
                    "install": cfg["install"] == "1",
                    "iscsi_install": cfg["iscsi_install"] == "1",
                    "upgrade": cfg["upgrade"] == "1"})
        return cfg

    def transaction(self):
        return None

    def install_on(self, init, root_size, efi_size, swap_size, logging_size,
                   config_size, data_size):
        """Convenience function which can be used to set the parameters which
        are going to be picked up by the installer backend to install Node on
        the given storage with the given othere params
        """
        self.update(install=True,
                    install_root=True,
                    root_install=True,
                    init=init,
                    root_size=root_size,
                    efi_size=efi_size,
                    swap_size=swap_size,
                    logging_size=logging_size,
                    config_size=config_size,
                    data_size=data_size)

    def upgrade(self):
        """Convenience function setting the params to upgrade
        """
        self.update(upgrade=True,
                    install=None)


class Management(NodeConfigFileSection):
    """Exchange informations with management part

    Plugins can use this class as follows:

    from ovirt.node.config.defaults import Management
    mgmt.update("oVirt Engine at <url>",
                ["ovirtmgmt"],
                [])


    Keys
    ----
    MANAGED_BY=<descriptive-text>
        This key is used to (a) signal the Node is being managed and
        (b) signaling who is managing this node.
        The value can be a descriptive text inclduning e.g. an URL to point
        to the management instance.

    MANAGED_IFNAMES=<ifname>[,<ifname>,...]
        This key is used to specify a number (comma separated list) if
        ifnames which are managed and for which the TUI shall display some
        information (IP, ...).
        This can also be used by the TUI to decide to not offer NIC
        configuration to the user.
        This is needed to tell the TUI the _important_ NICs on this host.
        E.g. it's probably worth to provide the ifname of the management
        interface here, e.g ovirtmgmt.

    MANAGED_LOCKED_PAGES=<pagename>[,<pagename>,...]
        (Future) A list of pages which shall be locked e.g. because the
        management instance is configuring the aspect (e.g. networking or
        logging).
    """
    keys = ("MANAGED_BY",
            "MANAGED_IFNAMES",
            "MANAGED_LOCKED_PAGES"
            )

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, managed_by, managed_ifnames, managed_locked_pages):
        assert type(managed_ifnames) is list
        return {"MANAGED_IFNAMES": (",".join(managed_ifnames)
                                    if managed_ifnames else None)}

    def retrieve(self):
        cfg = dict(NodeConfigFileSection.retrieve(self))
        cfg["managed_ifnames"] = (cfg["managed_ifnames"].split(",")
                                  if cfg["managed_ifnames"] else None)
        return cfg

    def transaction(self):
        return None

    def is_managed(self):
        return True if self.retrieve()["managed_by"] else False

    def has_managed_ifnames(self):
        return True if self.retrieve()["managed_ifnames"] else False
