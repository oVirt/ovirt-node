#!/usr/bin/python
#
# example.py - Copyright (C) 2012 Red Hat, Inc.
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
Example plugin with TUI
"""
import ovirt.node.plugins
import ovirt.node.ui
import ovirt.node.exceptions
import ovirt.node.valid


class Plugin(ovirt.node.plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Example Page"

    def rank(self):
        return 999

    def model(self):
        """Returns the model of this plugin
        This is expected to parse files and all stuff to build up the model.
        """
        if not self._model:
            self._model = {
                "foo.hostname": "example.com",
                "foo.port": "8080",
                "foo.password": "secret",
            }
        return self._model

    def validators(self):
        nospace = lambda v: "No space allowed." if " " in v else None

        return {
                "foo.hostname": ovirt.node.valid.FQDN(),
                "foo.port": ovirt.node.valid.Port(),
                "foo.password": nospace
            }

    def has_ui(self):
        return False

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        widgets = [
            ("foo.section",
                ovirt.node.ui.Header("Subsection")),
            ("foo.hostname",
                ovirt.node.ui.Entry("Hostname:")),
            ("foo.port",
                ovirt.node.ui.Entry("Port:")),
            ("foo.password",
                ovirt.node.ui.PasswordEntry("Password:")),
        ]
        self._widgets = dict(widgets)
        page = ovirt.node.ui.Page(widgets)
        return page

    def on_change(self, changes):
        """Applies the changes to the plugins model, will do all required logic
        """
        self.logger.debug("checking %s" % changes)
        if "foo.hostname" in changes:
            self.logger.debug("Found foo.hostname")

            if "/" in changes["foo.hostname"]:
                raise ovirt.node.exceptions.InvalidData("No slash allowed")

            if len(changes["foo.hostname"]) < 5:
                raise ovirt.node.exceptions.Concern(
                                                "Should be at least 5 chars")

            self._model.update(changes)

            if "dis" in changes["foo.hostname"]:
                self._widgets["foo.port"].enabled(False)
                self.logger.debug("change to dis")
                self._widgets["foo.section"].text(changes["foo.hostname"])
                #raise ovirt.node.plugins.ContentRefreshRequest()
            else:
                self._widgets["foo.port"].enabled(True)

        if "foo.port" in changes:
            self.logger.debug("Found foo.port")

            if "/" in changes["foo.port"]:
                raise ovirt.node.exceptions.InvalidData("No slashes allowed")

        if "dialog.button" in changes:
            self.logger.debug("Request to close the dialog")
            self._widgets["dialog.dialog"].close()

        return True

    def on_merge(self, effective_changes):
        """Applies the changes to the plugins model, will do all required logic
        """
        self.logger.debug("saving %s" % effective_changes)
        # Look for conflicts etc
        self._model.update(effective_changes)

        dialog = self._create_dialog("Everything was saved.")

        return dialog

    def _create_dialog(self, txt):
        self.logger.debug("Building dialog")
        widgets = [
                ("dialog.text", ovirt.node.ui.Label(txt)),
                ("dialog.button", ovirt.node.ui.Button("Close"))
                ]
        page = ovirt.node.ui.Dialog("Information", widgets)
        page.has_save_button = False

        self._widgets.update(dict(widgets))
        self._widgets["dialog.dialog"] = page

        return page
