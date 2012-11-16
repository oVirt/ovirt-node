#!/usr/bin/python
#
# snmp_page.py - Copyright (C) 2012 Red Hat, Inc.
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
Configure SNMP
"""

import ovirt.node.plugins
import ovirt.node.valid
import ovirt.node.ui


class Plugin(ovirt.node.plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "SNMP"

    def rank(self):
        return 40

    def model(self):
        if not self._model:
            self._model = {
                "snmp.enabled": "no",
                "snmp.password": "",
                "snmp.password_confirmation": "",
            }
        return self._model

    def validators(self):
        return {
                "passwd.admin.password": ovirt.node.valid.Text(),
                "passwd.admin.password_confirmation": ovirt.node.valid.Text(),
            }

    def ui_content(self):
        widgets = [
            ("snmp._header", ovirt.node.ui.Header("SNMP")),
            ("snmp.enabled", ovirt.node.ui.Options("Enable SNMP",
                [("yes", "Yes"), ("no", "No")])),
            ("ssh._divider", ovirt.node.ui.Divider()),


            ("snmp.password._header", ovirt.node.ui.Header("SNMP Password")),
            ("snmp.password", ovirt.node.ui.PasswordEntry("Password:")),
            ("snmp.password_confirmation", ovirt.node.ui.PasswordEntry(
                "Confirm Password:")),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        return page

    def on_change(self, changes):
        self._model.update(changes)

        if self._model["snmp.password"] != \
           self._model["snmp.password_confirmation"]:
            raise ovirt.node.exceptions.InvalidData("Passwords do not match.")

    def on_merge(self, effective_changes):
        pass
