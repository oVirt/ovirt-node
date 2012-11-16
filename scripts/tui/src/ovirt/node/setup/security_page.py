#!/usr/bin/python
#
# security_page.py - Copyright (C) 2012 Red Hat, Inc.
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
Configure Security
"""

import ovirt.node.plugins
import ovirt.node.valid
import ovirt.node.ui


class Plugin(ovirt.node.plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Security"

    def rank(self):
        return 20

    def model(self):
        if not self._model:
            self._model = {
                "ssh.enabled": "no",
                "strongrng.enabled": "no",
                "strongrng.bytes_used": "",
                "passwd.admin.password": "",
                "passwd.admin.password_confirmation": "",
            }
        return self._model

    def validators(self):
        return {
                "stringrng.bytes_used": ovirt.node.valid.Number(min=0) | \
                                        ovirt.node.valid.Empty,
                "passwd.admin.password": ovirt.node.valid.Text(),
                "passwd.admin.password_confirmation": ovirt.node.valid.Text(),
            }

    def ui_content(self):
        widgets = [
            ("ssh.address", ovirt.node.ui.Header("Remote Access")),
            ("ssh.enabled", ovirt.node.ui.Options(
                "Enable ssh password authentication",
                [("yes", "Yes"), ("no", "No")])),
            ("ssh._divider", ovirt.node.ui.Divider()),

            ("strongrng._label", ovirt.node.ui.Header(
                                            "Strong Random Number Generator")),
            ("strongrng.enabled", ovirt.node.ui.Options(
                "Enable AES-NI",
                [("yes", "Yes"), ("no", "No")])),
            ("strongrng.num_bytes", ovirt.node.ui.Entry("Bytes Used:")),
            ("strongrng._divider", ovirt.node.ui.Divider()),


            ("passwd._label", ovirt.node.ui.Label("Local Access")),
            ("passwd.admin.password", ovirt.node.ui.PasswordEntry(
                                                                "Password:")),
            ("passwd.admin.password_confirmation", ovirt.node.ui.PasswordEntry(
                "Confirm Password:")),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        return page

    def on_change(self, changes):
        self._model.update(changes)

        if self._model["passwd.admin.password"] != \
           self._model["passwd.admin.password_confirmation"]:
            raise ovirt.node.exceptions.InvalidData("Passwords do not match.")

    def on_merge(self, effective_changes):
        pass
