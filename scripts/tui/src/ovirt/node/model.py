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
oVirt Node Model functions
"""

import logging
import glob

import ovirt.node.utils

LOGGER = logging.getLogger(__name__)

OVIRT_NODE_DEFAULTS_FILENAME = "/etc/defaults/ovirt"


def defaults(new_dict=None, filename=OVIRT_NODE_DEFAULTS_FILENAME):
    """Reads /etc/defaults/ovirt

    Args:
        new_dict: New values to be used for setting the defaults
    Returns:
        A dict
    """
    aug = ovirt.node.utils.AugeasWrapper()
    basepath = "/files/%s/" % filename.strip("/")
    if new_dict:
        # If values are given, update the file
        aug.set_many(new_dict, basepath + "OVIRT_")

    # Retrieve all entries of the default file and return their values
    paths = aug.match(basepath + "*")
    return aug.get_many(paths)


def configure_networking(iface, bootproto, ipaddr=None, netmask=None, gw=None,
                         vlanid=None):
    """Sets
        - OVIRT_BOOTIF
        - OVIRT_IP_ADDRESS, OVIRT_IP_NETMASK, OVIRT_IP_GATEWAY
        - OVIRT_VLAN
        - OVIRT_IPV6
    """
    config = {
        "BOOTIF": iface,
        "BOOTPROTO": bootproto,
        "IP_ADDRESS": ipaddr,
        "IP_NETMASK": netmask,
        "IP_GATEWAY": gw,
        "VLAN": vlanid
    }
    defaults(config)
    # FIXME also remove keys with None value?


def configure_nameservers(servers):
    """Sets OVIRT_DNS

    1. Parse nameservers from defaults
    2. Update resolv.conf
    3. Update ifcfg- (peerdns=no if manual resolv.conf)
    4. Persist resolv.conf

    Args:
        servers: List of servers (str)
    """
    ovirt_config = defaults()
    if "OVIRT_DNS" not in ovirt_config:
        LOGGER.debug("No DNS server entry in default config")
        return

    servers = ovirt_config["OVIRT_DNS"]
    if servers is None or servers == "":
        LOGGER.debug("No DNS servers configured in default config")

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


def timeservers(servers):
    """Sets OVIRT_NTP

    Args:
        servers: List of servers (str)
    """
    pass


def syslog(server, port):
    """Sets OVIRT_SYSLOG_{SERVER,PORT}
    """
    pass


def collectd(server, port):
    """Sets OVIRT_COLLECTD_{SERVER,PORT}
    """
    pass


def rhn(rhntype, url, ca_cert, username, password, profile, activationkey, org,
        proxy, proxyuser, proxypassword):
    """Sets ...
    """
    pass


def kdump(nfs, ssh):
    """Sets ...
    """
    pass


def iscsi(name, target_name, target_host, target_port):
    """Sets ...
    """
    pass


def snmp(password):
    """Sets ...
    """
    pass


def netconsole(server, port):
    """Sets ...
    """
    pass


def cim(enabled):
    """Sets ...
    """
    pass
