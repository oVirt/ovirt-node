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

"""
A plugin for a support page
"""

import ovirt.node.plugins
import ovirt.node.ui


class Plugin(ovirt.node.plugins.NodePlugin):
    def __init__(self, application):
        # Register F8: Display this plugin when F( is pressed
        application.ui.register_hotkey(["f8"],
                                lambda: application.ui.display_plugin(self))

    def name(self):
        return "Support"

    rank = lambda self: 999

    has_ui = lambda self: False

    def ui_content(self):
        widgets = [
            ("features.info", ovirt.node.ui.Label("FIXME Support info"))
        ]

        page = ovirt.node.ui.Page(widgets)
        page.has_save_button = False
        return page

    def model(self):
        return {}
