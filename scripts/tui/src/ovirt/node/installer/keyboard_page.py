#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# keyboard_page.py - Copyright (C) 2013 Red Hat, Inc.
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
Keyboard page of the installer
"""
from ovirt.node import plugins, ui, utils


class Plugin(plugins.NodePlugin):
    _model = {}

    def name(self):
        return "Keyboard"

    def rank(self):
        return 10

    def model(self):
        return self._model

    def validators(self):
        return {}

    def ui_content(self):
        kbd = utils.Keyboard()
        c = kbd.get_current()
        self.logger.debug("Current layout: %s" % c)
        ws = [ui.Header("header[0]", "Keyboard Layout Selection"),
              ui.Table("keyboard.layout", "", "Available Keyboard Layouts",
                       kbd.available_layouts(), c),
              ui.Label("label[0]", "(Hit return to select a layout)")
              ]
        self.widgets.add(ws)
        page = ui.Page("keyboard", ws)
        page.buttons = [ui.QuitButton("button.quit", "Quit"),
                        ui.SaveButton("button.next", "Continue")]
        return page

    def on_change(self, changes):
        if "keyboard.layout" in changes:
            self._model.update(changes)

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        if changes.contains_any(["keyboard.layout", "button.next"]):
            # Apply kbd layout directly so it takes affect on the password page
            kbd = utils.Keyboard()
            self.dry_or(lambda: kbd.set_layout(changes["keyboard.layout"]))

            self.application.ui.navigate.to_next_plugin()
