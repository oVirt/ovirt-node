#!/usr/bin/python
# rhn.py - Copyright (C) 2011 Red Hat, Inc.
# Register system to RHN
# Written by Joey Boggs <jboggs@redhat.com> and Alan Pevec <apevec@redhat.com>
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

import os
import sys
from ovirtnode.ovirtfunctions import *
from subprocess import Popen, PIPE, STDOUT
from snack import *
from urlparse import urlparse
import _snack

RHN_CONFIG_FILE = "/etc/sysconfig/rhn/up2date"
RHSM_CONFIG_FILE = "/etc/rhsm/rhsm.conf"
RHN_XMLRPC_ADDR = "https://xmlrpc.rhn.redhat.com/XMLRPC"

def run_rhnreg(serverurl="", cacert="", activationkey="", username="",
               password="", profilename="", proxyhost="", proxyuser="",
               proxypass=""):
    # novirtinfo: rhn-virtualization daemon refreshes virtinfo
    extra_args = ['--novirtinfo', '--norhnsd', '--nopackages', '--force']
    args = ['/usr/sbin/rhnreg_ks']
    # Get cacert location
    if len(serverurl) > 0:
        if not serverurl.endswith("/XMLRPC"):
            serverurl = serverurl + "/XMLRPC"
        args.append('--serverUrl')
        args.append(serverurl)
    location = "/etc/sysconfig/rhn/%s" % os.path.basename(cacert)
    if len(cacert) > 0:
        if not os.path.exists(cacert):
            logger.debug("CACert: " + cacert)
            logger.debug("Location: " + location)
            logger.info("Downloading Satellite CA cert.....")
            logger.debug("From: " + cacert + " To: " + location)
            wget_cmd = "wget -nd --no-check-certificate " + \
                            "--timeout=30 --tries=3 -O \"" + location + \
                            "\" \"" + cacert + "\""
            wget_proc = passthrough(wget_cmd, logger.debug)
            if wget_proc.retval > 0:
                logger.error("Error Downloading Satellite CA cert!")
                logger.debug(wget_proc.stdout)
                return 3
        if os.path.isfile(location):
            if os.stat(location).st_size > 0:
                args.append('--sslCACert')
                args.append(location)
                ovirt_store_config(location)
            else:
                logger.error("Error Downloading Satellite CA cert!")
                return 3

    if len(activationkey):
        args.append('--activationkey')
        args.append(activationkey)
    elif len(username):
        args.append('--username')
        args.append(username)
        if len(password):
            args.append('--password')
            args.append(password)
    else:
        # skip RHN registration when neither activationkey
        # nor username/password is supplied
        # return success for AUTO w/o rhn_* parameters
        return 1

    if len(profilename):
        args.append('--profilename')
        args.append(profilename)

    if len(proxyhost) > 1:
        args.append('--proxy')
        args.append(proxyhost)
        if len(proxyuser):
            args.append('--proxyUser')
            args.append(proxyuser)
            if len(proxypass):
                args.append('--proxyPassword')
                args.append(proxypass)

    args.extend(extra_args)

    logger.info("Registering to RHN account.....")

    remove_config("/etc/sysconfig/rhn/systemid")
    remove_config("/etc/sysconfig/rhn/up2date")
    logged_args = list(args)
    remove_values_from_args = ["--password", "--proxyPassword"]
    for idx, arg in enumerate(logged_args):
        if arg in remove_values_from_args:
            logged_args[idx+1] = "XXXXXXX"
    logged_args = str(logged_args)

    logger.debug(logged_args)
    rhn_reg = subprocess_closefds(args, shell=False, stdout=PIPE,
                                  stderr=STDOUT)
    rhn_reg_output = rhn_reg.stdout.read()
    logger.debug(rhn_reg_output)
    if rhn_reg.wait() == 0:
        ovirt_store_config("/etc/sysconfig/rhn/up2date")
        ovirt_store_config("/etc/sysconfig/rhn/systemid")
        logger.info("System %s sucessfully registered to %s" % (profilename,
                                                                serverurl))
        return 0
    else:
        if "username/password" in rhn_reg_output:
            rc = 2
        else:
            rc = 1
        logger.error("Error registering to RHN account!")
        return rc


