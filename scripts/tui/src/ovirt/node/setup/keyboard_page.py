#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# keyboard_page.py - Copyright (C) 2012 Red Hat, Inc.
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
Configure Keyboard Layout
"""

import ovirt.node.plugins
import ovirt.node.ui


class Plugin(ovirt.node.plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Keyboard"

    def rank(self):
        return 30

    def model(self):
        if not self._model:
            self._model = {
                "layout": "en_US",
            }

        return self._model

    def validators(self):
        return {}

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        widgets = [
            ("layout._header",
                ovirt.node.ui.Header("Keyboard Layout Selection")),
            ("layout", ovirt.node.ui.Table("Available Keyboard Layouts",
                                           "", self._get_layouts())),

        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        return page

    def _get_layouts(self):
        # FIXME load from somewhere
        return [
                ("en_US", "U.S. English"),
                ("de_DE", "German"),
                ]

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        pass
