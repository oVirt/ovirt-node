#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# password_page.py - Copyright (C) 2013 Red Hat, Inc.
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
Password page of the installer
"""
from ovirt.node import plugins, ui


class Plugin(plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Console Password"

    def rank(self):
        return 50

    def model(self):
        return self._model or {}

    def validators(self):
        return {}

    def ui_content(self):
        widgets = [
            ("layout._header",
             ui.Header("Require a password for local console access?")),

            ("divider[0]", ui.Divider()),
            ("root.password", ui.PasswordEntry("Password:")),
            ("root.password_confirmation",
             ui.PasswordEntry("Confirm Password:")),
        ]
        self._widgets = dict(widgets)
        page = ui.Page(widgets)
        page.buttons = [("button.quit", ui.Button("Quit")),
                        ("button.back", ui.Button("Back")),
                        ("button.next", ui.Button("Install"))]
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        if changes.contains_any(["root.password_confirmation", "button.next"]):
            self.transaction = "a"
            self.application.ui.navigate.to_next_plugin()
