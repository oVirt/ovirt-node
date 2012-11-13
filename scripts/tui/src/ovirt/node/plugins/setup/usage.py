#!/usr/bin/python
#
# usage.py - Copyright (C) 2012 Red Hat, Inc.
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
A plugin illustrating how to use the TUI
"""

import ovirt.node.plugins
import ovirt.node.ui


usage = """Plugins need to be derived from a provided class and need to \
implement a couple of methods.
Data is only passed via a dictionary between the UI and the plugin, this way \
it should be also easier to test plugins.

The plugin (one python file) just needs to be dropped into a specififc \
directory to get picked up (ovirt/node/plugins/) and is  a python file.
"""


class Plugin(ovirt.node.plugins.NodePlugin):
    def name(self):
        return "Usage"

    rank = lambda self: 999

    has_ui = lambda self: False

    def ui_content(self):
        widgets = [
            ("usage.info", ovirt.node.ui.Label(usage))
        ]

        page = ovirt.node.ui.Page(widgets)
        page.has_save_button = False
        return page

    def model(self):
        return {}
