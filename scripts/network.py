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
from ovirtnode.ovirtfunctions import *
import tempfile
import sys

class Network:

    def __init__(self):
        OVIRT_VARS = parse_defaults()
        self.WORKDIR=tempfile.mkdtemp()
        self.IFCONFIG_FILE_ROOT="/files/etc/sysconfig/network-scripts/ifcfg"
        self.NTPCONF_FILE_ROOT="/files/etc/ntp"
        self.NTP_CONFIG_FILE="/etc/ntp.conf"
        self.NTPSERVERS=""
        self.CONFIGURED_NIC= ""
        self.IF_CONFIG = ""
        self.BR_CONFIG = ""
        self.VL_CONFIG = ""
        self.VLAN_ID=""
        self.VL_ROOT=""
        self.VL_FILENAME =""
        self.nic=""
        self.bridge=""
        self.vlan_id=""

    def configure_interface(self):
        log("Configuring Interface")
        if OVIRT_VARS.has_key("OVIRT_IP_ADDRESS"):
            IPADDR = OVIRT_VARS["OVIRT_IP_ADDRESS"]
            NETMASK = OVIRT_VARS["OVIRT_IP_NETMASK"]
            GATEWAY = OVIRT_VARS["OVIRT_IP_GATEWAY"]

        if OVIRT_VARS.has_key("OVIRT_BOOTIF"):
            self.CONFIGURED_NIC = OVIRT_VARS["OVIRT_BOOTIF"]
        if not self.CONFIGURED_NIC is None:
            log("\nDeleting existing network configuration...\n")
            os.system("cp -a  /etc/sysconfig/network-scripts/ifcfg-lo /etc/sysconfig/network-scripts/backup.lo")
            for file in os.listdir("/etc/sysconfig/network-scripts/"):
                if "ifcfg-" in file:
                    remove_config("/etc/sysconfig/network-scripts/" + file)
            os.system("rm -rf /etc/sysconfig/network-scripts/ifcfg-* &>/dev/null")
            os.system("cp -a  /etc/sysconfig/network-scripts/backup.lo /etc/sysconfig/network-scripts/ifcfg-lo")
        else:
            log("\nAborting...\n")
            return False

        for file in os.listdir(self.WORKDIR):
            os.system("rm -rf %s/%s") % (self.WORKDIR, file)
        n_address = open("/sys/class/net/" + self.CONFIGURED_NIC + "/address")
        nic_hwaddr = n_address.readline().strip("\n")
        n_address.close()
        BRIDGE = "br" + self.CONFIGURED_NIC
        IF_FILENAME = self.WORKDIR + "/augtool-" + self.CONFIGURED_NIC
        BR_FILENAME = self.WORKDIR + "/augtool-" + BRIDGE
        log("\nConfigure $BRIDGE for use by $NIC..\n\n")
        IF_ROOT = "%s-%s" % (self.IFCONFIG_FILE_ROOT, self.CONFIGURED_NIC)
        self.IF_CONFIG += "rm %s\nset %s/DEVICE %s\n" % (IF_ROOT, IF_ROOT, self.CONFIGURED_NIC)
        self.IF_CONFIG += "set %s/HWADDR %s\n" % (IF_ROOT, nic_hwaddr)
        BR_ROOT = "%s-%s" % (self.IFCONFIG_FILE_ROOT, BRIDGE)
        self.BR_CONFIG += "rm %s\nset %s/DEVICE %s\n" % (BR_ROOT, BR_ROOT, BRIDGE)
        self.BR_CONFIG += "set %s/TYPE Bridge\n" % BR_ROOT
        self.BR_CONFIG += "set %s/PEERNTP yes\n" % BR_ROOT
        self.BR_CONFIG += "set %s/DELAY 0\n" % BR_ROOT

        if OVIRT_VARS.has_key("OVIRT_IPV6"):
            if OVIRT_VARS["OVIRT_IPV6"]  == "auto":
                self.BR_CONFIG += "set %s/IPV6INIT yes\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6FORWARDING no\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6_AUTOCONF yes\n" % BR_ROOT
            elif OVIRT_VARS["OVIRT_IPV6"] == "dhcp":
                self.BR_CONFIG += "set %s/IPV6INIT yes\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6_AUTOCONF no\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6FORWARDING no\n" % BR_ROOT
                self.BR_CONFIG += "set %s/DHCPV6C yes\n" % BR_ROOT
            else:
                self.BR_CONFIG += "set %s/IPV6INIT yes\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6ADDR %s\n" % (BR_ROOT, OVIRT_VARS["OVIRT_IPV6_ADDRESS"])
                self.BR_CONFIG += "set %s/IPV6_AUTOCONF no\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6FORWARDING no\n" % BR_ROOT

        if OVIRT_VARS.has_key("OVIRT_VLAN"):
            VLAN_ID=OVIRT_VARS["OVIRT_VLAN"]
            VL_ROOT = "%s.%s" % (IF_ROOT, VLAN_ID)
            self.VL_CONFIG += "rm %s\n" % VL_ROOT
            self.VL_CONFIG += "set %s/DEVICE %s.%s\n" % (VL_ROOT, self.CONFIGURED_NIC, VLAN_ID)
            self.VL_CONFIG += "set %s/HWADDR %s\n" % (VL_ROOT, nic_hwaddr)
            self.VL_CONFIG += "set %s/BRIDGE %s\n" % (VL_ROOT, BRIDGE)
            self.VL_CONFIG += "set %s/VLAN yes\n" % VL_ROOT
            self.VL_FILENAME = "%s.%s" % (IF_FILENAME, OVIRT_VARS["OVIRT_VLAN"])
            self.VL_CONFIG +="set %s/ONBOOT yes" % VL_ROOT


        if not OVIRT_VARS.has_key("OVIRT_IP_ADDRESS"):
	    if not self.VL_CONFIG:
	        self.IF_CONFIG += "set %s/BRIDGE %s\n" % (IF_ROOT, BRIDGE)
            self.BR_CONFIG += "set %s/BOOTPROTO dhcp\n" % BR_ROOT
        else:
            if OVIRT_VARS.has_key("OVIRT_IP_ADDRESS") and OVIRT_VARS["OVIRT_IP_ADDRESS"] != "off":
		if self.VL_CONFIG == "":
                    self.IF_CONFIG += "set %s/BRIDGE %s\n" % (IF_ROOT, BRIDGE)
                self.BR_CONFIG += "set %s/IPADDR %s\n" % (BR_ROOT, OVIRT_VARS["OVIRT_IP_ADDRESS"])
                if OVIRT_VARS.has_key("OVIRT_IP_NETMASK"):
                    self.BR_CONFIG += "set %s/NETMASK %s\n" % (BR_ROOT, OVIRT_VARS["OVIRT_IP_NETMASK"])
                if OVIRT_VARS.has_key("OVIRT_IP_GATEWAY"):
                    self.BR_CONFIG += "set %s/GATEWAY %s\n" % (BR_ROOT, OVIRT_VARS["OVIRT_IP_GATEWAY"])
        self.IF_CONFIG += "set %s/ONBOOT yes" % IF_ROOT
        self.BR_CONFIG += "set %s/ONBOOT yes" % BR_ROOT
        self.IF_CONFIG = self.IF_CONFIG.split("\n")
        self.BR_CONFIG = self.BR_CONFIG.split("\n")
        try:
            self.VL_CONFIG = self_VL_CONFIG.split("\n")
        except:
            pass
        log("VL_CONFIG: " + self.VL_CONFIG)
        return True

    def configure_dns(self):
        if OVIRT_VARS.has_key("OVIRT_DNS"):
            DNS=OVIRT_VARS["OVIRT_DNS"]
            if not DNS is None:
                try:
                    DNS1, DNS2 = DNS.split(" ", 1)
                    if not DNS1 is None:
                        augtool("set", "/files/etc/resolv.conf/nameserver[1]", DNS1)
                    if not DNS2 is None:
                        augtool("set", "/files/etc/resolv.conf/nameserver[2]", DNS2)
                except:
                    log("Failed to set DNS servers")

    def configure_ntp(self):
        if OVIRT_VARS.has_key("OVIRT_NTP"):
            NTPSERVERS=OVIRT_VARS["OVIRT_NTP"]
        else:
            NTPSERVERS=""

    def save_ntp_configuration(self):
        ntproot = "/files/etc/ntp.conf"
        ntpconf = "rm %s\n" % ntproot
        ntpconf += "set %s/driftfile /var/lib/ntp/drift\n" % ntproot
        ntpconf += "set %s/includefile /etc/ntp/crypto/pw\n" % ntproot
        ntpconf += "set %s/keys /etc/ntp/keys" % ntproot
        ntpconf = ntpconf.split("\n")
        for line in ntpconf:
            try:
                oper, file, value = line.split()
            except:
                oper, file = line.split()
            
            augtool(oper, line, "")

        if OVIRT_VARS.has_key("NTPSERVERS"):
            offset=1
            SERVERS = OVIRT_VARS["NTPSERVERS"].split(":")
            for server in SERVERS:
                augtool("set", "/files/etc/ntp.conf/server[%s]", server) % offset
                offset = offset + 1

    def save_network_configuration(self):
        net_configured=0
        augtool_workdir_list = "ls %s/augtool-* >/dev/null"
        log("Configuring network")

