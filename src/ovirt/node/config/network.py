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
from ovirt.node import utils, base, log
from ovirt.node.utils import AugeasWrapper as Augeas, fs, is_fileobj
from ovirt.node.utils.fs import ShellVarFile
import glob
import os

"""
Some convenience functions related to networking
"""


LOGGER = log.getLogger(__name__)


class NicConfig(base.Base):
    """A common interface to NIC configuration options
    """
    ifname = None

    type = None
    bootproto = None
    ipaddr = None
    netmask = None
    gateway = None
    bridge = None
    vlan = None
    device = None
    onboot = None
    delay = None
    hwaddr = None

    ipv6init = None
    ipv6forwarding = None
    ipv6_autoconf = None
    dhcpv6c = None
    ipv6addr = None
    ipv6_defaultgw = None

    peerntp = None
    peerdns = None

    master = None
    slave = None
    bonding_opts = None

    vlan_parent = None

    _backend = None

    _keys = ["bridge", "type", "bootproto", "ipaddr", "netmask",
             "gateway", "vlan", "device", "onboot", "hwaddr",
             "ipv6init", "ipv6forwarding", "ipv6_autoconf",
             "dhcpv6c", "ipv6addr", "ipv6_defaultgw", "delay",
             "peerntp", "peerdns",
             "master", "slave", "bonding_opts"]

    def __init__(self, ifname):
        super(NicConfig, self).__init__()
        self.ifname = ifname
        self._backend = self._backend_type(self, ifname)
        self.load()

    def exists(self):
        """Return if a config exists
        """
        return self._backend.exists()

    def load(self):
        data = self._backend.read()
        # Additional convenience stuff
        self.vlan = self.vlan.strip() if self.vlan else self.vlan
        if self.vlan:
            parts = self.ifname.split(".")
            self.vlan_id = parts[-1:][0]
            self.vlan_parent = ".".join(parts[:-1])

            self.logger.debug("Found VLAN %s on %s" %
                              (str(self.vlan_id), self.ifname))
        return data

    def save(self):
        return self._backend.write()

    def delete(self):
        return self._backend.delete()

    def __str__(self):
        return self.build_str("ifname")

    @staticmethod
    def list():
        return NicConfig._backend_type.list()

    class IfcfgBackend(ShellVarFile):
        filename_tpl = "/etc/sysconfig/network-scripts/ifcfg-%s"
        filename = None

        def __init__(self, cfg, ifname):
            self.cfg = cfg
            filename = ifname
            if not is_fileobj(ifname):
                filename = self.filename_tpl % ifname
            super(NicConfig.IfcfgBackend, self).__init__(filename, True)

        def read(self):
            """Read values from a ifcfg file and update self.cfg
            """
            if not self.exists():
                self.logger.debug("Config does not exist: %s" %
                                  self.filename)
                return

            data = self.get_dict()

            for k in self.cfg._keys:
                self.cfg.__dict__[k] = data.get(k.upper(), None)

        def write(self):
            """Write a ifcfg file from the cfg
            """

            data = {}
            for k in self.cfg._keys:
                data[k.upper()] = self.cfg.__dict__.get(k)

            ShellVarFile.write(self, data, True)

            pcfg = fs.Config()
            if pcfg.is_enabled():
                pcfg.persist(self.filename)

            return data

        def delete(self):
            pcfg = fs.Config()
            if pcfg.is_enabled():
                pcfg.unpersist(self.filename)

            self._fileobj.delete()

        @staticmethod
        def list():
            """List all available configuration
            """
            configs = []
            prefix = NicConfig.IfcfgBackend.filename_tpl % ""
            for fn in os.listdir(os.path.dirname(prefix)):
                configs.append(fn.replace("ifcfg-", ""))
            return configs
    _backend_type = IfcfgBackend


def _aug_get_or_set(augpath, new_servers=None):
    """Get or set some servers
    """
    aug = Augeas()
    aug.save()
    aug.force_reload()

    servers = []
    for path in aug.match(augpath):
        servers.append(aug.get(path))

    LOGGER.debug("Current servers: %s" % servers)

    if new_servers is not None:
        itempath = lambda idx: "%s[%d]" % (augpath, idx + 1)
        LOGGER.debug("Removing old servers: %s" % servers)
        for idx, server in enumerate(servers):
            LOGGER.debug("Removing server %s: %s" % (itempath(idx),
                                                     server))
            aug.remove(itempath(idx))
        LOGGER.debug("Setting new servers: %s" % new_servers)
        for idx, server in enumerate(new_servers):
            LOGGER.debug("Setting server %s: %s" % (itempath(idx), server))
            aug.set(itempath(idx), server)
    return servers


def nameservers(new_servers=None):
    """Get or set DNS servers

    >>> import ovirt.node.utils.process as p
    >>> stdout = p.pipe("egrep '^nameserver' /etc/resolv.conf | wc -l",
    ...                 shell=True)
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
    Using the hostnamectl tool
    """
    hostnamefile = "/etc/hostname"

    if not os.path.isfile(hostnamefile):
        return __legacy_hostname(new_hostname)

    if new_hostname:
        # hostnamectl set's runtime and config file
        utils.process.check_call(["hostnamectl", "--static", "set-hostname",
                                  new_hostname])

    current_hostname = utils.fs.get_contents(hostnamefile)
    if new_hostname and current_hostname != new_hostname:
        raise RuntimeError(("Runtime hostname '%s' doesn't match" +
                            "configured one: %s") % (current_hostname,
                                                     new_hostname))

    return current_hostname


def __legacy_hostname(new_hostname=None):
    """The legacy way of setting a hostname.
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


def ifaces():
    """Returns all configured ifaces
    """
    ifaces = []
    filepath = "/etc/sysconfig/network-scripts/ifcfg-"
    for fn in glob.glob("%s*" % filepath):
        iface = fn[len(filepath):]
        ifaces.append(iface)
    return ifaces