def parse_host_port(u):
    if u.count('://') == 1:
        (proto, u) = u.split('://')
    else:
        proto = ''
    if u.count(':') == 1:
        (u, port) = u.split(':')
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
    host = u.split('/')[0]
    return (host, port)


def run_rhsm(serverurl="", cacert="", activationkey="", username="",
             password="", profilename="", proxyhost="", proxyuser="",
             proxypass="", org=""):
    extra_args = ['--force', '--autosubscribe']
    sm = ['/usr/sbin/subscription-manager']

    args = list(sm)
    args.append('register')
    if len(activationkey) and len(org):
        args.append('--activationkey')
        args.append(activationkey)
        args.append('--org')
        args.append(org)
    elif len(username):
        args.append('--username')
        args.append(username)
        if len(password):
            args.append('--password')
            args.append(password)
    else:
        # skip RHN registration when neither activationkey
        # nor username/password is supplied
        # return success for AUTO w/o rhn_* parameters
        return 1

    if len(serverurl) > 0:
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
    if len(cacert) > 0:
        if not os.path.exists(cacert):
            logger.debug("CACert: " + cacert)
            logger.debug("Location: " + location)
            logger.info("Downloading Satellite CA cert.....")
            logger.debug("From: " + cacert + " To: " + location)
            system("wget -q -r -nd --no-check-certificate --timeout=30 " +
                   "--tries=3 -O \"" + location + "\" \"" + cacert + "\"")
        if os.path.isfile(location):
            if os.stat(location).st_size > 0:
                ovirt_store_config(location)
            else:
                logger.error("Error Downloading CA cert!")
                return 3

    smconf = list(sm)
    smconf.append('config')
    smconf.append('--server.hostname')
    smconf.append(host)
    smconf.append('--server.port')
    smconf.append(port)
    smconf.append('--server.prefix')
    smconf.append(prefix)

    if len(cacert) > 0:
        smconf.append('--rhsm.repo_ca_cert')
        smconf.append('/etc/rhsm/ca/candlepin-local.pem')
    log(str(smconf))
    smconf_proc = subprocess_closefds(smconf, shell=False, stdout=PIPE,
                                      stderr=STDOUT)
    smconf_output = smconf_proc.stdout.read()
    log(smconf_proc)
    if smconf_proc.wait() == 0:
        ovirt_store_config("/etc/rhsm/rhsm.conf")

    if len(profilename):
        args.append('--name')
        args.append(profilename)

    if len(proxyhost) > 1:
        args.append('--proxy')
        args.append(proxyhost)
        if len(proxyuser):
            args.append('--proxyuser')
            args.append(proxyuser)
            if len(proxypass):
                args.append('--proxypassword')
                args.append(proxypass)

    args.extend(extra_args)

    log("Registering to RHN account.....")

    import glob
    all_rhsm_configs = (["/var/lib/rhsm/cache/installed_products.json",
                        "/var/lib/rhsm/facts/facts.json"])
    unmount_config(all_rhsm_configs)
    unmount_config(glob.glob("/etc/pki/consumer/*pem"))

    def unlink_if_exists(f):
        if os.path.exists(f):
            os.unlink(f)
    for f in all_rhsm_configs:
        unlink_if_exists(f)

    logged_args = list(args)
    remove_values_from_args = ["--password", "--proxypassword"]
    for idx, arg in enumerate(logged_args):
        if arg in remove_values_from_args:
            logged_args[idx+1] = "XXXXXXX"
    logged_args = str(logged_args)

    log(logged_args)
    smreg_proc = subprocess_closefds(args, shell=False, stdout=PIPE,
                                     stderr=STDOUT)
    smreg_output = smreg_proc.stdout.read()
    log(smreg_output)
    smreg_proc.wait()
    if "been registered" in smreg_output:
        ovirt_store_config(all_rhsm_configs)
        ovirt_store_config("/etc/pki/consumer/key.pem")
        ovirt_store_config("/etc/pki/consumer/cert.pem")
        log("System %s sucessfully registered to %s" % (profilename,
                                                        serverurl))
        return 0
    else:
        if "username/password" in smreg_output:
            rc = 2
        else:
            rc = 1
        log("Error registering to RHN account!")
        return rc


