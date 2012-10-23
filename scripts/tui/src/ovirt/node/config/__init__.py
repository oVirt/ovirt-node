#!/usr/bin/python
#
# __init__.py - Copyright (C) 2012 Red Hat, Inc.
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
Config functions
"""

import logging

LOGGER = logging.getLogger(__name__)


def configure_networking(iface, bootproto, ipaddr=None, netmask=None, gw=None,
                         vlanid=None):
    """Sets
        - OVIRT_BOOTIF
        - OVIRT_IP_ADDRESS, OVIRT_IP_NETMASK, OVIRT_IP_GATEWAY
        - OVIRT_VLAN
        - OVIRT_IPV6
    """
    if bootproto == "dhcp":
        pass
    elif bootproto == "static":
        pass


def disable_networking():
    """Unsets
        - OVIRT_BOOTIF
        - OVIRT_IP_ADDRESS, OVIRT_IP_NETMASK, OVIRT_IP_GATEWAY
        - OVIRT_VLAN
        - OVIRT_IPV6
    """
    pass


def nameservers(servers):
    """Sets OVIRT_DNS

    Args:
        servers: List of servers (str)
    """
    pass


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
