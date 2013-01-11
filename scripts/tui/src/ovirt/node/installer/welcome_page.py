#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# welcome_page.py - Copyright (C) 2013 Red Hat, Inc.
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
Welcome page of the installer

The idea is that every page modifies it's own model, which is at the end pulled
using the plugin.model() call and used to build a stream of
transaction_elements (see progress_page.py)

NOTE: Each page stores the information in the config page
NOTE II: Or shall we build the transactions per page?
"""
from ovirt.node import plugins, ui


class Plugin(plugins.NodePlugin):
    """The welcome page plugin
    """
    _model = {}
    _elements = None

    def name(self):
        return "Welcome"

    def rank(self):
        return 10

    def model(self):
        return self._model

    def validators(self):
        return {}

    def ui_content(self):
        ws = [ui.Button("button.install", "Install %s" %
                        str(self.application.product)),
              ]
        self.widgets.add(ws)
        page = ui.Page("welcome", ws)
        page.buttons = [ui.Button("button.quit", "Quit")]
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        if "button.install" in effective_changes:
            self.transaction = "a"
            self.application.ui.navigate.to_next_plugin()
