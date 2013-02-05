#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# ping_page.py - Copyright (C) 2012 Red Hat, Inc.
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
A ping tool page
"""

from ovirt.node import plugins, valid, ui
from ovirt.node.utils import process


class Plugin(plugins.NodePlugin):
    _model = None

    def name(self):
        return "Networking/Ping"

    def rank(self):
        return 999

    def has_ui(self):
        return False

    def model(self):
        """Returns the model of this plugin
        This is expected to parse files and all stuff to build up the model.
        """
        if not self._model:
            self._model = {
                # The target address
                "ping.address": "127.0.0.1",
                "ping.count": "3",
                "ping.progress": "0",
                # The result field
                "ping.result": "",
            }
        return self._model

    def validators(self):
        """Validators validate the input on change and give UI feedback
        """
        # The address must be fqdn, ipv4 or ipv6 address
        return {"ping.address": valid.FQDNOrIPAddress(),
                "ping.count": valid.Number(bounds=[1, 20]),
                }

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        ws = [ui.Header("ping.header", "Ping a remote host"),
              ui.Entry("ping.address", "Address:"),
              ui.Entry("ping.count", "Count:"),
              ui.Divider("divider[1]"),
              ui.Button("ping.do_ping", "Ping"),
              ui.Divider("divider[2]"),
              ui.ProgressBar("ping.progress"),
              ui.Divider("divider[3]"),
              ui.Label("ping.result", "Result:"),
              ]

        page = ui.Page("page", ws)
        page.buttons = []
        self.widgets.add(page)
        return page

    def on_change(self, changes):
        """Applies the changes to the plugins model, will do all required logic
        """
        self.logger.debug("New (valid) address: %s" % changes)
        if "ping.address" in changes:
            self._model.update(changes)
        if "ping.count" in changes:
            self._model.update(changes)

    def on_merge(self, effective_changes):
        """Applies the changes to the plugins model, will do all required logic
        Normally on_merge is called by pushing the SaveButton instance, in this
        case it is called by on_change
        """

        if "ping.address" in self._model:
            addr = self._model["ping.address"]
            count = self._model["ping.count"]
            self.logger.debug("Pinging %s" % addr)

            cmd = "ping"
            if valid.IPv6Address().validate(addr):
                cmd = "ping6"

            cmd = "%s -c %s %s" % (cmd, count, addr)
            out = ""
            current = 0
            for line in process.pipe_async(cmd):
                out += line
                if "icmp_req" in line:
                    current += 100.0 / float(count)
                    self.widgets["ping.progress"].current(current)
                self.widgets["ping.result"].text("Result:\n\n%s" % out)
