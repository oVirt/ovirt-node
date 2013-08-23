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
from ovirt.node import plugins, ui
from ovirt.node.utils import process

"""
Diagnostics page
"""


class Plugin(plugins.NodePlugin):

    def name(self):
        return _("Diagnostics")

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
        ws = [ui.Header("diagnostic._header", _("Diagnostic Utilities")),
              ui.Label("diagnostic.info", _("Select one of the tools below.")),
              ui.Divider("diagnostic.divider"),
              ui.Table("diagnostic.tools", "", _("Available diagnostics"),
                       self.__diagnostics(), height=min(
                           len(self.__diagnostics()), 4)),
              ]

        page = ui.Page("page", ws)
        page.buttons = []
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
                contents = process.check_output(cmd,
                                                stderr=process.STDOUT,
                                                shell=True)
                return ui.TextViewDialog("output.dialog", _("Command Output"),
                                         contents)

    def __diagnostics(self):
        return [("multipath", "multipath -ll"),
                ("fdisk", "fdisk -l"),
                ("parted", "parted -s -l"),
                ("lsblk", "lsblk")]