#        # delete existing scripts
#        try:
#            for vlan in os.listdir("/proc/net/vlan/"):
#                if "config" in vlan:
#                    os.system("vconfig rem %s &> /dev/null") % vlan
#        except:
#            pass
#
#        for script in os.listdir("/etc/sysconfig/network-scripts/"):
#            if "ifcfg" in script:
#                if not "ifcfg-lo" in script:
#                    ovirt_safe_delete_config(script)

        config = self.WORKDIR + "/config-augtool"
        
        for line in self.IF_CONFIG:
            log(line)
            try:
                oper, file, value = line.split()
                augtool(oper, file, value)
            except:
                oper, file = line.split()
                augtool(oper, line, "")
        for line in self.BR_CONFIG:
            log(line)
            try:
                oper, file, value = line.split()
                augtool(oper, file, value)
            except:
                try:
                    oper, file = line.split()
                    augtool(oper, line, "")
                except:
                    pass

        for line in self.VL_CONFIG.split("\n"):
            log(line)
            try:
                oper, file, value = line.split()
                augtool(oper, file, value)
            except:
                try:
                    oper, file = line.split()
                    augtool(oper, line, "")
                except:
                    pass

        net_configured=1
        for i in os.listdir("/etc/sysconfig/network-scripts/"):
            if "ifcfg" in i:
                ovirt_store_config("/etc/sysconfig/network-scripts/" + i)
        ovirt_store_config(self.NTP_CONFIG_FILE)
        log("Network configured successfully")
        if net_configured == 1:
            log("\nStopping Network service")
            os.system("service network stop &> /dev/null")
            brctl_cmd = "brctl show|grep breth|awk '{print $1}'"
            brctl = subprocess.Popen(brctl_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
            brctl_output = brctl.stdout.read()
            for i in brctl_output.split():
                if_down_cmd = "ifconfig %s down &> /dev/null" % i
                os.system(if_down_cmd)
                del_br_cmd = "brctl delbr %s &> /dev/null" % i
                os.system(del_br_cmd)
            log("\nStarting Network service")
            os.system("service network start &> /dev/null")
            if OVIRT_VARS.has_key("NTP"):
                log("Testing NTP Configuration")
                test_ntp_configuration()


if __name__ == "__main__":
    try:
        if "AUTO" in sys.argv[1]:
            if OVIRT_VARS.has_key("OVIRT_INIT"):
                network = Network()
                network.configure_interface()
                network.configure_dns()
                network.configure_ntp()
                network.save_ntp_configuration()
                network.save_network_configuration()
            else:
                log("No network interface specified. Unable to configure networking.")
    except:
        log("Exiting..")
        sys.exit(0)
