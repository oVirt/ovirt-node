#!/usr/bin/python
#
# status.py - Copyright (C) 2012 Red Hat, Inc.
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
Status plugin
"""
import logging

import ovirt.node.plugins
import ovirt.node.valid
import ovirt.node.ui
import ovirt.node.utils

LOGGER = logging.getLogger(__name__)


class Plugin(ovirt.node.plugins.NodePlugin):
    """This is the summary page, summarizing all sorts of informations

    There are no validators, as there is no input.
    """

    _model = None
    _widgets = None

    def name(self):
        return "Status"

    def rank(self):
        return 0

    def model(self):
        if not self._model:
            self._model = {
                "status": "Virtualization hardware was not detected",
                "networking": "On",
                "networking.bridge": "breth0: 192.168.122.1",
                "logs": "Local Only",
                "libvirt.num_guests": "42",
            }
        return self._model

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        # Function to expand all "keywords" to the same length
        aligned = lambda l: l.ljust(16)

        # Network related widgets, appearing in one row
        network_widgets = [
                ("networking",
                    ovirt.node.ui.KeywordLabel(aligned("Networking: "))),
                ("networking.bridge",
                    ovirt.node.ui.Label("N/A")),
            ]
        widgets = [
            ("status",
                ovirt.node.ui.KeywordLabel(aligned("Status: "))),
            ("status._space", ovirt.node.ui.Divider()),

            ("network._column", ovirt.node.ui.Row(network_widgets)),
            ("network._space", ovirt.node.ui.Divider()),

            ("logs",
                ovirt.node.ui.KeywordLabel(aligned("Logs: "))),
            ("logs._space", ovirt.node.ui.Divider()),

            ("libvirt.num_guests",
                ovirt.node.ui.KeywordLabel(aligned("Running VMs: "))),
            ("libvirt._space", ovirt.node.ui.Divider()),

            ("support.hint", ovirt.node.ui.Label("Press F8 for support menu")),
            ("support._space", ovirt.node.ui.Divider()),

            ("action.hostkey", ovirt.node.ui.Button("View Host Key")),
#            ("action", ovirt.node.ui.Buttons(["Lock", "Log Off", "Restart",
#                                              "Power Off"])),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        page.has_save_button = False
        return page
