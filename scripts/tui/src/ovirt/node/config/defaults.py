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
from ovirt.node import base, exceptions, valid, utils
import glob
import logging
import os
import ovirt.node.config

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

LOGGER = logging.getLogger(__name__)

OVIRT_NODE_DEFAULTS_FILENAME = "/etc/default/ovirt"


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


class NodeConfigFileSection(base.Base):
    none_value = None

    def __init__(self, cfgfile=None):
        super(NodeConfigFileSection, self).__init__()
        self.defaults = cfgfile or ConfigFile()

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
        tx()

    def retrieve(self):
        """Returns the config keys of the current component

        Returns:
            A dict with a mapping (arg, value).
            arg corresponds to the named arguments of the subclass's configure()
            method.
        """
        func = self.update.wrapped_func
        varnames = func.func_code.co_varnames[1:]
        values = ()
        cfg = self.defaults.get_dict()
        for key in self.keys:
            value = cfg[key] if key in cfg else self.none_value
            values += (value,)
        assert len(varnames) == len(values)
        return dict(zip(varnames, values))

    def clear(self):
        """Remove the configuration for this item
        """
        cfg = self.defaults.get_dict()
        to_be_deleted = {k: None for k in self.keys}
        cfg.update(to_be_deleted)
        self.defaults.update(cfg, remove_empty=True)

    def _map_config_and_update_defaults(self, *args, **kwargs):
        assert len(args) == 0
        assert (set(self.keys) ^ set(kwargs.keys())) == set(), \
               "Keys: %s, Args: %s" % (self.keys, kwargs)
        new_dict = {k.upper(): v for k, v in kwargs.items()}
        self.defaults.update(new_dict, remove_empty=True)

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
            assert kwargs == {}, "kwargs are not allowed for these functions"
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


