#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# logging_page.py - Copyright (C) 2012 Red Hat, Inc.
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

from ovirt.node import plugins, valid, ui, utils
from ovirt.node.config import defaults
from ovirt.node.plugins import ChangesHelper


class Plugin(plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Logging"

    def rank(self):
        return 50

    def model(self):
        logrotate = dict(defaults.Logrotate().retrieve())
        netconsole = dict(defaults.Netconsole().retrieve())
        syslog = dict(defaults.Syslog().retrieve())

        model = {
            "logrotate.max_size": "1024",
            "rsyslog.address": "",
            "rsyslog.port": "514",
            "netconsole.address": "",
            "netconsole.port": "6666",
        }
        model["logrotate.max_size"] = logrotate["max_size"] or "1024"

        model["rsyslog.address"] = syslog["server"] or ""
        model["rsyslog.port"] = syslog["port"] or ""

        model["netconsole.address"] = netconsole["server"] or ""
        model["netconsole.port"] = netconsole["port"] or ""

        return model

    def validators(self):
        """Validators validate the input on change and give UI feedback
        """
        return {
                "logrotate.max_size": valid.Number(range=[0, None]),
                "rsyslog.address": valid.FQDNOrIPAddress(),
                "rsyslog.port": valid.Port(),
                "netconsole.address": valid.FQDNOrIPAddress(),
                "netconsole.port": valid.Port(),
            }

    def ui_content(self):
        widgets = [
            ("header", ui.Header("Logging")),

            ("logrotate.max_size", ui.Entry("Logrotate Max Log " +
                                                 "Size (KB):")),

            ("rsyslog.header", ui.Label(
                                    "RSyslog is an enhanced multi-threaded " +
                                    "syslogd")),
            ("rsyslog.address", ui.Entry("Server Address:")),
            ("rsyslog.port", ui.Entry("Server Port:")),

            ("netconsole.header", ui.Label(
                                    "Netconsole service allows a remote sys" +
                                    "log daemon to record printk() messages")),
            ("netconsole.address", ui.Entry("Server Address:")),
            ("netconsole.port", ui.Entry("Server Port:")),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ui.Page(widgets)
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        self.logger.debug("Saving logging page")
        changes = ChangesHelper(self.pending_changes(False))
        model = self.model()
        model.update(effective_changes)
        effective_model = ChangesHelper(model)

        self.logger.debug("Saving logging page: %s" % changes.changes)
        self.logger.debug("Logging page model: %s" % effective_model.changes)

        logrotate_keys = ["logrotate.max_size"]
        rsyslog_keys = ["rsyslog.address", "rsyslog.port"]
        netconsole_keys = ["netconsole.address", "netconsole.port"]

        txs = utils.Transaction("Updating logging related configuration")

        # If any logrotate key changed ...
        if changes.any_key_in_change(logrotate_keys):
            # Get all logrotate values fomr the effective model
            model = defaults.Logrotate()
            # And update the defaults
            model.update(*effective_model.get_key_values(logrotate_keys))
            txs += model.transaction()

        if changes.any_key_in_change(rsyslog_keys):
            model = defaults.Syslog()
            model.update(*effective_model.get_key_values(rsyslog_keys))
            txs += model.transaction()

        if changes.any_key_in_change(netconsole_keys):
            model = defaults.Netconsole()
            model.update(*effective_model.get_key_values(netconsole_keys))
            txs += model.transaction()

        txs.prepare()  # Just to display something in dry mode
        self.dry_or(lambda: txs())
