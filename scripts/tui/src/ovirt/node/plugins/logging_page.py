#!/usr/bin/python
#
# logging.py - Copyright (C) 2012 Red Hat, Inc.
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
Configure Logging
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
        return "Logging"

    def rank(self):
        return 50

    def model(self):
        if not self._model:
            self._model = {
                # The target address
                "max_log_size": "1024",
                "rsyslog.address": "",
                "rsyslog.port": "514",
                "netconsole.address": "",
                "netconsole.port": "6666",
            }
        return self._model

    def validators(self):
        """Validators validate the input on change and give UI feedback
        """
        return {
                "max_log_size": ovirt.node.valid.Number(min=0),
                "rsyslog.address": ovirt.node.valid.FQDNOrIPAddress(),
                "rsyslog.port": ovirt.node.valid.Port(),
                "netconsole.address": ovirt.node.valid.FQDNOrIPAddress(),
                "netconsole.port": ovirt.node.valid.Port(),
            }

    def ui_content(self):
        widgets = [
            ("header", ovirt.node.ui.Header("Logging")),

            ("max_log_size", ovirt.node.ui.Entry("Logrotate Max Log " +
                                                 "Size (KB)")),

            ("rsyslog.header", ovirt.node.ui.Label(
                                    "RSyslog is an enhanced multi-threaded " +
                                    "syslogd")),
            ("rsyslog.address", ovirt.node.ui.Entry("Server Address")),
            ("rsyslog.port", ovirt.node.ui.Entry("Server Port")),

            ("netconsole.header", ovirt.node.ui.Label(
                                    "Netconsole service allows a remote sys" +
                                    "log daemon to record printk() messages")),
            ("netconsole.address", ovirt.node.ui.Entry("Server Address")),
            ("netconsole.port", ovirt.node.ui.Entry("Server Port")),
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
