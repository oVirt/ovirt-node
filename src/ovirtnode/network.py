#!/usr/bin/python
# network.py - Copyright (C) 2010 Red Hat, Inc.
# Written by Joey Boggs <jboggs@redhat.com>
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

from glob import glob
from ovirt.node.utils import Transaction
from pipes import quote
import logging
import os
import subprocess
import tempfile
logger = logging.getLogger(__name__)


class Network:
    def __init__(self):
        self.WORKDIR = tempfile.mkdtemp()
        self.IFSCRIPTS_PATH = "/etc/sysconfig/network-scripts/ifcfg-"
        self.IFCONFIG_FILE_ROOT = "/files%s" % self.IFSCRIPTS_PATH
        self.NTP_CONFIG_FILE = "/etc/ntp.conf"
        self.NTPSERVERS = ""
        self.CONFIGURED_NIC = ""
        self.CONFIGURED_NICS = []
        self.IF_CONFIG = ""
        self.BR_CONFIG = ""
        self.VL_CONFIG = ""
        self.VLAN_ID = ""
        self.VL_ROOT = ""
        self.VL_FILENAME = ""
        self.nic = ""
        self.bridge = ""
        self.vlan_id = ""

    def configure_dns(self):
        from ovirt.node.config.defaults import Nameservers
        return Nameservers().commit()


class SetDefaultBootproto(Transaction.Element):
    title = "Setting DHCP"

    def commit(self):
        from ovirt.node.config import defaults
        defaults.Network().update(bootproto="dhcp")


def build_network_auto_transaction():
    from ovirt.node.config.defaults import Network, Nameservers, \
        Timeservers, Hostname

    txs = Transaction("Automatic Installation")

    mhostname = Hostname()
    txs += mhostname.transaction()

    mnet = Network()
    netmodel = mnet.retrieve()
    logger.debug("Got netmodel: %s" % netmodel)

    if netmodel["iface"]:
        if not netmodel["ipaddr"]:
            txs.append(SetDefaultBootproto())

        txs += mnet.transaction()

        mdns = Nameservers()
        txs += mdns.transaction()

        mntp = Timeservers()
        txs += mntp.transaction()

    return txs
