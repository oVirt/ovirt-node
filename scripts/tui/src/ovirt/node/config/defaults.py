#!/usr/bin/python
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

"""
Classes and functions related to model of the configuration of oVirt Node.

Node is writing it's configuration into one central configuration file
(OVIRT_NODE_DEFAULTS_FILENAME) afterwards all actual configurations files are
created based on this file. This module provides an high level to this model.

There are classes for all components which can be configured through that
central configuration file.
Each class (for a component) can have a configure and apply_config method. Look
at the CentralNodeConfiguration for more informations.

Each class should implement a configure method, mainly to define all the
required arguments (or keys).
"""

import logging
import glob

import ovirt.node.config
from ovirt.node import base, exceptions, valid, utils


LOGGER = logging.getLogger(__name__)

OVIRT_NODE_DEFAULTS_FILENAME = "/etc/defaults/ovirt"


class AugeasProvider(base.Base):
    def __init__(self, filename):
        super(AugeasProvider, self).__init__()
        self.filename = filename

    def update(self, new_dict, remove_empty):
        aug = utils.AugeasWrapper()
        basepath = "/files/%s/" % self.filename.strip("/")
        if new_dict:
            # If values are given, update the file
            LOGGER.debug("Updating oVirtNode defaults file '%s': %s %s" % (
                                                                self.filename,
                                                                new_dict,
                                                                basepath))
            aug.set_many(new_dict, basepath)

            if remove_empty:
                paths_to_be_removed = [p for p, v in new_dict.items()
                                       if v is None]
                aug.remove_many(paths_to_be_removed, basepath)

    def get_dict(self):
        aug = utils.AugeasWrapper()
        basepath = "/files/%s/" % self.filename.strip("/")

        # Retrieve all entries of the default file and return their values
        paths = aug.match(basepath + "*")
        return aug.get_many(paths, strip_basepath=basepath)


class SimpleProvider(base.Base):
    """Can write our simple configuration file

    >>> fn = "/tmp/cfg_dummy.simple"
    >>> open(fn, "w").close()
    >>> cfg = {
    ... "IP_ADDR": "127.0.0.1",
    ... "NETMASK": "255.255.255.0",
    ... }
    >>> p = SimpleProvider(fn)
    >>> p.get_dict()
    {}
    >>> p.update(cfg, True)
    >>> p.get_dict() == cfg
    True
    """
    def __init__(self, filename):
        super(SimpleProvider, self).__init__()
        self.filename = filename
        self.logger.debug("Using %s" % self.filename)

    def update(self, new_dict, remove_empty):
        cfg = self.get_dict()
        cfg.update(new_dict)

        for key, value in cfg.items():
            if remove_empty and value is None:
                del cfg[key]
            assert type(value) in [str, unicode] or value is None
        self._write(cfg)

    def get_dict(self):
        cfg = {}
        with open(self.filename) as source:
            for line in source:
                if line.startswith("#"):
                    continue
                key, value = line.split("=", 1)
                cfg[key] = value.strip("\"' \n")
        return cfg

    def _write(self, cfg):
        # FIXME make atomic
        contents = []
        # Sort the dict, looks nicer
        for key in sorted(cfg.iterkeys()):
            contents.append("%s='%s'" % (key, cfg[key]))
        with open(self.filename, "w+") as dst:
            dst.write("\n".join(contents))


class ConfigFile(base.Base):
    def __init__(self, filename=None, provider_class=None):
        super(ConfigFile, self).__init__()
        filename = filename or OVIRT_NODE_DEFAULTS_FILENAME
        provider_class = provider_class or SimpleProvider
        self.provider = provider_class(filename)

    def update(self, new_dict, remove_empty=False):
        """Reads /etc/defaults/ovirt and creates a dictionary
        The dict will contain all OVIRT_* entries of the defaults file.

        Args:
            new_dict: New values to be used for setting the defaults
            filename: The filename to read the defaults from
            remove_empty: Remove a key from defaults file, if the new value
                          is None
        Returns:
            A dict
        """
        self.logger.debug("Updating defaults: %s" % new_dict)
        self.logger.debug("Removing empty entries? %s" % remove_empty)
        self.provider.update(new_dict, remove_empty)

    def get_dict(self):
        return self.provider.get_dict()


