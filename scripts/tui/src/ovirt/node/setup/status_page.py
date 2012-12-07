#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# status_page.py - Copyright (C) 2012 Red Hat, Inc.
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
import os
import textwrap

from ovirt.node import ui, plugins, utils
from ovirt.node.utils import security, virt, system

"""
Status page plugin
"""


class Plugin(plugins.NodePlugin):
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
        net_addrs_str = ""
        if net_addrs:
            net_addrs_str = "\nIPv4: {inet}\nIPv6: {inet6}".format(**net_addrs)

        num_domains = "N/A"
        with virt.LibvirtConnection() as con:
            num_domains = str(con.numOfDomains())

        return {
            "status": virt.virtualization_hardware_status(),
            "networking": net_status,
            "networking.bridge": "%s %s" % (net_br, net_addrs_str),
            "logs": "Local Only",
            "libvirt.num_guests": num_domains,
        }

    def validators(self):
        return {}

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        # Function to expand all "keywords" to the same length
        aligned = lambda l: l.ljust(14)

        # Network related widgets, appearing in one row
        network_widgets = [
                ("networking",
                    ui.KeywordLabel(aligned("Networking: "))),
                ("networking.bridge",
                    ui.KeywordLabel("Bridge: ")),
            ]

        action_widgets = [
            ("action.lock", ui.Button("Lock")),
            ("action.logoff", ui.Button("Log Off")),
            ("action.restart", ui.Button("Restart")),
            ("action.poweroff", ui.Button("Poweroff")),
        ]

        widgets = [
            ("status",
                ui.KeywordLabel(aligned("Status: "))),
            ("status._space", ui.Divider()),

            ("network._column", ui.Row(network_widgets)),
            ("network._space", ui.Divider()),

            ("logs",
                ui.KeywordLabel(aligned("Logs: "))),
            ("logs._space", ui.Divider()),

            ("libvirt.num_guests",
                ui.KeywordLabel(aligned("Running VMs: "))),
            ("libvirt._space", ui.Divider()),

            ("support.hint", ui.Label("Press F8 for support menu")),
            ("support._space", ui.Divider()),

            ("action.hostkey", ui.Button("View Host Key")),

            ("action._row", ui.Row(action_widgets)),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ui.Page(widgets)
        page.buttons = []
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, changes):
        # Handle button presses
        if "action.lock" in changes:
            self.logger.info("Locking screen")
            self._lock_dialog = self._build_lock_dialog()
            return self._lock_dialog
        elif "action.unlock" in changes and "password" in changes:
            self.logger.info("UnLocking screen")
            pam = security.PAM()
            if pam.authenticate(os.getlogin(), changes["password"]):
                self._lock_dialog.close()

        elif "action.logoff" in changes:
            self.logger.info("Logging off")
            self.application.quit()

        elif "action.restart" in changes:
            self.logger.info("Restarting")
            self.dry_or(lambda: system.reboot())

        elif "action.poweroff" in changes:
            self.logger.info("Shutting down")
            self.dry_or(lambda: system.poweroff())

        elif "action.hostkey" in changes:
            self.logger.info("Showing hostkey")
            return self._build_hostkey_dialog()

        elif "_save" in changes:
            self._widgets["dialog.hostkey"].close()

    def _build_dialog(self, path, txt, widgets):
        self._widgets.update(dict(widgets))
        self._widgets[path] = ui.Dialog(txt, widgets)
        return self._widgets[path]

    def _build_hostkey_dialog(self):
        ssh = security.Ssh()
        fp, hk = ssh.get_hostkey()
        dialog = self._build_dialog("dialog.hostkey", "Host Key", [
            ("hostkey.fp._label",
                ui.Label("RSA Host Key Fingerprint:")),
            ("hostkey.fp",
                ui.Label(fp)),

            ("hostkey._divider", ui.Divider()),

            ("hostkey._label",
                ui.Label("RSA Host Key:")),
            ("hostkey",
                ui.Label("\n".join(textwrap.wrap(hk, 64)))),
        ])
        dialog.buttons = []
        return dialog

    def _build_lock_dialog(self):
        widgets = [
            ("label[0]", ui.Header("Enter the admin password to unlock")),
            ("username", ui.KeywordLabel("Username: ", os.getlogin())),
            ("password",
                ui.PasswordEntry("Password:"))
        ]
        self._widgets = dict(widgets)
        page = ui.Dialog("This screen is locked.", widgets)
        page.buttons = [("action.unlock", ui.Button("Unlock"))]
        page.escape_key = None
        return page