class Network(NodeConfigFileSection):
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
    >>> data = sorted(n.retrieve().items())
    >>> data[:3]
    [('bootproto', 'static'), ('gateway', '10.0.0.255'), ('iface', 'eth0')]
    >>> data[3:]
    [('ipaddr', '10.0.0.1'), ('netmask', '255.0.0.0'), ('vlanid', '20')]

    >>> n.clear()
    >>> data = sorted(n.retrieve().items())
    >>> data[:3]
    [('bootproto', ''), ('gateway', ''), ('iface', '')]
    >>> data[3:]
    [('ipaddr', ''), ('netmask', ''), ('vlanid', '')]
    """
    keys = ("OVIRT_BOOTIF",
            "OVIRT_BOOTPROTO",
            "OVIRT_IP_ADDRESS",
            "OVIRT_NETMASK",
            "OVIRT_GATEWAY",
            "OVIRT_VLAN")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, iface, bootproto, ipaddr=None, netmask=None, gateway=None,
                  vlanid=None):
        if bootproto not in ["static", "none", "dhcp", None]:
            raise exceptions.InvalidData("Unknown bootprotocol: %s" %
                                         bootproto)
        (valid.IPv4Address() | valid.Empty(or_none=True))(ipaddr)
        (valid.IPv4Address() | valid.Empty(or_none=True))(netmask)
        (valid.IPv4Address() | valid.Empty(or_none=True))(gateway)

    def transaction(self):
        """Return all transactions to re-configure networking

        FIXME this should be rewritten o allow more fine grained progress
        informations
        """
        class ConfigureNIC(utils.Transaction.Element):
            title = "Configuring NIC"

            def prepare(self):
                self.logger.debug("Psuedo prewparing ovirtnode.Network")

            def commit(self):
                from ovirtnode.network import Network as oNetwork
                net = oNetwork()
                net.configure_interface()
                net.save_network_configuration()

        tx = utils.Transaction("Saving network configuration")
        tx.append(ConfigureNIC())
        return tx


class Nameservers(NodeConfigFileSection):
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

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, servers):
        assert type(servers) is list
        servers = filter(lambda i: i.strip() not in ["", None], servers)
        map(valid.IPv4Address(), servers)
        return {
                "OVIRT_DNS": ",".join(servers)
                }

    def retrieve(self):
        """We mangle the original vale a bit for py convenience
        """
        cfg = dict(NodeConfigFileSection.retrieve(self))
        cfg.update({
            "servers": cfg["servers"].split(",")
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
        ovirt_config = self.defaults.get_dict()

        tx = utils.Transaction("Configuring DNS")

        if "OVIRT_DNS" not in ovirt_config:
            self.logger.debug("No DNS server entry in default config")
            return tx

        servers = ovirt_config["OVIRT_DNS"]
        if servers is None or servers == "":
            self.logger.debug("No DNS servers configured " +
                              "in default config")
        servers = servers.split(",")

        class UpdateResolvConf(utils.Transaction.Element):
            title = "Updateing resolv.conf"

            def commit(self):
                # Write resolv.conf any way, sometimes without servers
                comment = ("Please make changes through the TUI. " + \
                           "Manual edits to this file will be " + \
                           "lost on reboot")
                aug.set("/files/etc/resolv.conf/#comment[1]", comment)
                # Now set the nameservers
                ovirt.node.config.network.nameservers(servers)
                utils.fs.persist_config("/etc/resolv.conf")

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

        tx += [UpdateResolvConf(), UpdatePeerDNS()]

        return tx


class Timeservers(NodeConfigFileSection):
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

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, servers):
        assert type(servers) is list
        servers = filter(lambda i: i.strip() not in ["", None], servers)
        map(valid.IPv4Address(), servers)
        return {
                "OVIRT_NTP": ",".join(servers)
                }

    def retrieve(self):
        cfg = dict(NodeConfigFileSection.retrieve(self))
        cfg.update({
            "servers": cfg["servers"].split(",")
            })
        return cfg

    def transaction(self):
        return utils.Transaction("Configuring timeserver")


class Syslog(NodeConfigFileSection):
    """Configure rsyslog

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> server = "10.0.0.6"
    >>> port = "514"
    >>> n = Syslog(cfgfile)
    >>> n.update(server, port)
    >>> sorted(n.retrieve().items())
    [('port', '514'), ('server', '10.0.0.6')]
    """
    keys = ("OVIRT_SYSLOG_SERVER",
            "OVIRT_SYSLOG_PORT")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, server, port):
        valid.FQDNOrIPAddress()(server)
        valid.Port()(port)

    def transaction(self):
        cfg = dict(self.retrieve())
        server, port = (cfg["server"], cfg["port"])

        class CreateRsyslogConfig(utils.Transaction.Element):
            def commit(self):
                import ovirtnode.log as olog
                olog.ovirt_rsyslog(server, port, "udp")

        tx = utils.Transaction("Configuring syslog")
        tx.append(CreateRsyslogConfig())
        return tx


class Collectd(NodeConfigFileSection):
    """Configure collectd

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> server = "10.0.0.7"
    >>> port = "42"
    >>> n = Collectd(cfgfile)
    >>> n.update(server, port)
    >>> sorted(n.retrieve().items())
    [('port', '42'), ('server', '10.0.0.7')]
    """
    keys = ("OVIRT_COLLECTD_SERVER",
            "OVIRT_COLLECTD_PORT")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, server, port):
        valid.FQDNOrIPAddress()(server)
        valid.Port()(port)


class RHN(NodeConfigFileSection):
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

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, rhntype, url, ca_cert, username, password, profile,
                  activationkey, org, proxy, proxyuser, proxypassword):
        pass


class KDump(NodeConfigFileSection):
    """Configure kdump

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> nfs_url = "host.example.com"
    >>> ssh_url = "root@host.example.com"
    >>> n = KDump(cfgfile)
    >>> n.update(nfs_url, ssh_url, True)
    >>> d = sorted(n.retrieve().items())
    >>> d[:2]
    [('local', True), ('nfs', 'host.example.com')]
    >>> d[2:]
    [('ssh', 'root@host.example.com')]
    """
    keys = ("OVIRT_KDUMP_NFS",
            "OVIRT_KDUMP_SSH",
            "OVIRT_KDUMP_LOCAL")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, nfs, ssh, local):
        (valid.Empty(or_none=True) | valid.FQDNOrIPAddress())(nfs)
        (valid.Empty(or_none=True) | valid.URL())(ssh)
        (valid.Empty(or_none=True) | valid.Boolean())(local)
        return {
                "OVIRT_KDUMP_LOCAL": "true" if local else None
                }

    def transaction(self):
        cfg = dict(self.retrieve())
        nfs, ssh, restore = (cfg["nfs"], cfg["ssh"], cfg["local"])

        class BackupKdumpConfig(utils.Transaction.Element):
            def __init__(self):
                self.backups = utils.fs.BackupedFiles(["/etc/kdump.conf"])

            def commit(self):
                self.backups.create()

        class RestoreKdumpConfig(utils.Transaction.Element):
            def commit(self):
                import ovirtnode.kdump as okdump
                okdump.restore_kdump_config()

        class CreateNfsKdumpConfig(utils.Transaction.Element):
            def commit(self):
                import ovirtnode.kdump as okdump
                okdump.write_kdump_config(nfs)

        class CreateSshKdumpConfig(utils.Transaction.Element):
            def commit(self):
                import ovirtnode.kdump as okdump
                from ovirtnode.ovirtfunctions import ovirt_store_config

                okdump.write_kdump_config(ssh)

                if os.path.exists("/usr/bin/kdumpctl"):
                    cmd = "kdumpctl propagate"
                else:
                    cmd = "service kdump propagate"
                cmd += "2>&1"

                success, stdout = utils.process.pipe(cmd)

                if success:
                    ovirt_store_config(["/root/.ssh/kdump_id_rsa.pub",
                                        "/root/.ssh/kdump_id_rsa",
                                        "/root/.ssh/known_hosts",
                                        "/root/.ssh/config"])
                else:
                    self.logger.warning("Failed to activate KDump with " +
                                        "SSH: %s" % stdout)

        class RemoveKdumpConfig(utils.Transaction.Element):
            def __init__(self, backups):
                self.backups = backups

            def commit(self):
                from ovirtnode.ovirtfunctions import remove_config

                remove_config("/etc/kdump.conf")
                utils.process.system("service kdump stop")
                open('/etc/kdump.conf', 'w').close()

                self.backups.remove()

        class RestartKdumpService(utils.Transaction.Element):
            def __init__(self, backups):
                self.backups = backups

            def commit(self):
                from ovirtnode.ovirtfunctions import unmount_config, \
                                                     ovirt_store_config
                from ovirt.node.utils.process import system

                if utils.process.system("service kdump restart") > 0:
                    unmount_config("/etc/kdump.conf")
                    self.backups.restore("/etc/kdump.conf")
                    system("service kdump restart")

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
        elif restore:
            tx.append(RestoreKdumpConfig())
        else:
            final_txe = RemoveKdumpConfig(backup_txe.backups)

        tx.append(final_txe)

        return tx


class iSCSI(NodeConfigFileSection):
    """Configure iSCSI

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = iSCSI(cfgfile)
    >>> n.update("node.example.com", "target.example.com", "10.0.0.8", "42")
    >>> data = sorted(n.retrieve().items())
    >>> data[:2]
    [('name', 'node.example.com'), ('target_host', '10.0.0.8')]
    >>> data[2:]
    [('target_name', 'target.example.com'), ('target_port', '42')]
    """
    keys = ("OVIRT_ISCSI_NODE_NAME",
            "OVIRT_ISCSI_TARGET_NAME",
            "OVIRT_ISCSI_TARGET_IP",
            "OVIRT_ISCSI_TARGET_PORT")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, name, target_name, target_host, target_port):
        # FIXME add validation
        pass

    def transaction(self):
        cfg = dict(self.retrieve())
        initiator_name = cfg["name"]

        class ConfigureIscsiInitiator(utils.Transaction.Element):
            def commit(self):
                from ovirtnode.iscsi import set_iscsi_initiator
                set_iscsi_initiator(initiator_name)

        tx = utils.Transaction("Configuring the iSCSI Initiator")
        tx.append(ConfigureIscsiInitiator())
        return tx


class SNMP(NodeConfigFileSection):
    """Configure SNMP

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = SNMP(cfgfile)
    >>> n.update("secret")
    >>> n.retrieve().items()
    [('password', 'secret')]
    """
    keys = ("OVIRT_SNMP_PASSWORD",)

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, password):
        # FIXME add validation
        pass


class Netconsole(NodeConfigFileSection):
    """Configure netconsole

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = Netconsole(cfgfile)
    >>> server = "10.0.0.9"
    >>> port = "666"
    >>> n.update(server, port)
    >>> sorted(n.retrieve().items())
    [('port', '666'), ('server', '10.0.0.9')]
    """
    keys = ("OVIRT_NETCONSOLE_SERVER",
            "OVIRT_NETCONSOLE_PORT")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, server, port):
        valid.FQDNOrIPAddress()(server)
        valid.Port()(port)

    def transaction(self):
        cfg = dict(self.retrieve())
        server, port = (cfg["server"], cfg["port"])

        class CreateNetconsoleConfig(utils.Transaction.Element):
            def commit(self):
                import ovirtnode.log as olog
                olog.ovirt_netconsole(server, port, "udp")

        tx = utils.Transaction("Configuring netconsole")
        tx.append(CreateNetconsoleConfig())
        return tx


class Logrotate(NodeConfigFileSection):
    """Configure logrotate

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = Logrotate(cfgfile)
    >>> max_size = "42"
    >>> n.update(max_size)
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
            def commit(self):
                import ovirtnode.log as olog
                olog.set_logrotate_size(max_size)

        tx = utils.Transaction("Configuring logrotate")
        tx.append(CreateLogrotateConfig())
        return tx