def ov(var):
    if var in OVIRT_VARS:
        return OVIRT_VARS[var]
    else:
        return ""


def get_rhn_config():
    conf_files = []
    if os.path.exists(RHN_CONFIG_FILE):
        conf_files.append(RHN_CONFIG_FILE)
    if os.path.exists(RHSM_CONFIG_FILE):
        conf_files.append(RHSM_CONFIG_FILE)
    rhn_conf = {}
    for f in conf_files:
        rhn_config = open(f)
        for line in rhn_config:
            if "=" in line and "[comment]" not in line:
                item, value = line.replace(" ", "").split("=")
                rhn_conf[item] = value.strip()
        rhn_config.close()
    return rhn_conf


def rhn_check():
    filebased = True
    registered = False
    if filebased:
        # Thefollowing file exists when the sys is registered with rhn
        registered = os.path.exists("/etc/sysconfig/rhn/systemid")
    else:
        rhncheck_cmd = subprocess_closefds("rhn_check", shell=False,
                                           stdout=PIPE, stderr=STDOUT)
        rhncheck = rhncheck_cmd.communicate()[0]
        if rhncheck_cmd.returncode == 0:
            registered = True
    return registered


def sam_check():
    filebased = True
    registered = False
    if filebased:
        # Thefollowing file exists when the sys is registered with a sat server
        registered = os.path.exists("/etc/rhsm/ca/candlepin-local.pem")
    else:
        samcheck_cmd = subprocess_closefds("subscription-manager identity",
                                           shell=True, stdout=PIPE,
                                           stderr=open('/dev/null', 'w'))
        registered = "identity is:" in samcheck_cmd.stdout.read()
    return registered

def get_rhn_status():
    msg = ""
    status = 0
    rhn_conf = get_rhn_config()
    if rhn_check():  # Is Satellite or Hosted
        status = 1
        logger.info(rhn_conf)
        try:
            if "serverURL" in rhn_conf:
                if ("https://xmlrpc.rhn.redhat.com/XMLRPC" in
                    rhn_conf["serverURL"]):
                    msg = "RHN"
                else:
                    msg = "Satellite"
        except:
            #corrupt up2date config in this case
            status = 0
            pass
    elif sam_check():
        status = 1
        msg = "SAM"
    return (status, msg)


