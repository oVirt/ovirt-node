#!/usr/bin/python
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
import logging

import ovirt.node.plugins
import ovirt.node.valid
import ovirt.node.ui
import ovirt.node.utils

LOGGER = logging.getLogger(__name__)


class Plugin(ovirt.node.plugins.NodePlugin):
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
                "vdsm.connect_and_validate": ovirt.node.utils.parse_bool(True),
                "vdsm.password": "",
                "vdsm.password_confirmation": "",
            }
        return self._model

    def validators(self):
        return {
                "vdsm.address": ovirt.node.valid.FQDNOrIPAddress(),
                "vdsm.port": ovirt.node.valid.Port(),
                "vdsm.password": ovirt.node.valid.Text(),
                "vdsm.password_confirmation": ovirt.node.valid.Text(),
            }

    def ui_content(self):
        widgets = [
            ("header", ovirt.node.ui.Header("oVirt Engine Configuration")),

            ("vdsm.address", ovirt.node.ui.Entry("Server Address:")),
            ("vdsm.port", ovirt.node.ui.Entry("Server Port:")),
            ("vdsm.connect_and_validate", ovirt.node.ui.Checkbox(
                    "Connect to oVirt Engine and Validate Certificate")),

            ("vdsm.password._divider", ovirt.node.ui.Divider("-")),
            ("vdsm.password._label", ovirt.node.ui.Label(
                    "Optional password for adding Node through oVirt " +
                    "Engine UI")),

            ("vdsm.password", ovirt.node.ui.PasswordEntry("Password:")),
            ("vdsm.password_confirmation", ovirt.node.ui.PasswordEntry(
                    "Confirm Password:")),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        return page

    def on_change(self, changes):
        self._model.update(changes)

        if self._model["vdsm.password"] != \
           self._model["vdsm.password_confirmation"]:
            raise ovirt.node.exceptions.InvalidData("Passwords do not match.")

    def on_merge(self, effective_changes):
        pass
