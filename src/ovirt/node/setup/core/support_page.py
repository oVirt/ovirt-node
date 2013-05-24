#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# support_page.py - Copyright (C) 2012 Red Hat, Inc.
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
from ovirt.node import ui, utils
from ovirt.node.plugins import NodePlugin
from ovirt.node.utils import process

"""
A plugin for a support page
"""


class Plugin(NodePlugin):
    def __init__(self, application):
        # Register F8: Display this plugin when F( is pressed
        show_plugin = lambda: application.switch_to_plugin(self)
        application.ui.register_hotkey(["f8"], show_plugin)
        super(Plugin, self).__init__(application)

    def name(self):
        return "Support"

    def rank(self):
        return 999

    def has_ui(self):
        return False

    def ui_content(self):
        ws = [ui.Header("header[0]", "Support Info"),
              ui.Label("support.info", "Select one of the logfiles below. \n" +
                       "Press 'q' to quit when viewing a logfile."),
              ui.Divider("divider[0]"),
              ui.Table("support.logfile", "", "Available Logfiles",
                       self.__debugfiles_to_offer()),
              ]

        page = ui.Page("page", ws)
        page.buttons = []
        self.widgets.add(page)
        return page

    def model(self):
        return {}

    def validators(self):
        return {}

    def on_change(self, changes):
        pass

    def on_merge(self, changes):
        if changes.contains_any(["support.logfile"]):
            logfile = changes["support.logfile"]
            cmds = {"node": "cat /var/log/ovirt.log | less",
                    "ui": "cat /tmp/ovirt.debug.log | less",
                    "messages": "cat /var/log/messages | less",
                    "audit": "cat /var/log/audit/audit.log | less",
                    "dmesg": "dmesg | less",
                    "journal": "journalctl --all --catalog --full"
                    }

            cmd = cmds[logfile] if logfile in cmds else None

            if cmd:
                contents = process.check_output(cmd, stderr=process.STDOUT)
                return ui.TextViewDialog("output.dialog", "Logfile",
                                         contents)

    def __debugfiles_to_offer(self):
        return [("node", "/var/log/ovirt.log"),
                ("ui", "/tmp/ovirt.debug.log"),
                ("dmesg", "dmesg"),
                ("messages", "/var/log/messages"),
                ("journal", "journal (systemd)"),
                ("audit", "/var/log/audit/audit.log")]
