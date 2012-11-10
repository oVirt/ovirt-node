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
import textwrap

import ovirt.node.plugins
import ovirt.node.ui
import ovirt.node.utils as utils
import ovirt.node.utils.virt as virt
import ovirt.node.utils.security

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
        net_status, net_br, net_addrs = utils.network.networking_status()
        net_addrs_str = "\nIPv4: {inet}\nIPv6: {inet6}".format(**net_addrs)

        num_domains = "N/A"
#        with virt.LibvirtConnection() as con:
#            num_domains = str(con.numOfDomains())

        return {
            "status": virt.virtualization_hardware_status(),
            "networking": net_status,
            "networking.bridge": "%s %s" % (net_br, net_addrs_str),
            "logs": "Local Only",
            "libvirt.num_guests": num_domains,
        }

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        # Function to expand all "keywords" to the same length
        aligned = lambda l: l.ljust(14)

        # Network related widgets, appearing in one row
        network_widgets = [
                ("networking",
                    ovirt.node.ui.KeywordLabel(aligned("Networking: "))),
                ("networking.bridge",
                    ovirt.node.ui.KeywordLabel("Bridge: ")),
            ]

        action_widgets = [
            ("action.lock", ovirt.node.ui.Button("Lock")),
            ("action.logoff", ovirt.node.ui.Button("Log Off")),
            ("action.restart", ovirt.node.ui.Button("Restart")),
            ("action.poweroff", ovirt.node.ui.Button("Poweroff")),
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

            ("action._row", ovirt.node.ui.Row(action_widgets)),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        page.has_save_button = False
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, changes):
        # Handle button presses
        if "action.lock" in changes:
            LOGGER.info("Locking screen")

        elif "action.logoff" in changes:
            LOGGER.info("Logging off")
            self.application.quit()

        elif "action.restart" in changes:
            LOGGER.info("Restarting")

        elif "action.poweroff" in changes:
            LOGGER.info("Shutting down")

        elif "action.hostkey" in changes:
            LOGGER.info("Showing hostkey")
            return self._build_hostkey_dialog()

        elif "_save" in changes:
            self._widgets["dialog.hostkey"].close()

    def _build_dialog(self, path, txt, widgets):
        self._widgets.update(dict(widgets))
        self._widgets[path] = ovirt.node.ui.Dialog(txt, widgets)
        return self._widgets[path]

    def _build_hostkey_dialog(self):
        fp, hk = ovirt.node.utils.security.get_ssh_hostkey()
        return self._build_dialog("dialog.hostkey", "Host Key", [
            ("hostkey.fp._label",
                ovirt.node.ui.Label("RSA Host Key Fingerprint:")),
            ("hostkey.fp",
                ovirt.node.ui.Label(fp)),

            ("hostkey._divider", ovirt.node.ui.Divider()),

            ("hostkey._label",
                ovirt.node.ui.Label("RSA Host Key:")),
            ("hostkey",
                ovirt.node.ui.Label("\n".join(textwrap.wrap(hk, 64)))),
        ])
