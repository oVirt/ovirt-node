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
from ovirt.node import base, utils
from ovirt.node.config.defaults import NodeConfigFileSection
from ovirt.node.utils import process, system
from ovirt.node.utils.fs import Config
import sys
import re
import os.path
import glob
import requests
import urlparse

DEFAULT_CA_SAT6 = 'katello-server-ca'


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
            "OVIRT_RHN_ENVIRONMENT",
            "OVIRT_RHN_PROXY",
            "OVIRT_RHN_PROXYUSER")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, rhntype, url, ca_cert, username, profile,
               activationkey, org, environment, proxy, proxyuser):
        pass

    def retrieve(self):
        cfg = dict(NodeConfigFileSection.retrieve(self))
        return cfg

    def retrieve_cert(self, url, dest, proxies=None):
        """
        Grab the SSL certificate by trying 3 times (use another method to
        actually do the retrieval). If it doesn't get pulled, raise an
        exception
        """
        success = False

        for x in range(0, 3):
            msg = self._retrieve_url(url, dest, proxies)
            if msg:
                self.logger.info("Failed to retrieve download {url} on "
                                 "try {x}".format(url=url, x=x))
                self.logger.info(msg)
            else:
                # We could return and rely on the falling through to
                # raise the exception, but it's clearer to be explicit
                success = True
                break
        if not success:
            try:
                os.unlink(dest)
            except:
                # Possible that it wasn't downloaded at all, so this is ok
                pass
            raise RuntimeError("Error downloading SSL certificate")

    def _retrieve_url(self, url, dest, proxies):
        """
        Retrieve a file from a URL. Use python-requests so we can be as
        explicit as possible about problems, and it's the most pythonic
        library in stdlib (don't use urllib or urllib2 for this)
        """
        msg = None

        with open(dest, 'w') as f:
            try:
                s = requests.Session()
                r = s.get(url, stream=True, verify=False, proxies=proxies)
                if r.status_code != 200:
                    msg = "Cannot download the file: HTTP error code %s" \
                          % str(r.status_code)
                    os.unlink(dest)
                f.write(r.raw.read())
            except requests.exceptions.ConnectionError as e:
                msg = "Connection Error: %s" % str(e[0])
                os.unlink(dest)
            except:
                import traceback
                msg = "Unexpected error: %s" % str(traceback.format_exc())
            finally:
                return msg

    def parse_host_uri(self, uri):
        ports = {"http": 80,
                 "https": 443}

        # urlparse expects the URI to start with proto://, or else it's
        # a relative path. But only the // separator is required to parse
        # it out correctly. If it's not there, add it. Still safer than
        # re-implementing uri parsing ourselves
        urischeme = re.compile(r'^\w+://')
        uri = uri if urischeme.match(uri) else "//" + uri

        parsed = urlparse.urlparse(uri)
        port = parsed.port or ports[parsed.scheme] if parsed.scheme in ports \
            else None
        return parsed.hostname, port, parsed.path

    def transaction(self, password, proxypass=None):

        cfg = dict(self.retrieve())

        class Vars:
            """
            Hold variables which may be used between classes so we don't need
            to try to fake masking them with arrays or anything
            """
            argbuilder = None
            location = None
            ca_cert = None

        class RaiseError(utils.Transaction.Element):
            title = "Missing a required field"

            def __init__(self, msg):
                self.msg = msg
                super(RaiseError, self).__init__()

            def commit(self):
                raise RuntimeError(self.msg)

        class ConfigureRHNClassic(utils.Transaction.Element):
            title = "Setting up rhnreg config"

            def commit(self):
                # Append the path so we can import rhnreg. Why isn't it
                # also packaged in site-packages? Should ask the maintainer
                sys.path.append("/usr/share/rhn/up2date_client")
                import rhnreg

                rhnreg.cfg.set("serverURL",
                               "https://xmlrpc.rhn.redhat.com/XMLRPC")
                rhnreg.cfg.set("sslCACert",
                               "/usr/share/rhn/RHNS-CA-CERT")
                rhnreg.cfg.save()
                self.logger.debug("Updated rhnreg config using their API")

        class DownloadCertificate(utils.Transaction.Element):
            title = "Checking SSL Certificate"

            def commit(self):
                if not os.path.exists(Vars.location):
                    def build_proxies():
                        if cfg["proxyuser"] and proxypass:
                            proxy_prefix = "%s:%s" % (cfg["proxyuser"],
                                                      proxypass)
                        elif cfg["proxyuser"]:
                            proxy_prefix = "%s" % cfg["proxyuser"]

                        cfg["proxy"] = cfg["proxy"] if ":" in cfg["proxy"] \
                            else cfg["proxy"] + ":3128"

                        proxy_str = "http://%s@%s" % (proxy_prefix,
                                                      cfg["proxy"])

                        proxylist = {"http": proxy_str,
                                     "https": proxy_str,
                                     "ftp": proxy_str
                                     }

                        return proxylist

                    proxies = None

                    if cfg["proxy"]:
                        proxies = build_proxies()

                    self.logger.info("Downloading CA cert from: %s as %s"
                                     % (Vars.ca_cert, Vars.location))
                    RHN().retrieve_cert(Vars.ca_cert, Vars.location, proxies)

                if os.stat(Vars.location).st_size == 0:
                    os.unlink(Vars.location)
                    raise RuntimeError("SSL certificate %s has has zero size, "
                                       "can't use it. Please check the URL" %
                                       Vars.location)
                else:
                    Config().persist(Vars.location)

        class PrepareClassicRegistration(utils.Transaction.Element):
            title = "Preparing for registration"

            def commit(self):
                # If the URL doesn't end with the default path, add it
                cfg["url"] = cfg["url"] if cfg["url"].endswith("/XMLRPC") \
                    else cfg["url"] + "/XMLRPC"

                # If there's no CA cert path specified, assume the default
                Vars.ca_cert = cfg["ca_cert"] if cfg["ca_cert"] else \
                    cfg["url"] + "/pub/RHN-ORG-TRUSTED-SSL-CERT"

                Vars.location = "/etc/sysconfig/rhn/%s" % os.path.basename(
                    cfg["ca_cert"])

                # Why these flags?
                # --novirtinfo: rhn-virtualization daemon refreshes virtinfo
                # --nopackages because it's a ro image and an appliance
                #    can't update them anyway
                # --norhnsd because we don't want to try (and fail) to run
                #    actions on groups from Spacewalk/Satellite
                initial_args = ["/usr/sbin/rhnreg_ks"]
                initial_args.extend(["--novirtinfo", "--norhnsd",
                                     "--nopackages", "--force"])

                mapping = {"--serverUrl":     cfg["url"],
                           "--sslCACert":     "/etc/sysconfig/rhn/%s" %
                           os.path.basename(cfg["ca_cert"]),
                           "--activationkey": cfg["activationkey"],
                           "--username":      cfg["username"],
                           "--password":      password,
                           "--profilename":   cfg["profile"],
                           "--proxy":         cfg["proxy"],
                           "--proxyUser":     cfg["proxyuser"],
                           "--proxyPassword": proxypass
                           }

                Vars.argbuilder = ArgBuilder(initial_args, mapping)

        class RegisterRHNClassic(utils.Transaction.Element):
            state = ("RHN" if RHN().retrieve()["rhntype"] == "rhn"
                     else "Satellite")
            title = "Registering to %s" % state

            def commit(self):
                self.logger.info("Registering to RHN account...")

                # Filter out passwords from the log
                logged_args = Vars.argbuilder.get_commandlist(string=True,
                                                              filtered=True)
                self.logger.debug(logged_args)
                try:
                    process.check_call(Vars.argbuilder.get_commandlist())
                    Config().persist("/etc/sysconfig/rhn/up2date")
                    Config().persist("/etc/sysconfig/rhn/systemid")

                    if cfg["url"]:
                        self.logger.info("System %s successfully registered to"
                                         " %s" % (cfg["profile"], cfg["url"]))
                    else:
                        self.logger.info("System successfully registered to"
                                         "RHN classic")

                except process.CalledProcessError:
                    self.logger.exception("Failed to call: %s" % logged_args)
                    raise RuntimeError("Error registering to RHN account")

        class UpdateGuests(utils.Transaction.Element):
            title = "Refreshing the list of running VMs"

            def commit(self):
                # Syncing the profile resolves a problem with guests not
                # showing
                sys.path.append("/usr/share/rhn")
                from virtualization import support
                support.refresh(True)

        class RemoveConfigs(utils.Transaction.Element):
            title = "Removing old configuration"

            def commit(self):
                def scrub(f):
                    if Config().exists(f):
                        Config().unpersist(f)
                        # Unlinking causes problems with satellite5. Why?
                        # os.unlink(f)
                # find old SAM/Sat 6 registrations
                if Config().exists("/etc/rhsm/rhsm.conf"):
                    try:
                        process.call(["subscription-manager",
                                      "remove", "--all"])
                        process.call(["subscription-manager", "clean"])
                        Config().unpersist("/etc/rhsm/rhsm.conf")
                    except process.CalledProcessError:
                        raise RuntimeError("Couldn't remove old configuration!"
                                           " Check the output of "
                                           "subscription-manager remove --all")

                # First two are Sat5/RHN classic, last two are SAM/Sat6
                configs = ["/etc/sysconfig/rhn/systemid",
                           "/etc/sysconfig/rhn/up2date",
                           "/var/lib/rhsm/cache/installed_products.json",
                           "/var/lib/rhsm/facts/facts.json"]
                configs.extend(glob.glob("/etc/pki/consumer/*pem*"))

                [scrub(f) for f in configs]

                # Don't rely on Vars.location, since it may not be set, but we
                # should remove this regardless
                cert_path = "/etc/rhsm/ca/candlepin-local.pem"
                if os.path.exists(cert_path):
                    Config().unpersist(cert_path)
                    os.unlink(cert_path)
                Config().unpersist("/etc/cron.d/rhn-virtualization.cron")

        class ConfigureSubscriptionManager(utils.Transaction.Element):
            title = "Configuring subscription manager"

            def commit(self):
                initial_args = ["subscription-manager"]
                initial_args.extend(["config"])

                host = None
                port = None
                prefix = None

                if cfg["url"]:
                    host, port, prefix = RHN().parse_host_uri(cfg["url"])

                    # Default to /rhsm for Satellite 6
                    if DEFAULT_CA_SAT6 in cfg["ca_cert"] and \
                       cfg["rhntype"] == "satellite":
                        prefix = "/rhsm"

                else:
                    # Default values for public SAM
                    host = "subscription.rhn.redhat.com"
                    prefix = "/subscription"

                # Assume https unless we matched another scheme, probably http
                port = str(port) if port else "443"

                mapping = {"--server.hostname": host,
                           "--server.port":     port,
                           }

                # Figure out what other arguments need to be set
                # If there's a ca certificate or it's satellite, it's sat6
                if cfg["ca_cert"] and DEFAULT_CA_SAT6 in cfg["ca_cert"] and \
                   cfg["rhntype"] == "satellite":
                    mapping["--server.prefix"] = prefix
                else:
                    prefix = "%s/%s" % (host, prefix) if prefix else \
                             "%s/pulp/repos" % host
                    mapping["--rhsm.baseurl"] = prefix

                # FIXME: Why are we setting a default value if this was set?
                # Feels like it should be the other way. Investigate
                if cfg["ca_cert"]:
                    mapping["--rhsm.repo_ca_cert"] = \
                        "/etc/rhsm/ca/candlepin-local.pem"

                ab = ArgBuilder(initial_args, mapping)
                try:
                    process.check_call(ab.get_commandlist())
                    Config().persist("/etc/rhsm/rhsm.conf")
                except process.CalledProcessError:
                    self.logger.debug("Calling subscription-manager with "
                                      "'%s' failed!" % ab.get_commandlist(
                                          string=True))
                    raise RuntimeError("Error updating subscription manager "
                                       "configuration")

        class ConfigureSAMProxy(utils.Transaction.Element):
            title = "Configuring subscription-manager to use a proxy"

            def commit(self):
                initial_args = ["subscription-manager"]
                initial_args.extend(["config"])

                def _run_command(mapping):
                    ab = ArgBuilder(initial_args, mapping)
                    try:
                        process.check_call(ab.get_commandlist())
                    except process.CalledProcessError:
                        self.logger.debug("Updating subscription-manager proxy"
                                          " configuration with '%s' failed!" %
                                          ab.get_commandlist(string=True,
                                                             filtered=True))
                        raise RuntimeError("Error updating subscription "
                                           "manager proxy configuration")

                mapping = {"--server.proxy_user": cfg["proxyuser"]}
                _run_command(mapping)

                if cfg["proxyuser"]:
                    pass_mapping = {"--server.proxy_password": proxypass}
                    _run_command(pass_mapping)

        class PrepareSAM(utils.Transaction.Element):
            # SAM path is used for sat6 as well
            title = "Preparing for registration"

            def commit(self):
                # Sanity checking args for valid combinations
                if not cfg["activationkey"] and not (cfg["username"] and
                                                     password):
                    raise RuntimeError("No combination of activationkey "
                                       "or username+password was given for "
                                       "registration!")

                initial_args = ["/usr/sbin/subscription-manager"]
                initial_args.extend(["register", "--force"])

                # Don't autosubscribe for now, since it may cause entitlement
                # problems with SAM and Sat6
                # if not cfg["activationkey"]":
                #     initial_args.append("--autosubscribe")

                mapping = {"--activationkey": cfg["activationkey"],
                           "--org":           cfg["org"],
                           "--environment":   cfg["environment"],
                           "--username":      cfg["username"],
                           "--password":      password,
                           "--name":          cfg["profile"],
                           "--proxy":         cfg["proxy"],
                           "--proxyuser":     cfg["proxyuser"],
                           "--proxypassword": proxypass,
                           "--type":          "hypervisor"
                           }

                Vars.argbuilder = ArgBuilder(initial_args, mapping)

        class RegisterSAM(utils.Transaction.Element):
            title = "Registering to server"

            def commit(self):
                def check_for_errors(smreg_output):
                    mapping = {"Invalid credentials": "Invalid username"
                                                      "/password combination",
                               "already been taken":  "This hostname is "
                                                      "already registered",
                               "Organization":        "Organization not found "
                                                      "on Satellite 6"}
                    for k, v in mapping.items():
                        if k in smreg_output:
                            raise RuntimeError(v)

                    # Fallthrough
                    raise RuntimeError("Registration Failed")

                self.logger.info("Registering with subscription-manager")
                self.logger.info(Vars.argbuilder.get_commandlist(string=True,
                                                                 filtered=True)
                                 )

                # This may block if waiting for input with check_output.
                # pipe doesn't block
                smreg_output = process.pipe(
                    Vars.argbuilder.get_commandlist())
                if "been registered" not in smreg_output:
                    check_for_errors(smreg_output)

                # If we made it down here, we registered successfully
                else:
                    # Truncate the classic rhn cron job in favor of RHSM
                    rhn_cronjob = "/etc/cron.d/rhn-virtualization.cron"
                    with open(rhn_cronjob, "w"):
                        pass
                    Config().persist(rhn_cronjob)

                    system.service("rhsmcertd", "start")
                    configs = ["/var/lib/rhsm/cache/installed_products.json",
                               "/var/lib/rhsm/facts/facts.json"]

                    for conf in configs:
                        Config().persist(conf)
                        Config().persist("/etc/pki/consumer/key.pem")
                        Config().persist("/etc/pki/consumer/cert.pem")
                        if cfg["url"]:
                            self.logger.info("System %s successfully "
                                             "registered to %s" %
                                             (cfg["profile"],
                                              cfg["url"]))
                        else:
                            self.logger.info("System %s successfully "
                                             "registered to RHSM" %
                                             cfg["profile"])

                    # This isn't strictly necessary
                    if RHN().retrieve()["activationkey"]:
                        cmd = ["subscription-manager", "auto-attach"]
                        try:
                            process.check_call(cmd)
                        except process.CalledProcessError:
                            raise RuntimeError("Registration succeded, but "
                                               "there was a problem while "
                                               "auto-attaching with the "
                                               "provided key")

        self.logger.debug(cfg)
        rhntype = cfg["rhntype"]
        tx = utils.Transaction("Performing entitlement registration")
        tx.append(RemoveConfigs())

        if rhntype == "sam" or \
           (rhntype == "satellite" and DEFAULT_CA_SAT6 in cfg["ca_cert"]) or \
           (system.is_min_el(7) and rhntype == "rhn"):
            if rhntype == "satellite":
                if cfg["activationkey"]:
                    if not cfg["org"]:
                        del tx[0]
                        tx.extend([RaiseError(
                                        "Registration to Satellite "
                                        "6 with activation key requires "
                                        "an organization to be set")])
                        return tx
                    if cfg["environment"]:
                        del tx[0]
                        tx.extend([RaiseError(
                                        "Registration to Satellite 6 with "
                                        "activation key do not allow "
                                        "environments to be specified")])
                        return tx
                    if cfg["username"] or password:
                        del tx[0]
                        tx.extend([RaiseError(
                                        "Registration to Satellite 6 with an "
                                        "activation key do not require "
                                        "credentials")])
                        return tx
                else:
                    if not cfg["org"] or not cfg["environment"]:
                        del tx[0]
                        tx.extend([RaiseError(
                                        "Registration to Satellite 6 requires "
                                        "an organization and environment to "
                                        "be set")])
                        return tx

                    if not cfg["username"] or not password:
                        del tx[0]
                        tx.extend([RaiseError(
                                        "Registration to Satellite 6 without "
                                        "an activation key requires user "
                                        "credentials")])
                        return tx

            if cfg["proxy"]:
                tx.append(ConfigureSAMProxy())

            if cfg["ca_cert"]:
                Vars.ca_cert = cfg["ca_cert"]
                Vars.location = "/etc/rhsm/ca/candlepin-local.pem"
                tx.append(DownloadCertificate())

            if cfg["url"]:
                tx.append(ConfigureSubscriptionManager())

            tx.extend([PrepareSAM(),
                       RegisterSAM()
                       ])
        else:
            if rhntype == "rhn":
                tx.append(ConfigureRHNClassic())

            tx.extend([PrepareClassicRegistration(),
                       DownloadCertificate(),
                       RegisterRHNClassic(),
                       UpdateGuests()
                       ])
        return tx


class ArgBuilder(base.Base):
    args = None
    filtered_args = ["--password", "--proxyPassword",
                     "--server.proxy_password", "--proxypassword"]

    def __init__(self, initial_args, mapping):
        self.args = initial_args
        self._build_map(mapping)

    def _build_map(self, mapping):
        # Can't filter() on a dict, so use a dict comprehension to do it
        # and append in one line
        map(lambda (x, y): self.args.extend([x, y]),
            dict((k, v) for k, v in mapping.items() if v).iteritems())

    def get_commandlist(self, string=False, filtered=False):
        if not filtered and not string:
            return self.args

        command = " ".join(self.args)

        def filter(command):
            for arg in self.filtered_args:
                r = re.compile(r'(%s) \S+' % arg)
                command = re.sub(r, r'\1 XXXXXXXX', command)
            return command

        if not filtered and string:
            return command
        elif filtered:
            if string:
                return filter(command)
            else:
                return filter(command).split()
