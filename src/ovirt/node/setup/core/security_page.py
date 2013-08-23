#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# security_page.py - Copyright (C) 2012 Red Hat, Inc.
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
from ovirt.node import utils, plugins, ui, valid
from ovirt.node.config import defaults
from ovirt.node.plugins import Changeset

"""
Configure Security
"""


class Plugin(plugins.NodePlugin):
    _model = {}

    def name(self):
        return _("Security")

    def rank(self):
        return 20

    def model(self):
        cfg = defaults.SSH().retrieve()
        self.logger.debug(cfg)
        model = {
            "ssh.pwauth": cfg["pwauth"] or False,
            "strongrng.disable_aesni": cfg["disable_aesni"] or False,
            "strongrng.num_bytes": cfg["num_bytes"] or "",
            "passwd.admin.password": "",
        }
        return model

    def validators(self):
        number_or_empty = valid.Number(bounds=[0, None]) | \
            valid.Empty()
        return {"strongrng.num_bytes": number_or_empty,
                "passwd.admin.password":
                valid.Empty() | valid.Text(min_length=5)
                }

    def ui_content(self):
        ws = [ui.Header("header[0]", _("Remote Access")),
              ui.Checkbox("ssh.pwauth",
                          _("Enable SSH password authentication")),
              ui.Header("header[1]", _("Strong Random Number Generator")),
              ui.Checkbox("strongrng.disable_aesni", _("Disable AES-NI")),
              ui.Entry("strongrng.num_bytes", _("Bytes Used:")),
              ui.Header("header[2]", _("Password for the admin user")),
              ui.ConfirmedEntry("passwd.admin.password", _("Password:"),
                                is_password=True)
              ]

        page = ui.Page("page", ws)
        self.widgets.add(page)
        return page

    def on_change(self, changes):
        if changes.contains_any(["strongrng.disable_aesni"]):
            self._model.update(changes)
            model = self._model
            disable_aesni = model.get("strongrng.disable_aesni", "")
            if disable_aesni:
                self.widgets["strongrng.num_bytes"].enabled(False)
            else:
                self.widgets["strongrng.num_bytes"].enabled(True)

        if changes.contains_any(["passwd.admin.password"]):
            self._model.update(changes)
            model = self._model

    def on_merge(self, effective_changes):
        self.logger.debug("Saving security page")
        changes = Changeset(self.pending_changes(False))
        effective_model = Changeset(self.model())
        effective_model.update(effective_changes)

        self.logger.debug("Changes: %s" % changes)
        self.logger.debug("Effective Model: %s" % effective_model)

        ssh_keys = ["ssh.pwauth", "strongrng.num_bytes",
                    "strongrng.disable_aesni"]

        txs = utils.Transaction(_("Updating security configuration"))

        if changes.contains_any(ssh_keys):
            model = defaults.SSH()
            model.update(*effective_model.values_for(ssh_keys))
            txs += model.transaction()

        if changes.contains_any(["passwd.admin.password"]):
            pw = effective_model["passwd.admin.password"]
            passwd = utils.security.Passwd()

            # Create a custom transaction element, because the password
            # is not handled/saved in the defaults file
            class SetAdminPasswd(utils.Transaction.Element):
                title = _("Setting admin password")

                def commit(self):
                    self.logger.debug("Setting admin password.")
                    passwd.set_password("admin", pw)

            txs += [SetAdminPasswd()]

        progress_dialog = ui.TransactionProgressDialog("dialog.txs", txs, self)
        progress_dialog.run()

        return self.ui_content()
