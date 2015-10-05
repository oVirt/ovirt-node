#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# rhn_page.py - Copyright (C) 2013 Red Hat, Inc.
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
from ovirt.node import plugins, valid, ui, utils
import rhn_model
from ovirt.node.plugins import Changeset
from ovirt.node.utils import process, system
from ovirt.node.utils.network import NodeNetwork
import os.path
import logging
import sys
sys.path.append("/usr/share/rhn/up2date_client")


RHN_CONFIG_FILE = "/etc/sysconfig/rhn/up2date"
RHSM_CONFIG_FILE = "/etc/rhsm/rhsm.conf"
RHN_XMLRPC_ADDR = "https://xmlrpc.rhn.redhat.com/XMLRPC"
SAM_REG_ADDR = "subscription.rhn.redhat.com"
CANDLEPIN_CERT_FILE = "/etc/rhsm/ca/candlepin-local.pem"

logger = logging.getLogger(__name__)


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
        # The following file exists when the sys is registered with rhn
        registered = os.path.exists("/etc/sysconfig/rhn/systemid")
    else:
        if process.check_call("rhn_check"):
            registered = True
    return registered


def sam_check():
    if system.SystemRelease().is_redhat():
        import rhnreg
        if rhnreg.rhsm_registered():
            return True
    return False


def get_rhn_status():
    msg = ""
    status = 0
    rhn_conf = get_rhn_config()
    # local copy, blank proxy password
    # rhbz#837249
    for arg in "proxyPassword", "proxy_password":
        if arg in rhn_conf and rhn_conf[arg] != "":
            rhn_conf[arg] = "XXXXXXXX"
    if rhn_check():  # Is Satellite or Hosted
        status = 1
        try:
            if "serverURL" in rhn_conf:
                if RHN_XMLRPC_ADDR in rhn_conf["serverURL"]:
                    msg = "RHN"
                else:
                    msg = "Satellite"
        except:
            # corrupt up2date config in this case
            status = 0
            pass
    elif sam_check():
        status = 1
        msg = "SAM"
    return (status, msg)


