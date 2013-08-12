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
from ovirt.node import exceptions, ui, plugins, utils
from ovirt.node.config import defaults
from ovirt.node.utils import security, virt, system
from ovirt.node.utils.network import IPAddress
from ovirt.node.utils.system import Bootloader
import os
import textwrap


"""
Status page plugin
"""


class Plugin(plugins.NodePlugin):
    """This is the summary page, summarizing all sorts of informations

    There are no validators, as there is no input.
    """

    _model = {}
    _extra_model = {}

    def name(self):
        return _("Status")

    def rank(self):
        return 0

    def model(self):
        mng = defaults.Management()
        managementifs = mng.retrieve()["managed_ifnames"]

        # If prmiaryif == None, then the corretc NIC will be automatically be
        # determined
        primaryif = managementifs[0] if managementifs else None

        self.logger.debug("NIC for status: %s" % primaryif)

        net_status, net_br, net_addrs = \
            utils.network.networking_status(primaryif)
        net_addrs_str = ""
        if net_addrs:
            net_addrs_str = "IPv4: {inet}\nIPv6: {inet6}".format(**net_addrs)

        num_domains = virt.number_of_domains()

        model = {
            "status": virt.hardware_status(),
            "managed_by": mng.retrieve()["managed_by"],
            "networking": net_status,
            "networking.ip": net_addrs_str,
            "networking.bridge": net_br,
            "logs": self._logging_summary(),
            "libvirt.num_guests": num_domains,
        }

        model.update(self._extra_model)
        return model

    def validators(self):
        return {}

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        # Function to expand all "keywords" to the same length
        aligned = lambda l: l.ljust(13)

        # Network related widgets, appearing in one row
        network_widgets = [ui.KeywordLabel("networking",
                                           aligned(_("Networking: "))),
                           ui.Label("networking.bridge", ""),
                           ]

        action_widgets = [ui.Button("action.lock", _("Lock")),
                          ui.Button("action.logoff", _("Log Off")),
                          ui.Button("action.restart", _("Restart")),
                          ui.Button("action.poweroff", _("Power Off"))
                          ]

        widgets = [ui.Header("header[0]", _("System Information"))]

        if self.model()["managed_by"]:
            widgets += [ui.KeywordLabel("managed_by",
                                        aligned(_("Managed by: ")))]

        widgets += [ui.KeywordLabel("status", aligned(_("Status: "))),
                    ui.Divider("divider[0]"),

                    ui.Row("row[0]", network_widgets),
                    ui.Label("networking.ip", ""),
                    ui.Divider("divider[1]"),

                    ui.KeywordLabel("logs", aligned(_("Logs: "))),

                    ui.KeywordLabel("libvirt.num_guests",
                                    aligned(_("Running VMs: "))),

                    ui.Divider("divider[2]"),
                    ui.Label("support.hint", _("Press F8 for support menu")),

                    ui.Row("row[1]",
                           [ui.Button("action.hostkey", _("View Host Key")),
                            ui.Button("action.cpu_details",
                                      _("View CPU Details"))
                            ]),

                    ui.Button("action.console", "Set Console Path"),

                    ui.Row("row[2]", action_widgets),
                    ]

        self.widgets.add(widgets)

        page = ui.Page("page", widgets)
        page.buttons = []
        return page

    def on_change(self, changes):
        if "console.path" in changes:
            if "console.path" is not "" and not os.path.exists(
                    "/dev/%s" % changes["console.path"].split(',')[0]):
                raise exceptions.InvalidData("Console path must be a valid"
                                             "device or empty")

    def on_merge(self, changes):
        # Handle button presses
        number_of_vm = _("There are %s Virtual Machines running.") \
            % (virt.number_of_domains())
        if "action.lock" in changes:
            self.logger.info("Locking screen")
            self._lock_dialog = LockDialog(title=_("This screen is locked."))
            self.application.ui.hotkeys_enabled(False)
            self.widgets.add(self._lock_dialog)
            return self._lock_dialog

        elif "action.unlock" in changes and "password" in changes:
            self.logger.info("UnLocking screen")
            pam = security.PAM()
            if pam.authenticate(os.getlogin(), changes["password"]):
                self._lock_dialog.close()
                self.application.ui.hotkeys_enabled(True)
            else:
                self.application.notice(
                    _("The provided password was incorrect."))
                self.widgets["password"].text("")

        elif "action.logoff" in changes:
            self.logger.info("Logging off")
            self.application.quit()

        elif "action.restart" in changes:
            self.logger.info("Restarting")
            return ui.ConfirmationDialog("confirm.reboot",
                                         _("Confirm System Restart"),
                                         number_of_vm +
                                         _("\nThis will restart the system,") +
                                         _(" proceed?"))

        elif "confirm.reboot.yes" in changes:
            self.logger.info("Confirm Restarting")
            self.dry_or(lambda: system.reboot())

        elif "action.poweroff" in changes:
            self.logger.info("Shutting down")
            return ui.ConfirmationDialog(
                "confirm.shutdown",
                _("Confirm System Poweroff"),
                number_of_vm +
                _("\nThis will shut down the system,") +
                _("proceed?"))

        elif "confirm.shutdown.yes" in changes:
            self.logger.info("Confirm Shutting down")
            self.dry_or(lambda: system.poweroff())

        elif "action.hostkey" in changes:
            self.logger.info("Showing hostkey")
            return HostkeyDialog("dialog.hostkey", _("Host Key"))

        elif "action.cpu_details" in changes:
            self.logger.info("Showing CPU details")
            return CPUFeaturesDialog("dialog.cpu_details", _("CPU Details"))

        elif "action.console" in changes:
            self.logger.info("Showing Console details")
            self._consoledialog = ConsoleDialog(self, "dialog.console",
                                                "Console Details")
            return self._consoledialog

        elif "dialog.console.save" in changes:
            self.logger.info("Saving Console Details")
            if "console.path" in changes:
                self._consoledialog._console(changes["console.path"])
            self._consoledialog.close()

        elif "_save" in changes:
            self.widgets["dialog.hostkey"].close()

    def _logging_summary(self):
        """Return a textual summary of the current log configuration
        """
        netconsole = defaults.Netconsole().retrieve()
        syslog = defaults.Syslog().retrieve()

        destinations = []

        if syslog["server"]:
            destinations.append("Rsyslog: %s:%s" %
                                (IPAddress(syslog["server"]),
                                 syslog["port"] or "514"))

        if netconsole["server"]:
            destinations.append("Netconsole: %s:%s" %
                                (IPAddress(netconsole["server"]),
                                 netconsole["port"] or "6666"))

        indented = "\n" + " ".ljust(13)
        return indented.join(destinations) if destinations else "Local Only"


