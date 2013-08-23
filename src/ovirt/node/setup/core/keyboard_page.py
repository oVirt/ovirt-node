#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# keyboard_page.py - Copyright (C) 2012 Red Hat, Inc.
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
"""
Configure Keyboard Layout
"""

from ovirt.node import plugins, ui, utils
from ovirt.node.config import defaults
from ovirt.node.plugins import Changeset


class Plugin(plugins.NodePlugin):
    _model = None

    def name(self):
        return _("Keyboard")

    def rank(self):
        return 30

    def model(self):
        cfg = defaults.Keyboard().retrieve()
        kbd = utils.system.Keyboard()
        model = {}
        model["keyboard.layout"] = cfg["layout"] or ""
        model["keyboard.layout_name"] = kbd.get_current_name() or "None"
        return model

    def validators(self):
        return {}

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        kbd = utils.system.Keyboard()
        ws = [ui.Header("header", _("Keyboard Layout Selection")),
              ui.Label("label", _("Choose the Keyboard Layout you would ") +
                       _("like to apply to this system.")),
              ui.Divider("divider[0]"),
              ui.KeywordLabel("keyboard.layout_name", _("Current Active ") +
                              _("Keyboard Layout:  ")),
              ui.Table("keyboard.layout", "", _("Available Keyboard Layouts"),
                       kbd.available_layouts(), kbd.get_current()),
              ]

        page = ui.Page("page", ws)
        page.buttons = [ui.SaveButton("page.save", _("Save"))]
        self.widgets.add(page)
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        self.logger.debug("Saving keyboard page")
        changes = Changeset(self.pending_changes(False))
        effective_model = Changeset(self.model())
        effective_model.update(effective_changes)

        self.logger.debug("Changes: %s" % changes)
        self.logger.debug("Effective Model: %s" % effective_model)

        layout_keys = ["keyboard.layout"]

        txs = utils.Transaction(_("Updating keyboard related configuration"))

        if changes.contains_any(layout_keys):
            model = defaults.Keyboard()
            model.update(*effective_model.values_for(layout_keys))
            txs += model.transaction()

        progress_dialog = ui.TransactionProgressDialog("dialog.txs", txs, self)
        progress_dialog.run()

        return self.ui_content()
