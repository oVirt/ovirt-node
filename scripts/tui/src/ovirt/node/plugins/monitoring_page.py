#!/usr/bin/python
#
# monitoring_page.py - Copyright (C) 2012 Red Hat, Inc.
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
Configure Monitoring
"""
import logging

import ovirt.node.plugins
import ovirt.node.valid
import ovirt.node.ui

LOGGER = logging.getLogger(__name__)


class Plugin(ovirt.node.plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Monitoring"

    def rank(self):
        return 90

    def model(self):
        if not self._model:
            self._model = {
                "collectd.address": "",
                "collectd.port": "7634",
            }
        return self._model

    def validators(self):
        return {
                "collectd.address": ovirt.node.valid.FQDNOrIPAddress(),
                "collectd.port": ovirt.node.valid.Port(),
            }

    def ui_content(self):
        widgets = [
            ("header", ovirt.node.ui.Header("Monitoring Configuration")),

            ("label", ovirt.node.ui.Label("Collectd gathers statistics " +
                            "about the system and can be used to find " +
                            "performance bottlenecks and predict future " +
                            "system load.")),

            ("collectd.address", ovirt.node.ui.Entry("Server Address:")),
            ("collectd.port", ovirt.node.ui.Entry("Server Port:")),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        return page

    def on_change(self, changes):
        pass
        self._model.update(changes)

    def on_merge(self, effective_changes):
        pass