def rhn_auto():
    rhn_parameters = ["OVIRT_RHN_CA_CERT", "OVIRT_RHN_USERNAME",
        "OVIRT_RHN_PASSWORD", "OVIRT_RHN_ACTIVATIONKEY", "OVIRT_RHN_PROFILE",
        "OVIRT_RHN_ACTIVATIONKEY", "OVIRT_RHN_PROXY", "OVIRT_RHN_PROXYUSER",
        "OVIRT_RHN_PROXYPASSWORD"]

    # RHN_TYPE & RHN_URL have defaults if not present, set them here
    if not "OVIRT_RHN_TYPE" in OVIRT_VARS:
        OVIRT_VARS["OVIRT_RHN_TYPE"] = "classic"
    if not "OVIRT_RHN_URL" in OVIRT_VARS:
        OVIRT_VARS["OVIRT_RHN_URL"] = "https://xmlrpc.rhn.redhat.com/XMLRPC"

    # Default everything else to ""
    for parameter in rhn_parameters:
        if not parameter in OVIRT_VARS:
            OVIRT_VARS[parameter] = ""

    # We know USERNAME, PASSWORD & ACTIVATIONKEY are present
    # verify if username+password or activationkey is not ""
    if ((not OVIRT_VARS['OVIRT_RHN_USERNAME'] or
            not OVIRT_VARS['OVIRT_RHN_PASSWORD']) and
        not OVIRT_VARS['OVIRT_RHN_ACTIVATIONKEY']):
            logger.debug("RHN registration requires a username and " +
                "password, or an activation key.")
            return False

    if (not "https://xmlrpc.rhn.redhat.com/XMLRPC" in
        OVIRT_VARS["OVIRT_RHN_URL"] and not OVIRT_VARS["OVIRT_RHN_CA_CERT"]):
        logger.debug("Missing Satellite CA certificate URL")
        return False

    if OVIRT_VARS["OVIRT_RHN_TYPE"] == "sam":
        reg_rc = run_rhsm(serverurl=OVIRT_VARS["OVIRT_RHN_URL"],
            cacert=OVIRT_VARS["OVIRT_RHN_CA_CERT"],
            activationkey=OVIRT_VARS["OVIRT_RHN_ACTIVATIONKEY"],
            username=OVIRT_VARS["OVIRT_RHN_USERNAME"],
            password=OVIRT_VARS["OVIRT_RHN_PASSWORD"],
            profilename=OVIRT_VARS["OVIRT_RHN_PROFILE"],
            proxyhost=OVIRT_VARS["OVIRT_RHN_PROXY"],
            proxyuser=OVIRT_VARS["OVIRT_RHN_PROXYUSER"],
            org=OVIRT_VARS["OVIRT_RHN_ORG"],
            proxypass=OVIRT_VARS["OVIRT_RHN_PROXYPASSWORD"])
    elif OVIRT_VARS["OVIRT_RHN_TYPE"] == "classic":
        reg_rc = run_rhnreg(serverurl=OVIRT_VARS["OVIRT_RHN_URL"],
            cacert=OVIRT_VARS["OVIRT_RHN_CA_CERT"],
            activationkey=OVIRT_VARS["OVIRT_RHN_ACTIVATIONKEY"],
            username=OVIRT_VARS["OVIRT_RHN_USERNAME"],
            password=OVIRT_VARS["OVIRT_RHN_PASSWORD"],
            profilename=OVIRT_VARS["OVIRT_RHN_PROFILE"],
            proxyhost=OVIRT_VARS["OVIRT_RHN_PROXY"],
            proxyuser=OVIRT_VARS["OVIRT_RHN_PROXYUSER"],
            proxypass=OVIRT_VARS["OVIRT_RHN_PROXYPASSWORD"])
    else:
        logger.debug("Unknown RHN Type")
        return False
    if reg_rc == 0 and not False:
        logger.info("RHN Registration Successful")
        # sync profile if reregistering, fixes problem with virt guests not showing
        subprocess_closefds("rhn-profile-sync", shell=True, stdout=PIPE,
                                  stderr=STDOUT)
        return True
    elif reg_rc > 0:
        logger.debug(reg_rc)
        if reg_rc == 2:
            msg = "Invalid Username / Password "
        elif reg_rc == 3:
            msg = "Unable to retrieve satellite certificate"
        else:
            msg = "Check ovirt.log for details"
            logger.info("RHN Configuration Failed")
            return False


