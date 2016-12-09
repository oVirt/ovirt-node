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
from ovirt.node.plugins import Changeset
from ovirt.node.utils import process
from ovirt.node.utils.network import NodeNetwork
import rhn_model


class Plugin(plugins.NodePlugin):
    _model = None
    _rhn_types = [("rhn", "RHSM"),
                  ("satellite", "Satellite"),
                  ("sam", "SAM")]
    _fields_enabled = False

    def __init__(self, app):
        super(Plugin, self).__init__(app)
        self._model = {}

    def has_ui(self):
        return True

    def name(self):
        return "RHSM Registration"

    def rank(self):
        return 310

    def model(self):
        cfg = rhn_model.RHN().retrieve()
        self.logger.debug(cfg)

        model = {"rhn.username": cfg["username"],
                 "rhn.profilename": cfg["profile"],
                 "rhn.type": cfg["rhntype"],
                 "rhn.url": cfg["url"],
                 "rhn.ca": cfg["ca_cert"],
                 "rhn.org": cfg["org"],
                 "rhn.environment": cfg["environment"],
                 "rhn.activation_key": cfg["activationkey"],
                 "rhn.proxyuser": cfg["proxyuser"],
                 "rhn.proxyhost": "",
                 "rhn.proxyport": "",
                 "rhn.password": "",
                 "rhn.proxypassword": "",
                 }
        try:
            model["rhn.proxyhost"], \
                model["rhn.proxyport"] = cfg["proxy"].rsplit(":", 1)
        except:
            # We're passing because it can't assign multiple values, reassign
            # instead of passing
            model["rhn.proxyhost"] = cfg["proxy"] if cfg["proxy"] else ""
        return model

    def validators(self):
        return {"rhn.username": valid.Ascii(),
                "rhn.profilename": valid.Ascii() | valid.Empty(),
                "rhn.url": valid.Empty() | valid.URL(),
                "rhn.ca": valid.Empty() | valid.URL(),
                "rhn.proxyhost": (valid.FQDNOrIPAddress() |
                                  valid.URL() | valid.Empty()),
                "rhn.proxyport": valid.Port() | valid.Empty(),
                "rhn.proxyuser": valid.Text() | valid.Empty(),
                "rhn.org": valid.Text() | valid.Empty(),
                "rhn.environment": valid.Text() | valid.Empty(),
                "rhn.activation_key": valid.Text() | valid.Empty(),
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
                             "configure it before configuring RHSM"),
                   ui.Divider("notice.divider")])

        else:
            rhn_msg = ("RHSM Registration is required only if you wish " +
                       "to use Red Hat Enterprise Linux with virtual " +
                       "guests subscriptions for your guests.")

            if cfg["rhntype"] and self._get_status(cfg) is not None:
                rhn_msg = self._get_status(cfg)

            ws = [ui.Header("header[0]", rhn_msg),
                  ui.Entry("rhn.username", "Login:"),
                  ui.PasswordEntry("rhn.password", "Password:"),
                  ui.Entry("rhn.profilename", "Profile Name (optional):"),
                  ui.Divider("divider[0]"),
                  ui.Options("rhn.type", "Type", self._rhn_types),
                  ui.Entry("rhn.url", "URL:"),
                  ui.Entry("rhn.ca", "CA URL:"),
                  ui.Entry("rhn.org", "Organization:"),
                  ui.Entry("rhn.environment", "Environment:"),
                  ui.Entry("rhn.activation_key", "Activation Key:"),
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
                    self.widgets["rhn.environment"].enabled(True)
                    self.widgets["rhn.activation_key"].enabled(True)
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
        self.logger.debug("Saving RHSM page")
        changes = Changeset(self.pending_changes(False))
        effective_model = Changeset(self.model())
        effective_model.update(effective_changes)

        self.logger.debug("Changes: %s" % changes)
        self.logger.debug("Effective Model: %s" % effective_model)

        rhn_keys = ["rhn.username", "rhn.password", "rhn.profilename",
                    "rhn.type", "rhn.url", "rhn.ca", "rhn.proxyhost",
                    "rhn.proxyport", "rhn.proxyuser", "rhn.proxypassword",
                    "rhn.org", "rhn.environment", "rhn.activation_key"]

        if "button.proxy" in changes:
            description = ("Please enter the proxy details to use " +
                           "for contacting the management server ")
            self._dialog = ProxyDialog("Input proxy information",
                                       description, self)
            self.widgets.add(self._dialog)
            return self._dialog

        if "rhn.activation_key" in changes and "rhn.username" in changes:
            return ui.InfoDialog("dialog.error", "Conflicting Inputs",
                                 "Username and activationkey cannot be used "
                                 "simultaneously. Please clear one of the "
                                 "values")

        elif "rhn.activation_key" not in effective_model and \
                ("rhn.username" not in effective_model and
                 "rhn.password" not in effective_model):
            return ui.InfoDialog("dialog.error", "Conflicting Inputs",
                                 "Username or activationkey must be set."
                                 "Please set one of the values.")

        txs = utils.Transaction("Updating RHSM configuration")

        if changes.contains_any(rhn_keys):
            def update_proxy():
                vals = [effective_model["rhn.proxyhost"],
                        effective_model["rhn.proxyport"]]
                proxy_str = "%s:%s" % (vals[0], vals[1]) if vals[1] else \
                            "%s" % vals[0]
                return proxy_str
                effective_model["rhn.proxy"] = proxy_str

            self.logger.debug(changes)
            self.logger.debug(effective_model)

            effective_model["rhn.type"] = effective_model["rhn.type"] or "rhn"
            effective_model["rhn.proxy"] = update_proxy() if \
                effective_model["rhn.proxyhost"] else ""

            rhn_keys = ["rhn.type", "rhn.url", "rhn.ca", "rhn.username",
                        "rhn.profilename", "rhn.activation_key", "rhn.org",
                        "rhn.environment", "rhn.proxy", "rhn.proxyuser"]

            pw = effective_model["rhn.password"]
            proxypassword = effective_model["rhn.proxypassword"]

            warning_text = None

            rhn_type = effective_model["rhn.type"]
            if rhn_type == "sam" or rhn_type == "satellite":
                if not effective_model["rhn.url"] and not \
                        effective_model["rhn.ca"]:
                    warning_text = "URL and CA path "
                elif not effective_model["rhn.ca"]:
                    warning_text = "CA path "

            if warning_text:
                txt = "%s must not be empty!" % warning_text
                self._error_dialog = ui.InfoDialog("dialog.error",
                                                   "RHSM Error",
                                                   txt)
                return self._error_dialog
            else:
                model = rhn_model.RHN()
                model.clear()

                model.update(*effective_model.values_for(rhn_keys))
                txs += model.transaction(password=pw,
                                         proxypass=proxypassword)

                progress_dialog = ui.TransactionProgressDialog("dialog.txs",
                                                               txs, self)
                progress_dialog.run()
        return self.ui_content()

    def _get_status(self, cfg):
        rhn_msg = None
        if "satellite" in cfg["rhntype"]:
            rhntype = cfg["rhntype"].title()
        elif "rhn" in cfg["rhntype"]:
            rhntype = "RHSM"
        else:
            rhntype = cfg["rhntype"].upper()

        try:
            cmd = ["subscription-manager", "status"]
            output = process.check_output(cmd)
            if "Status: Unknown" not in output:
                rhn_msg = "RHSM Registration\n\nRegistration Status: %s" \
                          % rhntype

        except process.CalledProcessError as e:
            if "Status: Unknown" in e.output:
                # Not registered or registration failed
                pass
            else:
                rhn_msg = ("Registered to %s, but there are no "
                           "subscriptions attached or it is otherwise"
                           " invalid" % rhntype)

        return rhn_msg


class ProxyDialog(ui.Dialog):
    """A dialog to input proxy information
    """

    def __init__(self, title, description, plugin):
        self.keys = ["rhn.proxyhost", "rhn.proxyport", "rhn.proxyuser",
                     "rhn.proxypassword"]

        def clear_invalid(dialog, changes):
            [plugin.stash_change(prefix) for prefix in self.keys]

        title = _("RHSM Proxy Information")

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
