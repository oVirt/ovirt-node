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
from ovirt.node.utils import process, system
from ovirt.node.utils.fs import Config
from urlparse import urlparse
import sys
import os.path
import glob
import subprocess
import urllib


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
        for x in range(0, 3):
            try:
                # urllib doesn't check ssl certs, so we're ok here
                urllib.urlretrieve(url, dest)
                return
            except IOError:
                self.logger.debug(
                    "Failed to download {url} on try {x}".format(
                        url=url, x=x))

        # If we're here, we failed to get it
        raise RuntimeError("Error downloading SSL certificate!")

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
                    # find old SAM/Sat 6 registrations
                    if Config().exists("/etc/rhsm/rhsm.conf"):
                        process.call(["subscription-manager",
                                      "remove", "--all"])
                        process.call(["subscription-manager", "clean"])
                        Config().unpersist("/etc/rhsm/rhsm.conf")
                except:
                    self.logger.exception("Failed to call: %s" % logged_args)
                    raise RuntimeError("Error registering to RHN account")

        class ConfigureSAM(utils.Transaction.Element):
            # sam path is used for sat6 as well, making generic
            title = "Registering to Server..."

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

                # Don't autosubscribe for now, since it may cause entitlement
                # problems with SAM and Sat6
                # if not activationkey:
                #     extra_args.append("--autosubscribe")

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
                    if org:
                        args.append('--org')
                        args.append(org)
                else:
                    # skip RHN registration when neither activationkey
                    # nor username/password is supplied
                    # return success for AUTO w/o rhn_* parameters
                    return

                if serverurl:
                    (host, port) = parse_host_port(serverurl)
                    parsed_url = urlparse(serverurl)
                    prefix = parsed_url.path
                    if cacert.endswith(".pem") and rhntype == "satellite":
                        prefix = "/rhsm"
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
                if cacert and not cacert.endswith(".pem") or \
                   rhntype == "satellite":
                    smconf.append('--server.prefix')
                    smconf.append(prefix)
                else:
                    smconf.append('--rhsm.baseurl')
                    if prefix:
                        smconf.append("%s/%s" % (host, prefix))
                    else:
                        smconf.append(host + '/pulp/repos')
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
                [Config().unpersist(f) for f in rhsm_configs]
                [Config().unpersist(f) for f in
                 glob.glob("/etc/pki/consumer/*pem")]

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

                # This may block if waiting for input with check_output.
                # pipe doesn't block
                smreg_output = process.pipe(args)
                if "been registered" not in smreg_output:
                    if "Invalid credentials" in smreg_output:
                        raise RuntimeError("Invalid Username / Password")
                    elif "already been taken" in smreg_output:
                        raise RuntimeError("Hostname is already " +
                                           "registered")

                    if "Organization" in smreg_output:
                        raise RuntimeError("Organization must be specified "
                                           "with Satellite 6")

                    if activationkey:
                        cmd = ["subscription-manager", "auto-attach"]
                        try:
                            subprocess.check_call(cmd)
                        except:
                            raise RuntimeError("Error Setting Auto Attach")
                    else:
                        raise RuntimeError("Registration Failed")
                else:
                    for cfg in rhsm_configs:
                        conf.persist(cfg)
                    conf.persist("/etc/pki/consumer/key.pem")
                    conf.persist("/etc/pki/consumer/cert.pem")
                    self.logger.info("System %s sucessfully registered \
                                      to %s" % (profilename, serverurl))

        cfg = self.retrieve()
        self.logger.debug(cfg)
        rhntype = cfg["rhntype"]
        cacert = cfg["ca_cert"] or ""
        _rhn_brand = "RHSM" if system.is_min_el(7) else "RHN"
        tx = utils.Transaction("Performing %s Registration" % _rhn_brand)

        if rhntype == "sam" or cacert.endswith(".pem"):
            tx.append(ConfigureSAM())
        elif system.is_min_el(7) and rhntype == "rhn":
            tx.append(ConfigureSAM())
        else:
            tx.append(ConfigureRHNClassic())
        return tx
