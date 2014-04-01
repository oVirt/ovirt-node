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
from ovirt.node import plugins, valid, ui
from ovirt.node.utils import process
import network_page
import threading


"""
A ping tool page
"""


class Plugin(plugins.NodePlugin):
    _model = None

    def name(self):
        return _("Networking/Ping")

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
        ws = [ui.Header("ping.header", _("Ping a remote host")),
              ui.Entry("ping.address", _("Address:")),
              ui.Entry("ping.count", _("Count:")),
              ui.Divider("divider[1]"),
              ui.Row("row[0]", [ui.SaveButton("ping.do_ping", _("Ping")),
                                ui.Button("ping.close", _("Close"))
                                ]
                     ),
              ui.Divider("divider[2]"),
              ui.Label("ping.result", _("Result:")),
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

        if "ping.close" in effective_changes:
            self.application.switch_to_plugin(
                network_page.Plugin)
            return
        elif "ping.address" in self._model:
            addr = self._model["ping.address"]
            count = self._model["ping.count"]
            self.logger.debug("Pinging %s" % addr)

            cmd = "ping"
            if valid.IPv6Address().validate(addr):
                cmd = "ping6"

            cmd = "%s -c %s %s" % (cmd, count, addr)

            ping = PingThread(self, cmd, count)
            ping.start()


class PingThread(threading.Thread):
    def __init__(self, plugin, cmd, count):
        self.p = plugin
        self.cmd = cmd
        self.count = count
        super(PingThread, self).__init__()

    def run(self):
        try:
            ui_thread = self.p.application.ui.thread_connection()
            stdoutdump = self.p.widgets["ping.result"]

            self.p.widgets["ping.do_ping"].enabled(False)
            ui_thread.call(lambda: stdoutdump.text("Pinging ..."))
            out = process.pipe(self.cmd, shell=True)
            ui_thread.call(lambda: stdoutdump.text(out))
        except:
            self.p.logger.exception("Exception while pinging")
        finally:
            self.p.widgets["ping.do_ping"].enabled(True)
