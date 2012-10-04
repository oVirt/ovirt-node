#!/usr/bin/python
#
# features.py - Copyright (C) 2012 Red Hat, Inc.
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
A plugin illustrating the features of the TUI
"""
import logging

import ovirt.node.plugins


LOGGER = logging.getLogger(__name__)

features = """
- Resize the terminal window and watch
- Point your mouse cursor at one of the left side list items and click
- In the background: Event based
- Press <ESC>
"""


class Plugin(ovirt.node.plugins.NodePlugin):
    def name(self):
        return "Features"

    rank = lambda self: 10

    def ui_content(self):
        widgets = [
            ("features.info", ovirt.node.plugins.Label(features))
        ]
        return widgets

    def ui_config(self):
        return {
            "save_button": False
        }
