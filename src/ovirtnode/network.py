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
from ovirtnode.ovirtfunctions import OVIRT_VARS
from pipes import quote
import logging
import os
import ovirtnode.ovirtfunctions as _functions
import subprocess
import tempfile

logger = logging.getLogger(__name__)


class Network:
    def __init__(self):
        OVIRT_VARS = _functions.parse_defaults()
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
        from ovirt.node.config.defaults import Network
        return Network().commit()


def convert_to_biosdevname():
    if not "BIOSDEVNAMES_CONVERSION" in OVIRT_VARS:
        # check for appropriate bios version
        cmd="dmidecode|grep SMBIOS|awk {'print $2'}"
        proc = _functions.passthrough(cmd, log_func=logger.debug)
        ver = proc.stdout.split()[0]
        if not float(ver) >= 2.6:
            logger.debug("Skipping biosdevname conversion, SMBIOS too old")
            _functions.augtool("set", "/files/etc/default/ovirt/BIOSDEVNAMES_CONVERSION", "y")
            return
        nics = {}
        cmd = "biosdevname -d"
        biosdevname, err = subprocess.Popen(cmd, shell=True,
                                          stdout=subprocess.PIPE).communicate()
        biosdevname_output = biosdevname.splitlines()

        for line in biosdevname_output:
            if line is not None:
                if "BIOS device:" in line:
                    nic = line.split()[2]
                if "Permanent" in line:
                    mac = line.split()[2]
                    nics[mac.upper()] = nic
        logger.debug(nics)
        scripts_path = "/etc/sysconfig/network-scripts"
        logger.debug(glob(scripts_path + "/ifcfg-*"))
        for file in glob(scripts_path + "/ifcfg-*"):
            logger.debug("Processing %s" % file)
            # get mac for matching
            existing_mac = _functions.augtool_get("/files/" + file + "/HWADDR")
            # check dictionary for mac
            if not existing_mac is None and existing_mac.upper() in nics:
                old_nic_script = os.path.basename(file)
                new_nic_name = nics[existing_mac.upper()]
                logger.debug("Found %s in %s" % (existing_mac, file))
                # change device name within script file
                logger.debug("Setting to new device name: %s" % new_nic_name)
                _functions.augtool("set", \
                                   "/files" + file + "/DEVICE", new_nic_name)
                new_nic_file = "%s/ifcfg-%s" % (scripts_path, new_nic_name)
                cmd = "cp %s %s" % (file, new_nic_file)
                _functions.remove_config(file)
                if _functions.system(cmd):
                    logging.debug("Conversion on %s to %s succeed" % (file,
                                  new_nic_file))
                    _functions.ovirt_store_config(new_nic_file)
                else:
                    return False
        _functions.system("service network restart")
        _functions.augtool("set", \
                       "/files/etc/default/ovirt/BIOSDEVNAMES_CONVERSION", "y")
        _functions.ovirt_store_config("/etc/default/ovirt")
    return True


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
