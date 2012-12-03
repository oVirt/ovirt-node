#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# engine_page.py - Copyright (C) 2012 Red Hat, Inc.
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
Configure Engine
"""

from ovirt.node import plugins, valid, ui, utils, exceptions


class Plugin(plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "oVirt Engine"

    def rank(self):
        return 100

    def model(self):
        if not self._model:
            self._model = {
                "vdsm.address": "",
                "vdsm.port": "7634",
                "vdsm.connect_and_validate": utils.parse_bool(True),
                "vdsm.password": "",
                "vdsm.password_confirmation": "",
            }
        return self._model

    def validators(self):
        return {
                "vdsm.address": valid.FQDNOrIPAddress() | valid.Empty(),
                "vdsm.port": valid.Port(),
                "vdsm.password": valid.Text(),
                "vdsm.password_confirmation": valid.Text(),
            }

    def ui_content(self):
        widgets = [
            ("header", ui.Header("oVirt Engine Configuration")),

            ("vdsm.address", ui.Entry("Management Server:")),
            ("vdsm.port", ui.Entry("Management Server Port:")),

            ("divider[1]", ui.Divider()),

            ("vdsm.connect_and_validate", ui.Checkbox(
                    "Connect to oVirt Engine and Validate Certificate")),

            ("divider[0]", ui.Divider()),
            ("vdsm.password._label", ui.Label(
                    "Optional password for adding Node through oVirt " +
                    "Engine UI")),

            ("vdsm.password", ui.PasswordEntry("Password:")),
            ("vdsm.password_confirmation",
             ui.PasswordEntry("Confirm Password:")),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ui.Page(widgets)
        return page

    def on_change(self, changes):
        self._model.update(changes)

        if self._model["vdsm.password"] != \
           self._model["vdsm.password_confirmation"]:
            raise exceptions.InvalidData("Passwords do not match.")

    def on_merge(self, effective_changes):
        pass
