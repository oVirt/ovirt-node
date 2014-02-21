#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# progress_page.py - Copyright (C) 2013 Red Hat, Inc.
# Written by Ryan Barry <rbarry@redhat.com>
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
from ovirt.node import base
from ovirt.node.utils import AugeasWrapper, network, parse_bool
from ovirt.node.utils.fs import Config
from ovirtnode import iscsi, log, ovirtfunctions
import os


class MigrateConfigs(base.Base):

    def __init__(self):
        self.aug = AugeasWrapper()
        super(MigrateConfigs, self).__init__()

    def translate_all(self, do_network=True):
        if do_network:
            self.migrate_network_layout()

        [getattr(self, func)() for func in dir(self) if
            func.startswith("translate_") and not
            func.endswith("all")]

    def translate_rsyslog(self):
        if self.__is_persisted("/etc/rsyslog.conf"):
            rsyslog_server, rsyslog_port = log.get_rsyslog_config() if \
                log.get_rsyslog_config() is not None else (None, 514)
            if rsyslog_server:
                self.aug.set("/files/etc/default/ovirt/OVIRT_SYSLOG_SERVER",
                             rsyslog_server or "")
                self.aug.set("/files/etc/default/ovirt/OVIRT_SYSLOG_PORT",
                             rsyslog_port or "")

    def translate_netconsole(self):
        if self.__is_persisted("/etc/sysconfig/netconsole"):
            netconsole_server = ovirtfunctions.augtool_get(
                "/files/etc/sysconfig/netconsole/SYSLOGADDR")
            netconsole_port = ovirtfunctions.augtool_get(
                "/files/etc/sysconfig/netconsole/SYSLOGPORT")
            if netconsole_server:
                self.aug.set(
                    "/files/etc/default/ovirt/OVIRT_NETCONSOLE_SERVER",
                    netconsole_server or "")
                self.aug.set("/files/etc/default/ovirt/OVIRT_NETCONSOLE_PORT",
                             str(netconsole_port) or "")

    def translate_logrotate(self):
        if self.__is_persisted("/etc/logrotate.d/ovirt-node"):
            logrotate_size = ovirtfunctions.get_logrotate_size()
            if logrotate_size is not 1024:
                self.aug.set(
                    "/files/etc/default/ovirt/OVIRT_LOGROTATE_MAX_SIZE",
                    str(logrotate_size) or "")

    def translate_ssh(self):
        if self.__is_persisted("/etc/ssh/sshd_config"):
            pw_auth_enabled = ovirtfunctions.augtool_get(
                "/files/etc/ssh/sshd_config/PasswordAuthentication")
            rng_bytes, aes_enabled = ovirtfunctions.rng_status()

            rng_bytes = None if rng_bytes == 0 else rng_bytes
            aes_disabled = False if aes_enabled == "1" else True
            ssh_is_enabled = parse_bool(pw_auth_enabled)

            if rng_bytes:
                self.aug.set("/files/etc/default/ovirt/OVIRT_USE_STRONG_RNG",
                             str(rng_bytes))
            if aes_disabled:
                self.aug.set("/files/etc/default/ovirt/OVIRT_DISABLE_AES_NI",
                             "true")
            if ssh_is_enabled:
                self.aug.set("/files/etc/default/ovirt/OVIRT_SSH_PWAUTH",
                             "yes")

    def translate_network_servers(self):
        dns = [ovirtfunctions.augtool_get(
               "/files/etc/resolv.conf/nameserver[1]"),
               ovirtfunctions.augtool_get(
                   "/files/etc/resolv.conf/nameserver[2]")]
        self.aug.set("/files/etc/default/ovirt/OVIRT_DNS",
                     ",".join((filter(None, dns))))

        ntp = [ovirtfunctions.augtool_get(
               "/files/etc/ntp.conf/server[1]"),
               ovirtfunctions.augtool_get(
                   "/files/etc/ntp.conf/server[2]")]
        self.aug.set("/files/etc/default/ovirt/OVIRT_NTP",
                     ",".join((filter(None, ntp))))

        self.aug.set("/files/etc/default/ovirt/OVIRT_HOSTNAME",
                     os.uname()[1])

    def translate_kdump(self):
        if self.__is_persisted("/etc/kdump.conf"):
            kdump = self._get_kdump_config()
            if "nfs" in kdump:
                self.aug.set("/files/etc/default/ovirt/OVIRT_KDUMP_NFS",
                             kdump["nfs"])
            elif "ssh" in kdump:
                self.aug.set("/files/etc/default/ovirt/OVIRT_KDUMP_SSH",
                             kdump["ssh"])
            else:
                self.aug.set("/files/etc/default/ovirt/OVIRT_KDUMP_LOCAL",
                             "true")

    def translate_snmp(self):
        if self.__is_persisted("/etc/snmp/snmpd.conf"):
            self.aug.set("/files/etc/default/ovirt/OVIRT_SNMP_ENABLED",
                         "1")

    def translate_iscsi(self):
        if self.__is_persisted("/etc/iscsi/initiatorname.iscsi"):
            iscsi_initiator = iscsi.get_current_iscsi_initiator_name()
            if iscsi_initiator:
                self.aug.set("/files/etc/default/ovirt/OVIRT_ISCSI_NODE_NAME",
                             iscsi_initiator or "")

    def translate_nfs(self):
        if self.__is_persisted("/etc/idmapd.conf"):
            nfsv4_domain = self._get_current_nfsv4_domain()
            if nfsv4_domain:
                self.aug.set("/files/etc/default/ovirt/OVIRT_NFSV4_DOMAIN",
                             nfsv4_domain or "")

    def translate_rhn(self):
        try:
            self._translate_rhn()
        except:
            self.logger.debug("RHN plugin not available")

    def _translate_rhn(self):
        from ovirt.node.setup.rhn import rhn_page as rhn
        if self.__is_persisted("/etc/sysconfig/rhn/up2date") or \
                self.__is_persisted("/etc/rhsm/rhsm.conf"):

            rhn_type = None
            rhn_url = None
            rhn_ca = None
            rhn_username = None
            rhn_profile = None
            rhn_activationkey = None
            rhn_org = None
            rhn_proxyurl = None
            rhn_proxyuser = None

            rhn_conf = rhn.get_rhn_config()
            status, rhn_type = rhn.get_rhn_status()

            RHN_XMLRPC_ADDR = "https://xmlrpc.rhn.redhat.com/XMLRPC"
            SAM_REG_ADDR = "subscription.rhn.redhat.com"
            CANDLEPIN_CERT_FILE = "/etc/rhsm/ca/candlepin-local.pem"

            if not RHN_XMLRPC_ADDR in rhn_conf["serverURL"] and not \
                    rhn.sam_check():
                rhn_url = rhn_conf["serverURL"]
                rhn_ca = rhn_conf["sslCACert"]
            elif rhn.sam_check():
                if not SAM_REG_ADDR in rhn_conf["hostname"]:
                    rhn_url = "https://%s" % rhn_conf["hostname"]
                    if os.path.exists(CANDLEPIN_CERT_FILE):
                        rhn_ca = CANDLEPIN_CERT_FILE
            if "proxyUser" in rhn_conf and "proxyPassword" in rhn_conf:
                if len(rhn_conf["proxyUser"]) > 0:
                    rhn_proxyuser = rhn_conf["proxyUser"]
            elif "proxy_user" in rhn_conf and "proxy_password" in rhn_conf:
                rhn_proxyuser = rhn_conf["proxy_user"]

            if rhn_conf["httpProxy"] is not None:
                try:
                    proxy_hostname, proxy_port = rhn_conf[
                        "httpProxy"].split(':')
                    rhn_proxyurl = "%s:%s" % (proxy_hostname, proxy_port)
                except ValueError:
                    self.logger.debug("Bad proxy entry in old install %s" %
                                      rhn_conf["httpProxy"])

                    if rhn_conf["proxy_hostname"] is not None and rhn_conf[
                            "proxy_port"] is not None:
                        rhn_proxyurl = "%s:%s" % (rhn_conf["proxy_hostname"],
                                                  rhn_conf["proxy_port"])

            self.aug.set("/files/etc/default/ovirt/OVIRT_RHN_TYPE",
                         rhn_type.lower() if rhn_type else "")
            self.aug.set("/files/etc/default/ovirt/OVIRT_RHN_URL",
                         rhn_url or "")
            self.aug.set("/files/etc/default/ovirt/OVIRT_RHN_CA_CERT",
                         rhn_ca or "")
            self.aug.set("/files/etc/default/ovirt/OVIRT_RHN_USERNAME",
                         rhn_username or "")
            self.aug.set("/files/etc/default/ovirt/OVIRT_RHN_PROFILE",
                         rhn_profile or "")
            self.aug.set("/files/etc/default/ovirt/OVIRT_RHN_ACTIVATIONKEY",
                         rhn_activationkey or "")
            self.aug.set("/files/etc/default/ovirt/OVIRT_RHN_ORG",
                         rhn_org or "")
            self.aug.set("/files/etc/default/ovirt/OVIRT_RHN_PROXY",
                         rhn_proxyurl or "")
            self.aug.set("/files/etc/default/ovirt/OVIRT_RHN_PROXYUSER",
                         rhn_proxyuser or "")

    def _get_kdump_config(self):
        kdump_type = {}
        try:
            kdump_config_file = open("/etc/kdump.conf")
            for line in kdump_config_file:
                if not line.startswith("#"):
                    if line.startswith("net"):
                        line = line.replace("net ", "")
                        if "@" in line:
                            kdump_type = {"ssh": line.strip()}
                        elif ":" in line:
                            kdump_type = {"nfs": line.strip()}
                    elif "/dev/HostVG/Data" in line:
                        kdump_type = {"local": None}
            kdump_config_file.close()
        except:
            pass

        return kdump_type

    def _get_current_nfsv4_domain(self):
        domain = None
        with open("/etc/idmapd.conf") as nfs_config:
            for line in nfs_config:
                if "Domain =" in line:
                    domain = line.replace("Domain =", "").strip()
                    break
        return domain

    def __is_persisted(self, path):
        return Config().exists(path)

    def migrate_network_layout(self):
        bridges = [x for x in network.Bridges().ifnames() if
                   x.startswith("br")]
        bridged_nics = [x for x in network.all_ifaces() if
                        network.NIC(x).config.bridge in bridges]

        self.logger.debug("Found bridges: %s" % bridges)
        self.logger.debug("Found bridged NICs: %s" % bridged_nics)

        def cfgset(k, v, prefix="OVIRT_"):
            if v:
                self.logger.debug("  Setting %s = %s" % (k, v))
                self.aug.set("/files/etc/default/ovirt/%s%s" % (prefix, k),
                             str(v))

        found_mgmt = False
        for brn in ["rhevm", "ovirtmgmt"]:
            if brn in network.Bridges().ifnames():
                self.logger.debug("Found managed nic: %s" % brn)
                cfgset("MANAGED_BY", "RHEV-M", "")
                cfgset("MANAGED_IFNAMES", brn, "")
                found_mgmt = True
                break

        self.logger.debug("Found management: %s" % found_mgmt)

        if not found_mgmt and bridges and bridged_nics:
            self.logger.debug("Assuming default bridged network")

            self.aug.set("/files/etc/default/ovirt/OVIRT_NETWORK_LAYOUT",
                         "bridged")

            ifname = bridged_nics[0]
            br = bridges[0]
            vlanid = None

            self.logger.debug("Bridge and NIC: %s %s" % (br, ifname))

            probably_vlan = "." in ifname
            if probably_vlan:
                ifname, vlanid = ifname.split(".", 1)
                self.logger.debug("Found VLAN setup, base NIC: %s %s" %
                                  (ifname, vlanid))

            self.aug.set("/files/etc/default/ovirt/OVIRT_BOOTIF",
                         ifname)

            def ifcfg(i, k):
                v = self.aug.get("/files/etc/sysconfig/network-" +
                                 "scripts/ifcfg-%s/%s" % (i, k))
                self.logger.debug("  Getting %s.%s = %s" % (i, k, v))
                return v

            proto = ifcfg(br, "BOOTPROTO")
            cfgset("BOOTPROTO", proto)

            addr = ifcfg(br, "IPADDR")
            if addr:
                cfgset("IP_ADDRESS", addr)
                cfgset("IP_GATEWAY", ifcfg(br, "GATEWAY"))
                cfgset("IP_NETMASK", ifcfg(br, "NETMASK"))

            if vlanid:
                cfgset("VLAN", vlanid)