class CIM(NodeConfigFileSection):
    """Configure CIM

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = CIM(cfgfile)
    >>> n.update(True)
    >>> n.retrieve()
    {'enabled': '1'}
    """
    keys = ("OVIRT_CIM_ENABLED",)

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, enabled):
        return {
                "OVIRT_CIM_ENABLED": "1" if utils.parse_bool(enabled) else "0"
                }


class Keyboard(NodeConfigFileSection):
    """Configure keyboard

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = Keyboard(cfgfile)
    >>> layout = "de_DE.UTF-8"
    >>> n.update(layout)
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
            def commit(self):
                from ovirtnode.ovirtfunctions import ovirt_store_config
                kbd = utils.Keyboard()
                kbd.set_layout(layout)
                ovirt_store_config(["/etc/sysconfig/keyboard",
                                    "/etc/vconsole.conf"])

        tx = utils.Transaction("Configuring keyboard layout")
        tx.append(CreateKeyboardConfig())
        return tx


class NFSv4(NodeConfigFileSection):
    """Configure NFSv4

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = NFSv4(cfgfile)
    >>> domain = "foo.example"
    >>> n.update(domain)
    >>> n.retrieve().items()
    [('domain', 'foo.example')]
    """
    # FIXME this key is new!
    keys = ("OVIRT_NFSV4_DOMAIN",)

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, domain):
        # FIXME Some validation that layout is in the list of available layouts
        pass

    def transaction(self):
        cfg = dict(self.retrieve())
        domain = cfg["domain"]

        class ConfigureNfsv4(utils.Transaction.Element):
            def commit(self):
                from ovirtnode.network import set_nfsv4_domain
                set_nfsv4_domain(domain)

        tx = utils.Transaction("Configuring NFSv4")
        if domain:
            tx.append(ConfigureNfsv4())
        return tx


class SSH(NodeConfigFileSection):
    """Configure SSH

    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = SSH(cfgfile)
    >>> pwauth = True
    >>> num_bytes = "24"
    >>> disable_aesni = True
    >>> n.update(pwauth, num_bytes, disable_aesni)
    >>> sorted(n.retrieve().items())
    [('disable_aesni', True), ('num_bytes', '24'), ('pwauth', True)]
    """
    keys = ("OVIRT_SSH_PWAUTH",
            "OVIRT_USE_STRONG_RNG",
            "OVIRT_DISABLE_AES_NI")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, pwauth, num_bytes, disable_aesni):
        valid.Boolean()(pwauth)
        valid.Number()(num_bytes)
        valid.Boolean()(disable_aesni)
        return {
                "OVIRT_SSH_PWAUTH": "yes" if pwauth else None,
                "OVIRT_DISABLE_AES_NI": "true" if disable_aesni else None
                }

    def retrieve(self):
        cfg = dict(NodeConfigFileSection.retrieve(self))
        cfg.update({
                "pwauth": True if cfg["pwauth"] == "yes" else False,
                "disable_aesni": True if cfg["disable_aesni"] == "true" \
                                      else False
                })
        return cfg

    def transaction(self):
        cfg = dict(self.retrieve())
        pwauth, num_bytes, aesni = (cfg["pwauth"], cfg["num_bytes"],
                                    cfg["aesni"])

        ssh = utils.security.Ssh()

        class ConfigurePasswordAuthentication(utils.Transaction.Element):
            def commit(self):
                ssh.password_authentication(pwauth)

        class ConfigureStrongRNG(utils.Transaction.Element):
            def commit(self):
                ssh.strong_rng(num_bytes)

        class ConfigureAESNI(utils.Transaction.Element):
            def commit(self):
                ssh.aes_ni(aesni)

        tx = utils.Transaction("Configuring SSH")
        if pwauth:
            tx.append(ConfigurePasswordAuthentication())
        if num_bytes:
            tx.append(ConfigureStrongRNG())
        if aesni:
            tx.append(ConfigureAESNI())
        return tx
