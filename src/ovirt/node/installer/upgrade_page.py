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
from ovirt.node import plugins, ui, installer, exceptions
from ovirt.node.utils import security

"""
Password confirmation page for the upgarde part of the installer
"""


class Plugin(plugins.NodePlugin):
    _model = {}

    __no_new_password_msg = "You have not provided a new password, " \
        "current admin password will be used."

    def name(self):
        return "Upgrade Password"

    def rank(self):
        return 150

    def model(self):
        return self._model or {}

    def validators(self):
        return {}

    def ui_content(self):
        ws = [ui.Header("header[0]",
                        "Require a password for local console access?"),
              ui.Label("label[0]", "Please enter the current admin " +
                       "password. You may also change the admin password " +
                       "if required. If the new password fields are left" +
                       "blank the password will remain the same."),
              ui.Label("label[1]", "Password for local console access"),
              ui.Divider("divider[0]"),
              ui.PasswordEntry("upgrade.current_password",
                               "Current Password:"),
              ui.Divider("divider[1]"),
              ui.PasswordEntry("upgrade.password", "Password:"),
              ui.PasswordEntry("upgrade.password_confirmation",
                               "Confirm Password:"),
              ui.Divider("divider[2]"),
              ui.Label("current_password.info", ""),
              ui.Label("password.info", self.__no_new_password_msg)
              ]
        self.widgets.add(ws)
        page = ui.Page("password", ws)
        page.buttons = [ui.QuitButton("button.quit", "Quit"),
                        ui.Button("button.back", "Back"),
                        ui.SaveButton("button.next", "Update")]
        return page

    def on_change(self, changes):
        if changes.contains_any(["upgrade.password",
                                 "upgrade.password_confirmation"]):
            self._model.update(changes)
            up_pw, up_pw_conf = self._model.get("upgrade.password", ""), \
                self._model.get("upgrade.password_confirmation", "")

            if up_pw != up_pw_conf:
                self.widgets["password.info"].text("")
                raise exceptions.InvalidData("Passwords must be the same.")
            else:
                self.widgets["upgrade.password"].valid(True)
                self.widgets["upgrade.password_confirmation"].valid(True)
                self.widgets["password.info"].text("")

                if not up_pw and not up_pw_conf:
                    msg = self.__no_new_password_msg
                    self.widgets["password.info"].text(msg)

        if changes.contains_any(["upgrade.current_password"]):
            # Hide any message which was shown
            self.widgets["current_password.info"].text("")

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        if changes.contains_any(["button.back"]):
            self.application.ui.navigate.to_previous_plugin()
            return

        if changes.contains_any(["upgrade.current_password",
                                 "button.next"]):
            pam = security.PAM()
            # We can't use os.getlogin() here, b/c upgrade happens during boot
            # w/o login
            username = "admin"
            if pam.authenticate(username, changes["upgrade.current_password"]):
                nav = self.application.ui.navigate
                nav.to_plugin(installer.progress_page.Plugin)
            else:
                msg = "Current password is invalid"
                self.widgets["current_password.info"].text(msg)
