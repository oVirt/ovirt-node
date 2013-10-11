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
from ovirt.node.plugins import Changeset


class Plugin(plugins.NodePlugin):
    _model = None

    def name(self):
        return _("Logging")

    def rank(self):
        return 50

    def model(self):
        logrotate = defaults.Logrotate().retrieve()
        netconsole = defaults.Netconsole().retrieve()
        syslog = defaults.Syslog().retrieve()

        model = {}
        model["logrotate.max_size"] = logrotate["max_size"] or "1024"

        model["rsyslog.address"] = syslog["server"] or ""
        model["rsyslog.port"] = syslog["port"] or "514"

        model["netconsole.address"] = netconsole["server"] or ""
        model["netconsole.port"] = netconsole["port"] or "6666"

        return model

    def validators(self):
        """Validators validate the input on change and give UI feedback
        """
        return {"logrotate.max_size": valid.Number(bounds=[0, None]),
                "rsyslog.address": (valid.Empty() | valid.FQDNOrIPAddress()),
                "rsyslog.port": valid.Port(),
                "netconsole.address": (valid.Empty() |
                                       valid.FQDNOrIPAddress(
                                           allow_ipv6=False)),
                "netconsole.port": valid.Port(),
                }

    def ui_content(self):

        ws = [ui.Header("header[0]", _("Logging")),
              ui.Entry("logrotate.max_size", _("Logrotate Max Log ") +
                       _("Size (KB):")),
              ui.Divider("divider[0]")
              ]

        net_is_configured = utils.network.NodeNetwork().is_configured()

        if not net_is_configured:
            ws.extend([ui.Notice("network.notice",
                                 _("Networking is not configured, ") +
                                 _("please configure it before rsyslog ") +
                                 _("and/or netconsole")),
                       ui.Divider("notice.divider")])

        ws.extend([ui.Label("rsyslog.header",
                            _("RSyslog is an enhanced multi-") +
                            _("threaded syslogd")),
                   ui.Entry("rsyslog.address", _("Server Address:"),
                            enabled=net_is_configured),
                   ui.Entry("rsyslog.port", _("Server Port:"),
                            enabled=net_is_configured),
                   ui.Divider("divider[1]"),
                   ui.Label("netconsole.label",
                            _("Netconsole service allows a remote sys") +
                            _("log daemon to record printk() messages")),
                   ui.Entry("netconsole.address", _("Server Address:"),
                            enabled=net_is_configured),
                   ui.Entry("netconsole.port", _("Server Port:"),
                            enabled=net_is_configured)
                   ])

        page = ui.Page("page", ws)
        self.widgets.add(page)
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        self.logger.debug("Saving logging page")
        changes = Changeset(self.pending_changes(False))
        effective_model = Changeset(self.model())
        effective_model.update(effective_changes)

        self.logger.debug("Changes: %s" % changes)
        self.logger.debug("Effective Model: %s" % effective_model)

        txs = utils.Transaction(_("Updating logging related configuration"))

        # If any logrotate key changed ...
        logrotate_keys = ["logrotate.max_size"]
        if changes.contains_any(logrotate_keys):
            # Get all logrotate values fomr the effective model
            model = defaults.Logrotate()
            # And update the defaults
            model.update(*effective_model.values_for(logrotate_keys))
            txs += model.transaction()

        rsyslog_keys = ["rsyslog.address", "rsyslog.port"]
        if changes.contains_any(rsyslog_keys):
            model = defaults.Syslog()
            model.update(*effective_model.values_for(rsyslog_keys))
            txs += model.transaction()

        netconsole_keys = ["netconsole.address", "netconsole.port"]
        if changes.contains_any(netconsole_keys):
            model = defaults.Netconsole()
            model.update(*effective_model.values_for(netconsole_keys))
            txs += model.transaction()

        progress_dialog = ui.TransactionProgressDialog("dialog.txs", txs, self)
        progress_dialog.run()
