# -*- coding: utf-8 *-*
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# kdump_page.py - Copyright (C) 2012 Red Hat, Inc.
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
Diagnostics page
"""

from ovirt.node import plugins, ui


class Plugin(plugins.NodePlugin):

    def name(self):
        return "Diagnostics"

    def rank(self):
        return 95

    def model(self):
        """Don't need to set up anything"""
        return {}

    def validators(self):
        """Validators validate the input on change and give UI feedback
        """
        return {}

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        ws = [ui.Header("diagnostic._header", "Diagnostic Utilities"),
              ui.Label("diagnostic.info", "Select one of the tools below. \n" +
                       "Press 'q' to quit when viewing output"),
              ui.Divider("diagnostic.divider"),
              ui.Table("diagnostic.tools", "", "Available diagnostics",
                       self.__diagnostics(), height=min(
                           len(self.__diagnostics()), 4)),
              ]

        page = ui.Page("page", ws)
        self.widgets.add(page)
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, changes):
        if changes.contains_any(["diagnostic.logfiles", "diagnostic.tools"]):
            cmds = {}
            changed_field = changes.keys()[0]
            if "diagnostic.tools" in changed_field:
                cmds = dict((name, cmd) for (name, cmd)
                             in self.__diagnostics())
            cmd = cmds.get(changes[changed_field], None)
            if cmd:
                return OutputDialog("output.dialog", "Command Output", cmd)

    def __diagnostics(self):
        return [("multipath", "multipath -ll"),
                ("fdisk", "fdisk -l"),
                ("parted", "parted -l")]


class OutputDialog(ui.Dialog):

    def __init__(self, path, title, cmd):
        from ovirt.node.utils import process
        super(OutputDialog, self).__init__(path, title, [])
        output = process.check_output(cmd)
        self.children = [ui.Table("output[0]", "", cmd,
                                      output, height=10)]
        self.buttons = [ui.CloseButton("dialog.close")]
