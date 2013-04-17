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
from ovirt.node import plugins, ui, exceptions

"""
Password page of the installer
"""


class Plugin(plugins.NodePlugin):
    _model = {}

    def name(self):
        return "Console Password"

    def rank(self):
        return 50

    def model(self):
        return self._model or {}

    def validators(self):
        return {}

    def ui_content(self):
        ws = [ui.Header("header[0]",
                        "Require a password for local console access?"),
              ui.Divider("divider[0]"),
              ui.PasswordEntry("root.password", "Password:"),
              ui.PasswordEntry("root.password_confirmation",
                               "Confirm Password:"),
              ]
        self.widgets.add(ws)
        page = ui.Page("password", ws)
        page.buttons = [ui.QuitButton("button.quit", "Quit"),
                        ui.Button("button.back", "Back"),
                        ui.SaveButton("button.next", "Install")]
        return page

    def on_change(self, changes):
        if changes.contains_any(["root.password",
                                 "root.password_confirmation"]):
            self._model.update(changes)
            root_pw, root_pw_conf = self._model.get("root.password", ""), \
                self._model.get("root.password_confirmation", "")

            if root_pw != root_pw_conf:
                raise exceptions.InvalidData("Passwords must be the same.")
            else:
                self.widgets["root.password"].valid(True)
                self.widgets["root.password_confirmation"].valid(True)

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        if changes.contains_any(["button.back"]):
            self.application.ui.navigate.to_previous_plugin()
        elif changes.contains_any(["root.password_confirmation",
                                   "button.next"]):
            self.application.ui.navigate.to_next_plugin()
