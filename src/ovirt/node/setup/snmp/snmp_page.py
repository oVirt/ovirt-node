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
from ovirt.node import plugins, ui, utils
import snmp_model
from ovirt.node.plugins import Changeset
from ovirt.node.valid import RegexValidator

"""
Configure SNMP
"""


class SnmpPassword(RegexValidator):
    """A string, but without any space character and at least 8 chars

    >>> SnmpPassword().validate("1234567")
    False
    >>> SnmpPassword().validate("12345678")
    True
    >>> SnmpPassword().validate("123456 8")
    False
    >>> SnmpPassword().validate("Ab9873knad")
    True
    >>> SnmpPassword().validate("")
    False
    """

    description = "a string without spaces and at least 8 chars"
    pattern = "^\S{8,}$"


class Plugin(plugins.NodePlugin):
    _model = None

    def __init__(self, app):
        super(Plugin, self).__init__(app)
        self._model = {}

    def has_ui(self):
        return True

    def name(self):
        return "SNMP"

    def rank(self):
        return 40

    def model(self):
        cfg = snmp_model.SNMP().retrieve()
        self.logger.debug(cfg)
        model = {"snmp.enabled": cfg["enabled"] or False,
                 "snmp.password": "",
                 }
        return model

    def validators(self):
        return {"snmp.password": SnmpPassword()
                }

    def ui_content(self):
        ws = [ui.Header("header[0]", "SNMP"),
              ui.Checkbox("snmp.enabled", "Enable SNMP"),
              ui.Divider("divider[0]"),
              ui.Header("header[1]", "SNMP Password"),
              ui.ConfirmedEntry("snmp.password", "Password:",
                                is_password=True)
              ]

        page = ui.Page("page", ws)
        self.widgets.add(ws)
        return page

    def on_change(self, changes):
        if changes.contains_any(["snmp.password"]):
            self._model.update(changes)

    def on_merge(self, effective_changes):
        self.logger.debug("Saving SNMP page")
        changes = Changeset(self.pending_changes(False))
        effective_model = Changeset(self.model())
        effective_model.update(effective_changes)

        self.logger.debug("Changes: %s" % changes)
        self.logger.debug("Effective Model: %s" % effective_model)

        snmp_keys = ["snmp.password", "snmp.enabled"]

        txs = utils.Transaction("Updating SNMP configuration")

        if changes.contains_any(snmp_keys):
            is_enabled = effective_model["snmp.enabled"]
            pw = effective_model["snmp.password"]
            if is_enabled and len(pw) == 0:
                txt = "Unable to configure SNMP without a password!"
                self._confirm_dialog = ui.InfoDialog("dialog.confirm",
                                                     "SNMP Error",
                                                     txt)
                return self._confirm_dialog
            else:
                model = snmp_model.SNMP()
                model.update(is_enabled)
                txs += model.transaction(snmp_password=pw)
                progress_dialog = ui.TransactionProgressDialog("dialog.txs",
                                                               txs, self)
                progress_dialog.run()
        return self.ui_content()