class Plugin(plugins.NodePlugin):
    _model = None
    _rhn_types = [("rhn", "RHN"),
                  ("satellite", "Satellite"),
                  ("sam", "SAM")]
    _fields_enabled = False
    _type = "RHNSM Registration" if system.is_min_el(7) else \
            "RHN Registration"

    def __init__(self, app):
        super(Plugin, self).__init__(app)
        self._model = {}

    def has_ui(self):
        return True

    def name(self):
        return self._type

    def rank(self):
        return 310

    def model(self):
        cfg = rhn_model.RHN().retrieve()
        self.logger.debug(cfg)
        model = {"rhn.username": "",
                 "rhn.password": "",
                 "rhn.profilename": "",
                 "rhn.type": "",
                 "rhn.url": "",
                 "rhn.ca": "",
                 "rhn.org": "",
                 "rhn.activation_key": "",
                 "rhn.proxyhost": "",
                 "rhn.proxyport": "",
                 "rhn.proxyuser": "",
                 "rhn.proxypassword": "",
                 }

        status, rhn_type = get_rhn_status()
        model["rhn.username"] = cfg["username"]
        model["rhn.type"] = cfg["rhntype"]
        model["rhn.profilename"] = cfg["profile"]
        model["rhn.url"] = cfg["url"]
        model["rhn.ca"] = cfg["ca_cert"]
        model["rhn.proxyuser"] = cfg["proxyuser"]
        model["rhn.org"] = cfg["org"]
        try:
            p_server, p_port = cfg["proxy"].rsplit(":", 1)
            model["rhn.proxyhost"] = p_server
            model["rhn.proxyport"] = p_port
        except:
            pass
        return model

    def validators(self):
        return {"rhn.user": valid.Text(),
                "rhn.profilename": valid.Empty() | valid.Text(),
                "rhn.url": valid.Empty() | valid.URL(),
                "rhn.ca": valid.Empty() | valid.URL(),
                "rhn.proxyhost": (valid.FQDNOrIPAddress() |
                                  valid.URL() | valid.Empty()),
                "rhn.proxyport": valid.Port() | valid.Empty(),
                "rhn.proxyuser": valid.Text() | valid.Empty(),
                "rhn.org": valid.Text() | valid.Empty(),
                }

    def ui_content(self):
        cfg = rhn_model.RHN().retrieve()
        if self.application.args.dry:
            net_is_configured = True
        else:
            net_is_configured = NodeNetwork().is_configured()

        if not net_is_configured:

            ws = ([ui.Divider("notice.divider"),
                   ui.Notice("network.notice",
                             "Networking is not configured, please " +
                             "configure it before configuring RHN"),
                   ui.Divider("notice.divider")])

        else:
            status, rhn_type = get_rhn_status()
            if status == 0:
                rhn_msg = ("{0} is required only if you wish to use Red Hat "
                           "Enterprise Linux with virtual guests "
                           "subscriptions for your guests.".format(self._type))
            else:
                rhntype = cfg["rhntype"]
                if "satellite" in rhntype:
                    rhntype = rhntype.title()
                else:
                    rhntype = rhntype.upper()
                rhn_msg = "%s\n\nRegistration Status: %s" \
                          % (self._type, rhntype)

            ws = [ui.Header("header[0]", rhn_msg),
                  ui.Entry("rhn.username", "Login:"),
                  ui.PasswordEntry("rhn.password", "Password:"),
                  ui.Entry("rhn.profilename", "Profile Name (optional):"),
                  ui.Divider("divider[0]"),
                  ui.Options("rhn.type", "Type", self._rhn_types),
                  ui.Entry("rhn.url", "URL:"),
                  ui.Entry("rhn.ca", "CA URL:"),
                  ui.Entry("rhn.org", "Organization:"),
                  ui.Button("button.proxy", "HTTP Proxy Configuration"),
                  ]

        page = ui.Page("page", ws)
        self.widgets.add(ws)
        return page

    def on_change(self, changes):
        net_is_configured = NodeNetwork().is_configured()
        if "rhn.type" in changes and net_is_configured:
            if (changes["rhn.type"] == "sam" or
               changes["rhn.type"] == "satellite"):
                if not self._fields_enabled:
                    self._fields_enabled = True
                    self.widgets["rhn.url"].enabled(True)
                    self.widgets["rhn.ca"].enabled(True)
                    self.widgets["rhn.org"].enabled(True)
                    self.stash_pop_change("rhn.url", reuse_old=True)
                    self.stash_pop_change("rhn.ca", reuse_old=True)
            else:
                self._fields_enabled = False
                self.widgets["rhn.url"].enabled(False)
                self.widgets["rhn.ca"].enabled(False)
                self.stash_change("rhn.url")
                self.stash_change("rhn.ca")

        # Don't run a transaction yet, just close it out, save if the
        # normal save button is triggered
        if "proxy.save" in changes:
            self._dialog.close()
            return

    def on_merge(self, effective_changes):
        self.logger.debug("Saving RHN page")
        changes = Changeset(self.pending_changes(False))
        effective_model = Changeset(self.model())
        effective_model.update(effective_changes)

        self.logger.debug("Changes: %s" % changes)
        self.logger.debug("Effective Model: %s" % effective_model)

        rhn_keys = ["rhn.username", "rhn.password", "rhn.profilename",
                    "rhn.type", "rhn.url", "rhn.ca", "rhn.proxyhost",
                    "rhn.proxyport", "rhn.proxyuser", "rhn.proxypassword",
                    "rhn.org", "rhn.activation_key"]

        if "button.proxy" in changes:
            description = ("Please enter the proxy details to use " +
                           "for contacting the management server ")
            self._dialog = ProxyDialog("Input proxy information",
                                       description, self)
            self.widgets.add(self._dialog)
            return self._dialog

        txs = utils.Transaction("Updating RHN configuration")

        if changes.contains_any(rhn_keys):
            self.logger.debug(changes)
            self.logger.debug(effective_model)
            user = effective_model["rhn.username"]
            pw = effective_model["rhn.password"]
            profilename = effective_model["rhn.profilename"]
            rhn_type = effective_model["rhn.type"] or "rhn"
            url = effective_model["rhn.url"]
            ca = effective_model["rhn.ca"]
            org = effective_model["rhn.org"]
            activationkey = effective_model["rhn.activation_key"]
            proxyhost = effective_model["rhn.proxyhost"]
            proxyport = effective_model["rhn.proxyport"]
            proxyuser = effective_model["rhn.proxyuser"]
            proxypassword = effective_model["rhn.proxypassword"]

            warning_text = ""

            if rhn_type == "sam" or rhn_type == "satellite":
                if url == "" or url is None:
                        warning_text += "URL "

                if ca == "" or ca is None:
                        if warning_text is "":
                            warning_text += "CA path "
                        else:
                            warning_text += "and CA path "

            if warning_text is not "":
                txt = "%s must not be empty!" % warning_text
                self._error_dialog = ui.InfoDialog("dialog.error",
                                                   "RHN Error",
                                                   txt)
                return self._error_dialog
            else:
                model = rhn_model.RHN()
                model.clear()
                # join proxy host/port
                self.logger.debug(proxyhost)
                self.logger.debug(proxyport)
                proxy = None
                if len(proxyhost) > 0 and len(proxyport) > 0:
                    proxy = "%s:%s" % (proxyhost, proxyport)
                    self.logger.debug(proxy)
                model.update(rhn_type, url, ca, user, profilename,
                             activationkey, org, proxy, proxyuser)
                txs += model.transaction(password=pw,
                                         proxypass=proxypassword)
                progress_dialog = ui.TransactionProgressDialog("dialog.txs",
                                                               txs, self)
                progress_dialog.run()
        return self.ui_content()


class ProxyDialog(ui.Dialog):
    """A dialog to input proxy information
    """
    def __init__(self, title, description, plugin):
        self.keys = ["rhn.proxyhost", "rhn.proxyport", "rhn.proxyuser",
                     "rhn.proxypassword"]

        def clear_invalid(dialog, changes):
            [plugin.stash_change(prefix) for prefix in self.keys]

        title = _("RHN Proxy Information")

        entries = [ui.Entry("rhn.proxyhost", "Server:"),
                   ui.Entry("rhn.proxyport", "Port:"),
                   ui.Entry("rhn.proxyuser", "Username:"),
                   ui.PasswordEntry("rhn.proxypassword", "Password:")]
        children = [ui.Label("label[0]", description),
                    ui.Divider("divider[0]")]
        children.extend(entries)
        super(ProxyDialog, self).__init__("proxy.dialog", title, children)
        self.buttons = [ui.CloseButton("proxy.save", _("Save"),
                                       enabled=True),
                        ui.CloseButton("proxy.close",
                                       _("Cancel"))]

        b = plugins.UIElements(self.buttons)
        b["proxy.close"].on_activate.clear()
        b["proxy.close"].on_activate.connect(ui.CloseAction())
        b["proxy.close"].on_activate.connect(clear_invalid)
