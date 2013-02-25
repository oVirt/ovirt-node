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
from ovirt.node import ui, plugins, utils
from ovirt.node.config import defaults
from ovirt.node.utils import security, virt, system
import os
import textwrap


"""
Status page plugin
"""


class Plugin(plugins.NodePlugin):
    """This is the summary page, summarizing all sorts of informations

    There are no validators, as there is no input.
    """

    _model = None

    def name(self):
        return "Status"

    def rank(self):
        return 0

    def model(self):
        net_status, net_br, net_addrs = utils.network.networking_status()
        net_addrs_str = ""
        if net_addrs:
            net_addrs_str = "\nIPv4: {inet}\nIPv6: {inet6}".format(**net_addrs)

        num_domains = virt.number_of_domains()

        return {
            "status": virt.hardware_status(),
            "networking": net_status,
            "networking.bridge": "%s %s" % (net_br, net_addrs_str),
            "logs": self._logging_summary(),
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
        network_widgets = [ui.KeywordLabel("networking",
                                           aligned("Networking: ")),
                           ui.KeywordLabel("networking.bridge",
                                           "Bridge: "),
                           ]

        action_widgets = [ui.Button("action.lock", "Lock"),
                          ui.Button("action.logoff", "Log Off"),
                          ui.Button("action.restart", "Restart"),
                          ui.Button("action.poweroff", "Poweroff")
                          ]

        widgets = [ui.Header("header[0]", "System Information"),

                   ui.KeywordLabel("status", aligned("Status: ")),
                   ui.Divider("divider[0]"),

                   ui.Row("row[0]", network_widgets),
                   ui.Divider("divider[1]"),

                   ui.KeywordLabel("logs", aligned("Logs: ")),
                   ui.Divider("divider[2]"),

                   ui.KeywordLabel("libvirt.num_guests",
                                   aligned("Running VMs: ")),
                   ui.Divider("divider[3]"),

                   ui.Label("support.hint", "Press F8 for support menu"),
                   ui.Divider("divider[4]"),

                   ui.Row("row[1]",
                          [ui.Button("action.hostkey", "View Host Key"),
                           ui.Button("action.cpu_details",
                                     "View CPU Details"),
                           ]),

                   ui.Row("row[2]", action_widgets),
                   ]

        self.widgets.add(widgets)

        page = ui.Page("page", widgets)
        page.buttons = []
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, changes):
        # Handle button presses
        if "action.lock" in changes:
            self.logger.info("Locking screen")
            self._lock_dialog = LockDialog()
            self.application.ui.hotkeys_enabled(False)
            return self._lock_dialog
        elif "action.unlock" in changes and "password" in changes:
            self.logger.info("UnLocking screen")
            pam = security.PAM()
            if pam.authenticate(os.getlogin(), changes["password"]):
                self._lock_dialog.close()
                self.application.ui.hotkeys_enabled(True)

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
            return HostkeyDialog("dialog.hostkey", "Host Key")

        elif "action.cpu_details" in changes:
            self.logger.info("Showing CPU details")
            return CPUFeaturesDialog("dialog.cpu_details", "CPU Details")

        elif "_save" in changes:
            self.widgets["dialog.hostkey"].close()

    def _logging_summary(self):
        """Return a textual summary of the current log configuration
        """
        netconsole = defaults.Netconsole().retrieve()
        syslog = defaults.Syslog().retrieve()

        destinations = []

        if syslog["server"]:
            destinations.append("Rsyslog: %s:%s" % (syslog["server"],
                                                    syslog["port"] or "514"))

        if netconsole["server"]:
            destinations.append("Netconsole: %s:%s" %
                                (netconsole["server"],
                                 netconsole["port"] or "6666"))

        return ", ".join(destinations) if destinations else "Local Only"


class HostkeyDialog(ui.Dialog):
    def __init__(self, path, title):
        super(HostkeyDialog, self).__init__(path, title, [])
        ssh = security.Ssh()
        fp, hk = ssh.get_hostkey()
        self.children = [ui.Label("hostkey.label[0]",
                                  "RSA Host Key Fingerprint:"),
                         ui.Label("hostkey.fp", fp),

                         ui.Divider("hostkey.divider[0]"),

                         ui.Label("hostkey.label[1]",
                                  "RSA Host Key:"),
                         ui.Label("hostkey", "\n".join(textwrap.wrap(hk, 64))),
                         ]
        self.buttons = [ui.CloseButton("dialog.close")]


class CPUFeaturesDialog(ui.InfoDialog):
    """The dialog beeing displayed when th euser clicks CPU Details
    """
    def __init__(self, path, title):
        msg = utils.system.cpu_details()
        super(CPUFeaturesDialog, self).__init__(path, title, msg)


class LockDialog(ui.Dialog):
    """The dialog beeing displayed when the srceen is locked
    """
    def __init__(self, path="lock.dialog", title="This screen is locked."):
        super(LockDialog, self).__init__(path, title, [])
        self.children = [ui.Header("lock.label[0]",
                                   "Enter the admin password to unlock"),
                         ui.KeywordLabel("username", "Username: ",
                                         os.getlogin()),
                         ui.PasswordEntry("password", "Password:")
                         ]
        self.buttons = [ui.Button("action.unlock", "Unlock")]
        self.escape_key = None
