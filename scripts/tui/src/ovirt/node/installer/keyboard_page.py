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
    _elements = None

    def name(self):
        return "Keyboard"

    def rank(self):
        return 20

    def model(self):
        return self._model or {}

    def validators(self):
        return {}

    def ui_content(self):
        kbd = utils.Keyboard()
        ws = [ui.Header("header[0]", "Keyboard Layout Selection"),
              ui.Table("keyboard.layout", "Available Keyboard Layouts",
                       "", kbd.available_layouts()),
              ]
        self.widgets.add(ws)
        page = ui.Page("keyboard", ws)
        page.buttons = [ui.Button("button.quit", "Quit"),
                        ui.Button("button.next", "Continue")]
        return page

    def on_change(self, changes):
        if "keyboard.layout" in changes:
            self._model.update(changes)

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        if changes.contains_any(["keyboard.layout", "button.next"]):
            self.transaction = "a"
            self.application.ui.navigate.to_next_plugin()
