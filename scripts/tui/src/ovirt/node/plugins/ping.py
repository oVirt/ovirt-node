#!/usr/bin/python
#
# ping.py - Copyright (C) 2012 Red Hat, Inc.
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
import logging

import ovirt.node.plugins
import ovirt.node.valid
import ovirt.node.ui
import ovirt.node.utils.process

LOGGER = logging.getLogger(__name__)


class Plugin(ovirt.node.plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Tools (ping)"

    def rank(self):
        return 70

    def model(self):
        """Returns the model of this plugin
        This is expected to parse files and all stuff to build up the model.
        """
        if not self._model:
            self._model = {
                # The target address
                "ping.address": "127.0.0.1",
                "ping.count": "3",
                # The result field
                "ping.result": ""
            }
        return self._model

    def validators(self):
        """Validators validate the input on change and give UI feedback
        """
        return {
                # The address must be fqdn, ipv4 or ipv6 address
                "ping.address": ovirt.node.valid.FQDNOrIPAddress(),
                "ping.count": ovirt.node.valid.Number(min=1, max=20),
            }

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        widgets = [
            ("ping.header", ovirt.node.ui.Header("Ping a remote host")),
            ("ping.address", ovirt.node.ui.Entry("Address")),
            ("ping.count", ovirt.node.ui.Entry("Count")),
            ("ping.do_ping", ovirt.node.ui.Button("Ping")),
            ("ping.result-divider", ovirt.node.ui.Divider("-")),
            ("ping.result", ovirt.node.ui.Label("Result:")),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        page.has_save_button = False
        return page

    def on_change(self, changes):
        """Applies the changes to the plugins model, will do all required logic
        """
        LOGGER.debug("New (valid) address: %s" % changes)
        if "ping.address" in changes:
            self._model.update(changes)
        if "ping.count" in changes:
            self._model.update(changes)
        if "ping.do_ping" in changes:
            self.on_merge(changes)

    def on_merge(self, effective_changes):
        """Applies the changes to the plugins model, will do all required logic
        Normally on_merge is called by pushing the SaveButton instance, in this
        case it is called by on_change
        """

        if "ping.address" in self._model:
            addr = self._model["ping.address"]
            count = self._model["ping.count"]
            LOGGER.debug("Pinging %s" % addr)

            cmd = "ping"
            if ovirt.node.valid.IPv6Address().validate(addr):
                cmd = "ping6"

            cmd = "%s -c %s %s" % (cmd, count, addr)
            out = ""
            for line in ovirt.node.utils.process.pipe_async(cmd):
                out += line
                self._widgets["ping.result"].text("Result:\n\n%s" % out)