class HostkeyDialog(ui.Dialog):
    def __init__(self, path, title):
        super(HostkeyDialog, self).__init__(path, title, [])
        ssh = security.Ssh()
        fp, hk = ssh.get_hostkey()
        self.children = [ui.Label("hostkey.label[0]",
                                  _("RSA Host Key Fingerprint:")),
                         ui.Label("hostkey.fp", fp),

                         ui.Divider("hostkey.divider[0]"),

                         ui.Label("hostkey.label[1]",
                                  _("RSA Host Key:")),
                         ui.Label("hostkey", "\n".join(textwrap.wrap(hk, 64))),
                         ]
        self.buttons = [ui.CloseButton("dialog.close")]


class CPUFeaturesDialog(ui.InfoDialog):
    """The dialog beeing displayed when th euser clicks CPU Details
    """
    def __init__(self, path, title):
        msg = utils.system.cpu_details()
        super(CPUFeaturesDialog, self).__init__(path, title, msg)


class ConsoleDialog(ui.Dialog):
    """The dialog displayed to enter console paths for the bootloader"""
    def __init__(self, plugin, path, title):
        self.plugin = plugin
        super(ConsoleDialog, self).__init__(path, title, [])
        self.plugin._extra_model.update({"console.path": self._console()})
        self.plugin.model()
        self.children = [ui.Label("Enter the path to a valid console device"),
                         ui.Label("Example: /dev/ttyS0,115200n8"),
                         ui.Entry("console.path", "Console path:")]

    def _console(self, console_path=None):
        def real_console():
            b = Bootloader().Arguments()
            if not console_path:
                return b["console"] if "console" in b else ""
            else:
                b["console"] = str(console_path)
        return self.plugin.dry_or(real_console) or ""


class LockDialog(ui.Dialog):
    """The dialog beeing displayed when the srceen is locked
    """
    def __init__(self, path="lock.dialog", title="This screen is locked."):
        super(LockDialog, self).__init__(path, title, [])
        self.children = [ui.Header("lock.label[0]",
                                   _("Enter the admin password to unlock")),
                         ui.KeywordLabel("username", _("Username: "),
                                         os.getlogin()),
                         ui.PasswordEntry("password", _("Password:"))
                         ]
        self.buttons = [ui.Button("action.unlock", _("Unlock"))]
        self.escape_key = None
