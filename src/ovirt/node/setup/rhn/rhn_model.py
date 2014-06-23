#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# rhn_model.py - Copyright (C) 2013 Red Hat, Inc.
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
from ovirt.node import utils
from ovirt.node.config.defaults import NodeConfigFileSection
from ovirt.node.utils import process
from ovirt.node.utils.fs import Config
from ovirtnode.ovirtfunctions import unmount_config
from urlparse import urlparse
import sys
import os.path
import glob
import subprocess


RHN_XMLRPC_ADDR = "https://xmlrpc.rhn.redhat.com/XMLRPC"
RHN_SSL_CERT = "/usr/share/rhn/RHNS-CA-CERT"


def parse_host_port(url):
    if url.count('://') == 1:
        (proto, url) = url.split('://')
    else:
        proto = ''
    if url.count(':') == 1:
        (url, port) = url.split(':')
        try:
            port = int(port)
        except:
            port = 0
    elif proto == 'http':
        port = 80
    elif proto == 'https':
        port = 443
    else:
        port = 0
    host = url.split('/')[0]
    return (host, port)


class RHN(NodeConfigFileSection):
    """Configure RHN

    >>> from ovirt.node.utils import fs
    >>> n = RHN(fs.FakeFs.File("dst"))
    """
    keys = ("OVIRT_RHN_TYPE",
            "OVIRT_RHN_URL",
            "OVIRT_RHN_CA_CERT",
            "OVIRT_RHN_USERNAME",
            "OVIRT_RHN_PROFILE",
            "OVIRT_RHN_ACTIVATIONKEY",
            "OVIRT_RHN_ORG",
            "OVIRT_RHN_PROXY",
            "OVIRT_RHN_PROXYUSER")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, rhntype, url, ca_cert, username, profile,
               activationkey, org, proxy, proxyuser):
        pass

    def retrieve(self):
        cfg = dict(NodeConfigFileSection.retrieve(self))
        return cfg

    def retrieveCert(self, url, dest):
        try:
            cmd = ["wget", "-nd", "--no-check-certificate", "--timeout=30",
                   "--tries=3", "-O", dest, url]
            subprocess.check_call(cmd)
        except:
            raise RuntimeError("Error Downloading SSL Certificate!")

    def transaction(self, password, proxypass=None):

        class ConfigureRHNClassic(utils.Transaction.Element):
            state = ("RHN" if RHN().retrieve()["rhntype"] == "rhn"
                     else "Satellite")
            title = "Configuring %s" % state

            def commit(self):
                cfg = RHN().retrieve()
                self.logger.debug(cfg)
                rhntype = cfg["rhntype"]
                serverurl = cfg["url"]
                cacert = cfg["ca_cert"]
                activationkey = cfg["activationkey"]
                username = cfg["username"]
                profilename = cfg["profile"]
                proxy = cfg["proxy"]
                proxyuser = cfg["proxyuser"]

                # novirtinfo: rhn-virtualization daemon refreshes virtinfo
                extra_args = ['--novirtinfo', '--norhnsd', '--nopackages',
                              '--force']
                args = ['/usr/sbin/rhnreg_ks']
                if rhntype == "rhn":
                    sys.path.append("/usr/share/rhn/up2date_client")
                    import rhnreg
                    rhnreg.cfg.set("serverURL", RHN_XMLRPC_ADDR)
                    rhnreg.cfg.set("sslCACert", RHN_SSL_CERT)
                    rhnreg.cfg.save()
                    self.logger.info("ran update")
                if serverurl:
                    cacert = cacert if cacert is not None else serverurl + \
                        "/pub/RHN-ORG-TRUSTED-SSL-CERT"
                    if not serverurl.endswith("/XMLRPC"):
                        serverurl = serverurl + "/XMLRPC"
                    args.append('--serverUrl')
                    args.append(serverurl)
                    location = "/etc/sysconfig/rhn/%s" % \
                               os.path.basename(cacert)
                    if cacert:
                        if not os.path.exists(cacert):
                            self.logger.info("Downloading CA cert.....")
                            self.logger.debug("From: %s To: %s" %
                                              (cacert, location))
                            RHN().retrieveCert(cacert, location)
                        if os.path.isfile(location):
                            if os.stat(location).st_size > 0:
                                args.append('--sslCACert')
                                args.append(location)
                                Config().persist(location)
                            else:
                                raise RuntimeError("Error Downloading \
                                                   CA cert!")
                if activationkey:
                    args.append('--activationkey')
                    args.append(activationkey)
                elif username:
                    args.append('--username')
                    args.append(username)
                    if password:
                        args.append('--password')
                        args.append(password)
                else:
                    # skip RHN registration when neither activationkey
                    # nor username/password is supplied
                    self.logger.debug("No activationkey or "
                                      "username+password given")
                    return

                if profilename:
                    args.append('--profilename')
                    args.append(profilename)

                if proxy:
                    args.append('--proxy')
                    args.append(proxy)
                    if proxyuser:
                        args.append('--proxyUser')
                        args.append(proxyuser)
                        if proxypass:
                            args.append('--proxyPassword')
                            args.append(proxypass)
                args.extend(extra_args)

                self.logger.info("Registering to RHN account.....")
                conf = Config()
                conf.unpersist("/etc/sysconfig/rhn/systemid")
                conf.unpersist("/etc/sysconfig/rhn/up2date")
                logged_args = list(args)
                remove_values_from_args = ["--password", "--proxyPassword"]
                for idx, arg in enumerate(logged_args):
                    if arg in remove_values_from_args:
                        logged_args[idx+1] = "XXXXXXX"
                logged_args = str(logged_args)
                self.logger.debug(logged_args)
                try:
                    subprocess.check_call(args)
                    conf.persist("/etc/sysconfig/rhn/up2date")
                    conf.persist("/etc/sysconfig/rhn/systemid")
                    self.logger.info("System %s sucessfully registered to %s" %
                                     (profilename, serverurl))
                    # sync profile if reregistering, fixes problem with
                    # virt guests not showing
                    sys.path.append("/usr/share/rhn")
                    from virtualization import support
                    support.refresh(True)
                except:
                    self.logger.exception("Failed to call: %s" % logged_args)
                    raise RuntimeError("Error registering to RHN account")

        class ConfigureSAM(utils.Transaction.Element):
            title = "Configuring SAM"

            def commit(self):
                cfg = RHN().retrieve()
                self.logger.debug(cfg)
                # rhntype = cfg["rhntype"]
                org = cfg["org"]
                serverurl = cfg["url"]
                cacert = cfg["ca_cert"]
                activationkey = cfg["activationkey"]
                username = cfg["username"]
                profilename = cfg["profile"]
                proxy = cfg["proxy"]
                proxyuser = cfg["proxyuser"]
                conf = Config()
                if os.path.exists("/etc/sysconfig/rhn/systemid"):
                    conf.unpersist("/etc/sysconfig/rhn/systemid")

                extra_args = ['--force']
                if not activationkey:
                    extra_args.append("--autosubscribe")
                sm = ['/usr/sbin/subscription-manager']

                args = list(sm)
                args.append('register')
                if activationkey and org:
                    args.append('--activationkey')
                    args.append(activationkey)
                    args.append('--org')
                    args.append(org)
                elif username:
                    args.append('--username')
                    args.append(username)
                    if password:
                        args.append('--password')
                        args.append(password)
                else:
                    # skip RHN registration when neither activationkey
                    # nor username/password is supplied
                    # return success for AUTO w/o rhn_* parameters
                    return

                if serverurl:
                    (host, port) = parse_host_port(serverurl)
                    parsed_url = urlparse(serverurl)
                    prefix = parsed_url.path
                    if port == 0:
                        port = "443"
                    else:
                        port = str(port)
                else:
                    prefix = "/subscription"
                    host = "subscription.rhn.redhat.com"
                    port = "443"
                location = "/etc/rhsm/ca/candlepin-local.pem"
                if cacert:
                    if not os.path.exists(cacert):
                        self.logger.info("Downloading CA cert.....")
                        RHN().retrieveCert(cacert, location)
                    if os.path.isfile(location):
                        if os.stat(location).st_size > 0:
                            conf.persist(location)
                        else:
                            raise RuntimeError("Error Downloading CA cert!")

                smconf = list(sm)
                smconf.append('config')
                smconf.append('--server.hostname')
                smconf.append(host)
                smconf.append('--server.port')
                smconf.append(port)
                smconf.append('--server.prefix')
                smconf.append(prefix)

                if cacert:
                    smconf.append('--rhsm.repo_ca_cert')
                    smconf.append('/etc/rhsm/ca/candlepin-local.pem')
                try:
                    subprocess.check_call(smconf)
                    conf.persist("/etc/rhsm/rhsm.conf")
                except:
                    raise RuntimeError("Error updating subscription manager \
                                       configuration")
                if profilename:
                    args.append('--name')
                    args.append(profilename)

                if proxy:
                    try:
                        args.append('--proxy')
                        args.append(proxy)
                        if proxyuser:
                            args.append('--proxyuser')
                            args.append(proxyuser)
                            cmd = ["subscription-manager", "config",
                                   "--server.proxy_user", proxyuser]
                            process.check_call(cmd)
                        if proxypass:
                            args.append('--proxypassword')
                            args.append(proxypass)
                            cmd = ["subscription-manager", "config",
                                   "--server.proxy_password", proxypass]
                            logged_args = list(cmd)
                            remove_values_from_args = [
                                "--server.proxy_password"]
                            for idx, arg in enumerate(cmd):
                                if arg in remove_values_from_args:
                                    logged_args[idx+1] = "XXXXXXX"
                                    logged_args = str(logged_args)
                            self.logger.info(logged_args)
                            subprocess.check_call(cmd)
                    except:
                        raise RuntimeError("Error updating subscription \
                                           manager proxy configuration")
                args.extend(extra_args)

                self.logger.info("Registering to RHN account.....")

                rhsm_configs = (["/var/lib/rhsm/cache/installed_products.json",
                                 "/var/lib/rhsm/facts/facts.json"])
                unmount_config(rhsm_configs)
                unmount_config(glob.glob("/etc/pki/consumer/*pem"))

                def unlink_if_exists(f):
                    if os.path.exists(f):
                        os.unlink(f)
                for f in rhsm_configs:
                    unlink_if_exists(f)

                logged_args = list(args)
                remove_values_from_args = ["--password", "--proxypassword"]
                for idx, arg in enumerate(logged_args):
                    if arg in remove_values_from_args:
                        logged_args[idx+1] = "XXXXXXX"
                logged_args = str(logged_args)
                self.logger.info(logged_args)

                smreg_output = process.pipe(args)
                self.logger.debug(smreg_output)
                if "been registered" not in smreg_output:
                    if "Invalid credentials" in smreg_output:
                        raise RuntimeError("Invalid Username / Password")
                    elif "already been taken" in smreg_output:
                        raise RuntimeError("Hostname is already " +
                                           "registered")
                    else:
                        raise RuntimeError("Registration Failed")
                else:
                    conf.persist(rhsm_configs)
                    conf.persist("/etc/pki/consumer/key.pem")
                    conf.persist("/etc/pki/consumer/cert.pem")
                    self.logger.info("System %s sucessfully registered \
                                      to %s" % (profilename, serverurl))

        cfg = self.retrieve()
        self.logger.debug(cfg)
        rhntype = cfg["rhntype"]
        tx = utils.Transaction("Performing RHN Registration")

        if rhntype == "sam":
            tx.append(ConfigureSAM())
        else:
            tx.append(ConfigureRHNClassic())
        return tx
