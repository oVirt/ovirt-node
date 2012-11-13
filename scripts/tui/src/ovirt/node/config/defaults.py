#!/usr/bin/python
#
# model.py - Copyright (C) 2012 Red Hat, Inc.
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

import ovirt.node.utils
import ovirt.node.config
from ovirt.node import base


LOGGER = logging.getLogger(__name__)

OVIRT_NODE_DEFAULTS_FILENAME = "/etc/defaults/ovirt"


def defaults(new_dict=None, filename=OVIRT_NODE_DEFAULTS_FILENAME,
             remove_empty=False):
    """Reads /etc/defaults/ovirt and creates a dictionary
    The dict will contain all OVIRT_* entries of the defaults file.

    Args:
        new_dict: New values to be used for setting the defaults
        filename: The filename to read the defaults from
        remove_empty: Remove a key from defaults file, if the new value is None
    Returns:
        A dict
    """

    aug = ovirt.node.utils.AugeasWrapper()
    basepath = "/files/%s/" % filename.strip("/")
    if new_dict:
        # If values are given, update the file
        LOGGER.debug("Updating oVirtNode defaults file '%s': %s %s" % (
                                                                    filename,
                                                                    new_dict,
                                                                    basepath))
        aug.set_many(new_dict, basepath)

        if remove_empty:
            paths_to_be_removed = [p for p, v in new_dict.items() if v is None]
            aug.remove_many(paths_to_be_removed, basepath)

    # Retrieve all entries of the default file and return their values
    paths = aug.match(basepath + "*")
    return aug.get_many(paths, strip_basepath=basepath)


def map_and_update_defaults(func):
    """
    >>> class Foo(object):
    ...     keys = None
    ...     def _map_config_and_update_defaults(self, *args, **kwargs):
    ...         return kwargs
    ...     @map_and_update_defaults
    ...     def meth(self, a, b):
    ...         assert type(a) is int
    ...         assert type(b) is int
    >>> foo = Foo()
    >>> foo.keys = ("OVIRT_A", "OVIRT_B")
    >>> foo.meth(1, 2)
    {'OVIRT_A': 1, 'OVIRT_B': 2}
    """
    def wrapper(self, *args, **kwargs):
        new_dict = dict(zip(self.keys, args))
        func(self, *args, **kwargs)
        return self._map_config_and_update_defaults(**new_dict)
    return wrapper


class CentralNodeConfiguration(base.Base):
    def __init__(self, keys):
        assert type(keys) is tuple, "Keys need to have an order, " + \
                                    "therefor a tuple expected"
        self.keys = keys

    def configure(self, *args, **kwargs):
        """This function set's the correct entries in the defaults file for
        that specififc subclass.
        Is expected to call _map_config_and_update_defaults()
        """
        raise NotImplementedError

    def _map_config_and_update_defaults(self, *args, **kwargs):
        assert len(args) == 0
        assert (set(self.keys) ^ set(kwargs.keys())) == set()
        new_dict = {k.upper(): v for k, v in kwargs.items()}
        defaults(new_dict, remove_empty=True)

    def apply_config(self, *args, **kwargs):
        """This method updates the to this subclass specififc configuration
        files according to the config keys set with configure.
        """
        raise NotImplementedError

    def get_config(self):
        """Returns the config keys of the current component
        """
        items = {}
        for key, value in defaults().items():
            if key in self.keys:
                items[key] = value
        return items


class Network(CentralNodeConfiguration):
    """Sets network stuff
    - OVIRT_BOOTIF
    - OVIRT_IP_ADDRESS, OVIRT_IP_NETMASK, OVIRT_IP_GATEWAY
    - OVIRT_VLAN
    - OVIRT_IPV6
    """
    keys = ("OVIRT_BOOTIF",
            "OVIRT_BOOTPROTO",
            "OVIRT_IP_ADDRESS",
            "OVIRT_IP_NETMASK",
            "OVIRT_IP_GATEWAY",
            "OVIRT_VLAN")

    @map_and_update_defaults
    def configure(self, iface, bootproto, ipaddr=None, netmask=None, gw=None,
                  vlanid=None):
        pass


class Nameservers(CentralNodeConfiguration):
    keys = ("OVIRT_DNS")

    @map_and_update_defaults
    def configure(self, servers):
        pass


    def apply_config(self):
        """Derives the nameserver config from OVIRT_DNS

        1. Parse nameservers from defaults
        2. Update resolv.conf
        3. Update ifcfg- (peerdns=no if manual resolv.conf)
        4. Persist resolv.conf

        Args:
            servers: List of servers (str)
        """
        ovirt_config = defaults()
        if "OVIRT_DNS" not in ovirt_config:
            self.logger.debug("No DNS server entry in default config")
            return

        servers = ovirt_config["OVIRT_DNS"]
        if servers is None or servers == "":
            self.logger.debug("No DNS servers configured in default config")

        servers = servers.split(",")

        aug = ovirt.node.utils.AugeasWrapper()
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

        ovirt.node.utils.fs.persist_config("/etc/resolv.conf")


class Timeservers(CentralNodeConfiguration):
    keys = ("OVIRT_NTP")

    @map_and_update_defaults
    def configure(self, servers):
        pass


class Syslog(CentralNodeConfiguration):
    keys = ("OVIRT_SYSLOG_SERVER",
            "OVIRT_SYSLOG_PORT")

    @map_and_update_defaults
    def configure(self, server, port):
        pass


class Collectd(CentralNodeConfiguration):
    keys = ("OVIRT_COLLECTD_SERVER",
            "OVIRT_COLLECTD_PORT")

    @map_and_update_defaults
    def configure(self, server, port):
        pass


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

    @map_and_update_defaults
    def configure(self, rhntype, url, ca_cert, username, password, profile,
                  activationkey, org, proxy, proxyuser, proxypassword):
        pass


class KDump(CentralNodeConfiguration):
    keys = ("OVIRT_KDUMP_NFS",
            "OVIRT_KDUMP_SSH")

    @map_and_update_defaults
    def configure(self, nfs, ssh):
        pass


class iSCSI(CentralNodeConfiguration):
    keys = ("OVIRT_ISCSI_NODE_NAME",
            "OVIRT_ISCSI_TARGET_NAME",
            "OVIRT_ISCSI_TARGET_IP",
            "OVIRT_ISCSI_TARGET_PORT")

    @map_and_update_defaults
    def configure(self, name, target_name, target_host, target_port):
        pass


class SNMP(CentralNodeConfiguration):
    keys = ("OVIRT_SNMP_PASSWORD")

    @map_and_update_defaults
    def configure(self, password):
        pass


class Netconsole(CentralNodeConfiguration):
    keys = ("OVIRT_NETCONSOLE_SERVER",
            "OVIRT_NETCONSOLE_PORT")

    @map_and_update_defaults
    def configure(self, server, port):
        pass


class CIM(CentralNodeConfiguration):
    keys = ("OVIRT_CIM_ENABLED")

    @map_and_update_defaults
    def configure(self, enabled):
        assert enabled in ["1", "0"]