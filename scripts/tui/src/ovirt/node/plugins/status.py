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
        return 10

    def model(self):
        if not self._model:
            self._model = {
                "status.networking": "On",
                "status.logs": "Local",
                "status.vms.running": "42",
            }
        return self._model

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        aligned = lambda l: l.ljust(16)
        widgets = [
            ("status.networking",
                ovirt.node.ui.KeywordLabel(aligned("Networking: "))),
            ("status.logs",
                ovirt.node.ui.KeywordLabel(aligned("Logs: "))),
            ("status.vms.running",
                ovirt.node.ui.KeywordLabel(aligned("Running VMs: "))),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        page.has_save_button = False
        return page