class CentralNodeConfiguration(base.Base):
    def __init__(self, cfgfile=None):
        super(CentralNodeConfiguration, self).__init__()
        self.defaults = cfgfile or ConfigFile()

    def update(self, *args, **kwargs):
        """This function set's the correct entries in the defaults file for
        that specififc subclass.
        Is expected to call _map_config_and_update_defaults()
        """
        raise NotImplementedError

    def apply(self, *args, **kwargs):
        """This method updates the to this subclass specific configuration
        files according to the config keys set with configure.
        """
        raise NotImplementedError

    def retrieve(self):
        """Returns the config keys of the current component
        """
        func = self.update.wrapped_func
        varnames = func.func_code.co_varnames[1:]
        values = ()
        cfg = self.defaults.get_dict()
        for key in self.keys:
            value = cfg[key] if key in cfg else ""
            values += (value,)
        assert len(varnames) == len(values)
        return zip(varnames, values)

    def clear(self):
        """Remove the configuration for this item
        """
        cfg = self.defaults.get_dict()
        to_be_deleted = {k: None for k in self.keys}
        cfg.update(to_be_deleted)
        self.defaults.update(cfg, remove_empty=True)

    def _map_config_and_update_defaults(self, *args, **kwargs):
        assert len(args) == 0
        assert (set(self.keys) ^ set(kwargs.keys())) == set()
        new_dict = {k.upper(): v for k, v in kwargs.items()}
        self.defaults.update(new_dict, remove_empty=True)

    @staticmethod
    def map_and_update_defaults_decorator(func):
        """
        >>> class Foo(object):
        ...     keys = None
        ...     def _map_config_and_update_defaults(self, *args, **kwargs):
        ...         return kwargs
        ...     @CentralNodeConfiguration.map_and_update_defaults_decorator
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
            if len(self.keys) != len(args):
                raise Exception("There are not enough arguments given for " +
                                "%s of %s" % (func, self))
            new_cfg = dict(zip(self.keys, args))
            custom_cfg = func(self, *args, **kwargs) or {}
            assert type(custom_cfg) is dict, "%s must return a dict" % func
            new_cfg.update(custom_cfg)
            return self._map_config_and_update_defaults(**new_cfg)
        wrapper.wrapped_func = func
        return wrapper


class Network(CentralNodeConfiguration):
    """Sets network stuff
    - OVIRT_BOOTIF
    - OVIRT_IP_ADDRESS, OVIRT_IP_NETMASK, OVIRT_IP_GATEWAY
    - OVIRT_VLAN
    - OVIRT_IPV6

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = Network(cfgfile)
    >>> n.update("eth0", "static", "10.0.0.1", "255.0.0.0", "10.0.0.255",
    ...          "20")
    >>> data = n.retrieve()
    >>> data[:3]
    [('iface', 'eth0'), ('bootproto', 'static'), ('ipaddr', '10.0.0.1')]
    >>> data [3:]
    [('netmask', '255.0.0.0'), ('gw', '10.0.0.255'), ('vlanid', '20')]

    >>> n.clear()
    >>> data = n.retrieve()
    >>> data [:3]
    [('iface', None), ('bootproto', None), ('ipaddr', None)]
    >>> data [3:]
    [('netmask', None), ('gw', None), ('vlanid', None)]
    """
    keys = ("OVIRT_BOOTIF",
            "OVIRT_BOOTPROTO",
            "OVIRT_IP_ADDRESS",
            "OVIRT_NETMASK",
            "OVIRT_GATEWAY",
            "OVIRT_VLAN")

    @CentralNodeConfiguration.map_and_update_defaults_decorator
    def update(self, iface, bootproto, ipaddr=None, netmask=None, gw=None,
                  vlanid=None):
        if bootproto not in ["static", "none", "dhcp"]:
            raise exceptions.InvalidData("Unknown bootprotocol: %s" %
                                         bootproto)
        (valid.IPv4Address() | valid.Empty())(ipaddr)
        (valid.IPv4Address() | valid.Empty())(netmask)
        (valid.IPv4Address() | valid.Empty())(gw)


class Nameservers(CentralNodeConfiguration):
    """Configure nameservers
    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> servers = ["10.0.0.2", "10.0.0.3"]
    >>> n = Nameservers(cfgfile)
    >>> n.update(servers)
    >>> data = n.retrieve()
    >>> all([servers[idx] == s for idx, s in enumerate(data["servers"])])
    True
    """
    keys = ("OVIRT_DNS",)

    @CentralNodeConfiguration.map_and_update_defaults_decorator
    def update(self, servers):
        assert type(servers) is list
        servers = filter(lambda i: i.strip() not in ["", None], servers)
        map(valid.IPv4Address(), servers)
        return {
                "OVIRT_DNS": ",".join(servers)
                }

    def retrieve(self):
        cfg = dict(CentralNodeConfiguration.retrieve(self))
        return {
                "servers": cfg["servers"].split(",")
                }

    def apply(self):
        """Derives the nameserver config from OVIRT_DNS

        1. Parse nameservers from defaults
        2. Update resolv.conf
        3. Update ifcfg- (peerdns=no if manual resolv.conf)
        4. Persist resolv.conf

        Args:
            servers: List of servers (str)
        """
        ovirt_config = self.defaults.get_dict()
        if "OVIRT_DNS" not in ovirt_config:
            self.logger.debug("No DNS server entry in default config")
            return

        servers = ovirt_config["OVIRT_DNS"]
        if servers is None or servers == "":
            self.logger.debug("No DNS servers configured in default config")

        servers = servers.split(",")

        aug = utils.AugeasWrapper()
        # Write resolv.conf any way, sometimes without servers
        comment = ("Please make changes through the TUI. " + \
                   "Manual edits to this file will be " + \
                   "lost on reboot")
        aug.set("/files/etc/resolv.conf/#comment[1]", comment)

        # Now set the nameservers
        ovirt.node.config.network.nameservers(servers)

        # Set or remove PEERDNS for all ifcfg-*
        for nic in glob.glob("/etc/sysconfig/network-scripts/ifcfg-*"):
            if "ifcfg-lo" in nic:
                continue
            path = "/files%s/PEERDNS" % nic
            if len(servers) > 0:
                aug.set(path, "no")
            else:
                aug.remove(path)

        utils.fs.persist_config("/etc/resolv.conf")


class Timeservers(CentralNodeConfiguration):
    """Configure timeservers

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> servers = ["10.0.0.4", "10.0.0.5"]
    >>> n = Timeservers(cfgfile)
    >>> n.update(servers)
    >>> data = n.retrieve()
    >>> all([servers[idx] == s for idx, s in enumerate(data["servers"])])
    True
    """
    keys = ("OVIRT_NTP",)

    @CentralNodeConfiguration.map_and_update_defaults_decorator
    def update(self, servers):
        assert type(servers) is list
        servers = filter(lambda i: i.strip() not in ["", None], servers)
        map(valid.IPv4Address(), servers)
        return {
                "OVIRT_NTP": ",".join(servers)
                }

    def retrieve(self):
        cfg = dict(CentralNodeConfiguration.retrieve(self))
        return {
                "servers": cfg["servers"].split(",")
                }


class Syslog(CentralNodeConfiguration):
    """Configure rsyslog

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> server = "10.0.0.6"
    >>> port = "514"
    >>> n = Syslog(cfgfile)
    >>> n.update(server, port)
    >>> n.retrieve()
    [('server', '10.0.0.6'), ('port', '514')]
    """
    keys = ("OVIRT_SYSLOG_SERVER",
            "OVIRT_SYSLOG_PORT")

    @CentralNodeConfiguration.map_and_update_defaults_decorator
    def update(self, server, port):
        valid.FQDNOrIPAddress()(server)
        valid.Port()(port)


class Collectd(CentralNodeConfiguration):
    """Configure collectd

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> server = "10.0.0.7"
    >>> port = "42"
    >>> n = Collectd(cfgfile)
    >>> n.update(server, port)
    >>> n.retrieve()
    [('server', '10.0.0.7'), ('port', '42')]
    """
    keys = ("OVIRT_COLLECTD_SERVER",
            "OVIRT_COLLECTD_PORT")

    @CentralNodeConfiguration.map_and_update_defaults_decorator
    def update(self, server, port):
        valid.FQDNOrIPAddress()(server)
        valid.Port()(port)


class RHN(CentralNodeConfiguration):
    keys = ("OVIRT_RHN_TYPE",
            "OVIRT_RHN_URL",
            "OVIRT_RHN_CA_CERT",
            "OVIRT_RHN_USERNAME",
            "OVIRT_RHN_PASSWORD",
            "OVIRT_RHN_PROFILE",
            "OVIRT_RHN_ACTIVATIONKEY",
            "OVIRT_RHN_ORG",
            "OVIRT_RHN_PROXY",
            "OVIRT_RHN_PROXYUSER",
            "OVIRT_RHN_PROXYPASSWORD")

    @CentralNodeConfiguration.map_and_update_defaults_decorator
    def update(self, rhntype, url, ca_cert, username, password, profile,
                  activationkey, org, proxy, proxyuser, proxypassword):
        pass


class KDump(CentralNodeConfiguration):
    """Configure kdump

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> nfs_url = "host.example.com"
    >>> ssh_url = "root@host.example.com"
    >>> n = KDump(cfgfile)
    >>> n.update(nfs_url, ssh_url)
    >>> n.retrieve()
    [('nfs', 'host.example.com'), ('ssh', 'root@host.example.com')]
    """
    keys = ("OVIRT_KDUMP_NFS",
            "OVIRT_KDUMP_SSH")

    @CentralNodeConfiguration.map_and_update_defaults_decorator
    def update(self, nfs, ssh):
        valid.FQDNOrIPAddress()(nfs)
        valid.URL()(ssh)


class iSCSI(CentralNodeConfiguration):
    """Configure iSCSI

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = iSCSI(cfgfile)
    >>> n.update("node.example.com", "target.example.com", "10.0.0.8", "42")
    >>> data = n.retrieve()
    >>> data[:2]
    [('name', 'node.example.com'), ('target_name', 'target.example.com')]
    >>> data[2:]
    [('target_host', '10.0.0.8'), ('target_port', '42')]
    """
    keys = ("OVIRT_ISCSI_NODE_NAME",
            "OVIRT_ISCSI_TARGET_NAME",
            "OVIRT_ISCSI_TARGET_IP",
            "OVIRT_ISCSI_TARGET_PORT")

    @CentralNodeConfiguration.map_and_update_defaults_decorator
    def update(self, name, target_name, target_host, target_port):
        # FIXME add validation
        pass


class SNMP(CentralNodeConfiguration):
    """Configure SNMP

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = SNMP(cfgfile)
    >>> n.update("secret")
    >>> n.retrieve()
    [('password', 'secret')]
    """
    keys = ("OVIRT_SNMP_PASSWORD",)

    @CentralNodeConfiguration.map_and_update_defaults_decorator
    def update(self, password):
        # FIXME add validation
        pass


class Netconsole(CentralNodeConfiguration):
    """Configure netconsole

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = Netconsole(cfgfile)
    >>> server = "10.0.0.9"
    >>> port = "666"
    >>> n.update(server, port)
    >>> n.retrieve()
    [('server', '10.0.0.9'), ('port', '666')]
    """
    keys = ("OVIRT_NETCONSOLE_SERVER",
            "OVIRT_NETCONSOLE_PORT")

    @CentralNodeConfiguration.map_and_update_defaults_decorator
    def update(self, server, port):
        # FIXME add validation
        pass


class CIM(CentralNodeConfiguration):
    """Configure CIM

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = CIM(cfgfile)
    >>> n.update(True)
    >>> n.retrieve()
    [('enabled', '1')]
    """
    keys = ("OVIRT_CIM_ENABLED",)

    @CentralNodeConfiguration.map_and_update_defaults_decorator
    def update(self, enabled):
        return {
                "OVIRT_CIM_ENABLED": "1" if utils.parse_bool(enabled) else "0"
                }
