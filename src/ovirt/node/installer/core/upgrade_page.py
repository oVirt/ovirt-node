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
from ovirt.node import plugins, ui
from ovirt.node.utils import security
import keyboard_page
import progress_page

"""
Password confirmation page for the upgarde part of the installer
"""


class Plugin(plugins.NodePlugin):
    _model = {}

    __no_new_password_msg = "You have not provided a new password, " \
        "current admin password will be used."

    def name(self):
        return _("Upgrade Password")

    def rank(self):
        return 150

    def model(self):
        return self._model or {}

    def validators(self):
        return {}

    def ui_content(self):
        ws = [ui.Header("header[0]",
                        _("Require a password for the admin user?")),
              ui.Label("label[0]", _("Please enter the current admin ") +
                       _("password. You may also change the admin password ") +
                       _("if required. If the new password fields are left ") +
                       _("blank the password will remain the same.")),
              ui.Label("label[1]", _("Password for the admin user")),
              ui.Divider("divider[0]"),
              ui.PasswordEntry("upgrade.current_password",
                               _("Current Password:")),
              ui.Divider("divider[1]"),
              ui.ConfirmedEntry("upgrade.password", _("Password:"),
                                is_password=True),
              ui.Notice("current_password.info", ""),
              ui.Label("password.info", self.__no_new_password_msg)
              ]
        page = ui.Page("password", ws)
        page.buttons = [ui.QuitButton("button.quit", "Quit"),
                        ui.Button("button.back", "Back"),
                        ui.SaveButton("button.next", "Update")]
        self.widgets.add(page)
        return page

    def on_change(self, changes):
        if changes.contains_any(["upgrade.password"]):
            self._model.update(changes)
            up_pw = self._model.get("upgrade.password", "")
            if up_pw:
                self.widgets["password.info"].text("")
            else:
                self.widgets["password.info"].text(self.__no_new_password_msg)

        if changes.contains_any(["upgrade.current_password"]):
            # Hide any message which was shown
            self.widgets["current_password.info"].text("")

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        if changes.contains_any(["button.back"]):
            nav = self.application.ui.navigate
            nav.to_plugin(keyboard_page.Plugin)
            return

        if changes.contains_any(["upgrade.current_password",
                                 "button.next"]):
            self._model.update(effective_changes)
            pam = security.PAM()
            # We can't use os.getlogin() here, b/c upgrade happens during boot
            # w/o login
            username = "admin"
            if pam.authenticate(username, changes["upgrade.current_password"]):
                nav = self.application.ui.navigate
                nav.to_plugin(progress_page.Plugin)
            else:
                msg = "Current password is invalid"
                self.widgets["current_password.info"].text(msg)