#
# configuration UI plugin interface
#
class Plugin(PluginBase):
    """Plugin for RHN registration option.
    """

    def __init__(self, ncs):
        PluginBase.__init__(self, "Red Hat Network", ncs)
        self.rhn_conf = {}
        self.INVALID_CA_CONFIG_MSG = ""
        self.INVALID_URL_CONFIG_MSG = ""

    def form(self):
        elements = Grid(2, 12)
        login_grid = Grid(4, 2)
        self.rhn_user = Entry(15, "")
        self.rhn_pass = Entry(15, "", password=1)
        login_grid.setField(self.rhn_user, 1, 0)
        login_grid.setField(Label("Login: "), 0, 0, anchorLeft=1)
        login_grid.setField(Label(" Password: "), 2, 0, anchorLeft=1)
        login_grid.setField(self.rhn_pass, 3, 0, padding=(0, 0, 0, 1))
        elements.setField(login_grid, 0, 4, anchorLeft=1)
        profile_grid = Grid(2, 2)
        self.profilename = Entry(30, "")
        self.profilename.setCallback(self.profilename_callback)
        profile_grid.setField(Label("Profile Name (optional): "), 0, 0,
                                    anchorLeft=1)
        profile_grid.setField(self.profilename, 1, 0, anchorLeft=1)
        elements.setField(profile_grid, 0, 5, anchorLeft=1,
                          padding=(0, 0, 0, 1))
        rhn_type_grid = Grid(3, 2)
        self.public_rhn = Checkbox("RHN ")
        self.public_rhn.setCallback(self.public_rhn_callback)
        self.rhn_satellite = Checkbox("Satellite ")
        self.rhn_satellite.setCallback(self.rhn_satellite_callback)
        self.sam = Checkbox("Subscription Asset Manager")
        self.sam.setCallback(self.sam_callback)
        rhn_type_grid.setField(self.public_rhn, 0, 0)
        rhn_type_grid.setField(self.rhn_satellite, 1, 0)
        rhn_type_grid.setField(self.sam, 2, 0)
        elements.setField(rhn_type_grid, 0, 6, anchorLeft=1,
                          padding=(0, 0, 0, 1))
        rhn_grid = Grid(2, 2)
        rhn_grid.setField(Label("URL: "), 0, 0, anchorLeft=1)
        self.rhn_url = Entry(40, "")
        self.rhn_url.setCallback(self.rhn_url_callback)
        rhn_grid.setField(self.rhn_url, 1, 0, anchorLeft=1,
                          padding=(1, 0, 0, 0))
        self.rhn_ca = Entry(40, "")
        self.rhn_ca.setCallback(self.rhn_ca_callback)
        rhn_grid.setField(Label("CA : "), 0, 1, anchorLeft=1)
        rhn_grid.setField(self.rhn_ca, 1, 1, anchorLeft=1,
                          padding=(1, 0, 0, 0))
        elements.setField(rhn_grid, 0, 7, anchorLeft=1, padding=(0, 0, 0, 1))
        top_proxy_grid = Grid(4, 2)
        bot_proxy_grid = Grid(4, 2)
        elements.setField(Label("HTTP Proxy"), 0, 8, anchorLeft=1)
        self.proxyhost = Entry(20, "")
        self.proxyport = Entry(5, "", scroll=0)
        self.proxyuser = Entry(14, "")
        self.proxypass = Entry(12, "", password=1)
        self.proxyhost.setCallback(self.proxyhost_callback)
        self.proxyport.setCallback(self.proxyport_callback)
        top_proxy_grid.setField(Label("Server: "), 0, 0, anchorLeft=1)
        top_proxy_grid.setField(self.proxyhost, 1, 0, anchorLeft=1,
                                padding=(0, 0, 1, 0))
        top_proxy_grid.setField(Label("Port: "), 2, 0, anchorLeft=1)
        top_proxy_grid.setField(self.proxyport, 3, 0, anchorLeft=1,
                                padding=(0, 0, 0, 0))
        bot_proxy_grid.setField(Label("Username: "), 0, 0, anchorLeft=1)
        bot_proxy_grid.setField(self.proxyuser, 1, 0, padding=(0, 0, 1, 0))
        bot_proxy_grid.setField(Label("Password: "), 2, 0, anchorLeft=1)
        bot_proxy_grid.setField(self.proxypass, 3, 0, padding=(0, 0, 0, 0))
        elements.setField(top_proxy_grid, 0, 10, anchorLeft=1,
                          padding=(0, 0, 0, 0))
        elements.setField(bot_proxy_grid, 0, 11, anchorLeft=1,
                          padding=(0, 0, 0, 0))
        self.proxyhost.setCallback(self.proxyhost_callback)
        self.proxyport.setCallback(self.proxyport_callback)

        # optional: profilename, proxyhost, proxyuser, proxypass
        self.rhn_conf = get_rhn_config()
        if not "https://xmlrpc.rhn.redhat.com/XMLRPC" in self.rv("serverURL") \
            and not sam_check():
            self.rhn_url.set(self.rv("serverURL"))
            self.rhn_ca.set(self.rv("sslCACert"))
        elif sam_check():
            if not "subscription.rhn.redhat.com" in self.rv("hostname"):
                self.rhn_url.set("https://" + self.rv("hostname"))
                if os.path.exists("/etc/rhsm/ca/candlepin-local.pem"):
                    self.rhn_ca.set("/etc/rhsm/ca/candlepin-local.pem")
        self.proxyuser.set(self.rv("proxyUser"))
        self.proxypass.set(self.rv("proxyPassword"))
        try:
            p_server, p_port = self.rv("httpProxy").split(":")
            self.proxyhost.set(p_server)
            self.proxyport.set(p_port)
        except:
            pass
        self.rhn_actkey = Entry(40, "")
        if rhn_check():
            if self.rhn_url.value() == RHN_XMLRPC_ADDR or \
                                       len(self.rhn_url.value()) == 0 and \
                                       RHN_XMLRPC_ADDR in \
                                       self.rhn_conf["serverURL"]:
                self.public_rhn.setValue("*")
                self.rhn_url.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
                self.rhn_ca.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
            else:
                self.rhn_satellite.setValue("*")
                self.rhn_url.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)
                self.rhn_ca.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)
        elif sam_check():
            self.sam.setValue("*")
        else:
            self.public_rhn.setValue("*")
            self.rhn_url.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
            self.rhn_ca.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)

        if network_up():
            status, msg = get_rhn_status()
            if status == 0:
                rhn_msg = ("RHN Registration is required only if you wish " +
                           "to use\nRed Hat Enterprise Linux with virtual " +
                           "guests\nsubscriptions for your guests.")
            else:
                rhn_msg = "RHN Registration\n\nRegistration Status: %s" % msg
            elements.setField(Textbox(62, 4, rhn_msg), 0, 2, anchorLeft=1)
        else:
            elements.setField(Textbox(62, 3, "Network Down, Red " +
                                      "Hat Network Registration Disabled"),
                                      0, 2, anchorLeft=1)
            for i in (self.rhn_user, self.rhn_pass, self.profilename,
                     self.public_rhn, self.rhn_satellite, self.sam,
                     self.rhn_url, self.rhn_ca, self.proxyhost,
                     self.proxyport, self.proxyuser, self.proxypass):
                i.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
        return [Label(""), elements]

    def action(self):
        self.ncs.screen.setColor("BUTTON", "black", "red")
        self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
        if not network_up():
            return False
        if (len(self.INVALID_URL_CONFIG_MSG) > 0 or
                len(self.INVALID_CA_CONFIG_MSG) > 0):
            self.ncs._create_warn_screen()
            msg = "\n%s\n%s\n" % (self.INVALID_URL_CONFIG_MSG, self.INVALID_CA_CONFIG_MSG)
            ButtonChoiceWindow(self.ncs.screen, "Configuration Check",
                                msg, buttons=['Ok'])
            self.ncs._set_title()
            self.INVALID_URL_CONFIG_MSG = ""
            self.INVALID_CA_CONFIG_MSG = ""
            return False
        if self.rhn_satellite.value() == 1 and self.rhn_ca.value() == "":
            ButtonChoiceWindow(self.ncs.screen, "RHN Configuration",
                               "Please input a CA certificate URL",
                               buttons=['Ok'])
            return False
        if len(self.rhn_user.value()) < 1 or len(self.rhn_pass.value()) < 1:
            ButtonChoiceWindow(self.ncs.screen, "RHN Configuration",
                               "Login/Password must not be empty\n",
                               buttons=['Ok'])
            return False
        key_files = ["/etc/sysconfig/rhn/systemid",  # To check RHN
                     "/etc/rhsm/ca/candlepin-local.pem"  # To check SAM
                     ]
        for key_file in key_files:
            if os.path.exists(key_file):
                remove_config(key_file)
                os.remove(key_file)
        if self.sam.value() == 1:
            if os.path.exists(RHN_CONFIG_FILE):
                remove_config(RHN_CONFIG_FILE)
                os.remove(RHN_CONFIG_FILE)
            reg_rc = run_rhsm(serverurl=self.rhn_url.value(),
                cacert=self.rhn_ca.value(),
                activationkey=self.rhn_actkey.value(),
                username=self.rhn_user.value(),
                password=self.rhn_pass.value(),
                profilename=self.profilename.value(),
                proxyhost=self.proxyhost.value() + ":" +
                          self.proxyport.value(),
                proxyuser=self.proxyuser.value(),
                org="",
                proxypass=self.proxypass.value())
        else:
            # clear sam registration
            system("subscription-manager unregister")
            reg_rc = run_rhnreg(serverurl=self.rhn_url.value(),
                cacert=self.rhn_ca.value(),
                activationkey=self.rhn_actkey.value(),
                username=self.rhn_user.value(),
                password=self.rhn_pass.value(),
                profilename=self.profilename.value(),
                proxyhost=self.proxyhost.value() + ":" +
                          self.proxyport.value(),
                proxyuser=self.proxyuser.value(),
                proxypass=self.proxypass.value())
        if reg_rc == 0 and not False:
            ButtonChoiceWindow(self.ncs.screen, "RHN Configuration",
                               "RHN Registration Successful",
                               buttons=['Ok'])
            self.ncs.reset_screen_colors()
            return True
        elif reg_rc > 0:
            if reg_rc == 2:
                msg = "Invalid Username / Password "
            elif reg_rc == 3:
                msg = "Unable to retrieve satellite certificate"
            else:
                msg = "Check ovirt.log for details"
            ButtonChoiceWindow(self.ncs.screen, "RHN Configuration",
                               "RHN Configuration Failed\n\n" +
                               msg, buttons=['Ok'])
            self.ncs.reset_screen_colors()
            return False

    def profilename_callback(self):
        if self.profilename.value() is None:
            return True
        length = len(self.profilename.value())
        if (length > 0 and length < 3):
            self.ncs._create_warn_screen()
            self.ncs.screen.setColor("BUTTON", "black", "red")
            self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
            ButtonChoiceWindow(self.ncs.screen, "Configuration Check",
                               "RHN Profile Name must be at least 3 characters",
                               buttons=['Ok'])
            self.ncs.reset_screen_colors()
            self.ncs.gridform.draw()
            self.ncs._set_title()

    def rhn_url_callback(self):
        # TODO URL validation
        if not is_valid_url(self.rhn_url.value()):
            self.INVALID_URL_CONFIG_MSG = "Invalid RHN URL entered"
        else:
            self.INVALID_URL_CONFIG_MSG = ""

        if self.rhn_satellite.value() == 1:
            host = self.rhn_url.value().replace("/XMLRPC", "")

    def rhn_ca_callback(self):
        # TODO URL validation
        msg = ""
        if not self.rhn_ca.value() == "":
            if not is_valid_url(self.rhn_ca.value()):
                if not os.path.exists(self.rhn_ca.value()):
                    self.INVALID_CA_CONFIG_MSG = "Invalid CA URL or Path"
                else:
                    self.INVALID_CA_CONFIG_MSG = ""
            else:
                self.INVALID_CA_CONFIG_MSG = ""
        elif self.rhn_ca.value() == "":
            self.INVALID_CA_CONFIG_MSG = "Please input a CA certificate URL"

    def rv(self, var):
        if var in self.rhn_conf:
            return self.rhn_conf[var]
        else:
            return ""

    def public_rhn_callback(self):
        self.rhn_satellite.setValue(" 0")
        self.sam.setValue(" 0")
        self.rhn_url.set("")
        self.rhn_ca.set("")
        self.rhn_url.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
        self.rhn_ca.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)

    def rhn_satellite_callback(self):
        self.public_rhn.setValue(" 0")
        self.sam.setValue(" 0")
        self.rhn_url.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)
        self.rhn_ca.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)

    def sam_callback(self):
        self.public_rhn.setValue(" 0")
        self.rhn_satellite.setValue(" 0")
        self.rhn_url.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)
        self.rhn_ca.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)

    def proxyhost_callback(self):
        if len(self.proxyhost.value()) > 0:
            if not is_valid_host_or_ip(self.proxyhost.value()):
                self.ncs.screen.setColor("BUTTON", "black", "red")
                self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
                self.ncs._create_warn_screen()
                ButtonChoiceWindow(self.ncs.screen, "Configuration Check",
                                   "Invalid Proxy Host", buttons=['Ok'])
                self.ncs.reset_screen_colors()
                self.ncs.gridform.draw()

    def proxyport_callback(self):
        if len(self.proxyport.value()) > 0:
            if not is_valid_port(self.proxyport.value()):
                self.ncs.screen.setColor("BUTTON", "black", "red")
                self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
                self.ncs._create_warn_screen()
                ButtonChoiceWindow(self.ncs.screen, "Configuration Check",
                                   "Invalid Proxy Port", buttons=['Ok'])
                self.ncs.reset_screen_colors()
                self.ncs.gridform.draw()


def get_plugin(ncs):
    return Plugin(ncs)
