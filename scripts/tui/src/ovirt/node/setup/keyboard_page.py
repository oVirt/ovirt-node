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
from ovirt.node.plugins import ChangesHelper


class Plugin(plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Keyboard"

    def rank(self):
        return 30

    def model(self):
        cfg = defaults.Keyboard().retrieve()
        self.logger.debug(cfg)
        model = {}
        model["keyboard.layout"] = cfg["layout"] or ""
        return model

    def validators(self):
        return {}

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        kbd = utils.Keyboard()
        widgets = [
            ("layout._header",
                ui.Header("Keyboard Layout Selection")),
            ("keyboard.layout", ui.Table("Available Keyboard Layouts",
                                "", kbd.available_layouts())),
        ]

        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ui.Page(widgets)
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        self.logger.debug("Saving keyboard page")
        changes = ChangesHelper(self.pending_changes(False))
        model = self.model()
        model.update(effective_changes)
        effective_model = ChangesHelper(model)

        self.logger.debug("Saving keyboard page: %s" % changes.changes)
        self.logger.debug("Keyboard page model: %s" % effective_model.changes)

        layout_keys = ["keyboard.layout"]

        txs = utils.Transaction("Updating keyboard related configuration")

        if changes.any_key_in_change(layout_keys):
            model = defaults.Keyboard()
            model.update(*effective_model.get_key_values(layout_keys))
            txs += model.transaction()

        txs.prepare()  # Just to display something in dry mode
        self.dry_or(lambda: txs())
