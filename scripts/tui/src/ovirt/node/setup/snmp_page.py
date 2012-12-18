#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# snmp_page.py - Copyright (C) 2012 Red Hat, Inc.
# Written by Fabian Deutsch <fabiand@redhat.com>
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
from ovirt.node.config import defaults
from ovirt.node.plugins import Changeset

"""
Configure SNMP
"""


class Plugin(plugins.NodePlugin):
    _model = None
    _widgets = None

    def has_ui(self):
        # FIXME is SNMP in a plugin?
        return False

    def name(self):
        return "SNMP"

    def rank(self):
        return 40

    def model(self):
        cfg = defaults.SNMP().retrieve()
        self.logger.debug(cfg)
        model = {
            "snmp.enabled": True if cfg["password"] else False,
            "snmp.password": "",
            "snmp.password_confirmation": "",
        }
        return model

    def validators(self):
        same_as_password = plugins.Validator.SameAsIn(self,
                                                      "snmp.password",
                                                      "Password")
        return {
                "snmp.password": valid.Text(),
                "snmp.password_confirmation": same_as_password,
            }

    def ui_content(self):
        widgets = [
            ("header[0]", ui.Header("SNMP")),
            ("snmp.enabled", ui.Checkbox("Enable SNMP")),
            ("divider[0]", ui.Divider()),

            ("header[1]", ui.Header("SNMP Password")),
            ("snmp.password", ui.PasswordEntry("Password:")),
            ("snmp.password_confirmation",
             ui.PasswordEntry("Confirm Password:")),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ui.Page(widgets)
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        self.logger.debug("Saving SNMP page")
        changes = Changeset(self.pending_changes(False))
        effective_model = Changeset(self.model())
        effective_model.update(effective_changes)

        self.logger.debug("Changes: %s" % changes)
        self.logger.debug("Effective Model: %s" % effective_model)

        snmp_keys = ["snmp.password_confirmation", "snmp.enabled"]

        txs = utils.Transaction("Updating SNMP configuration")

        if changes.contains_any(snmp_keys):
            values = effective_model.values_for(snmp_keys)
            args = [values[0]]
            if values[1] is False:  # If set to disabled, set password to None
                args[0] = None
            model = defaults.SNMP()
            model.update(*args)
            txs += model.transaction()

        progress_dialog = ui.TransactionProgressDialog(txs, self)
        progress_dialog.run()
