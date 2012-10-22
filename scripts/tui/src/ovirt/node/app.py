#!/usr/bin/python
#
# app.py - Copyright (C) 2012 Red Hat, Inc.
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
Representing the whole application (not just the TUI).
Basically the application consists of two parts: Plugins and TUI
which communicate with each other.
"""

import logging

logging.basicConfig(level=logging.DEBUG,
                    filename="app.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOGGER = logging.getLogger(__name__)


import ovirt.node.tui
import ovirt.node.utils


class Application(object):
    plugins = []

    ui = None

    def __init__(self):
        self.ui = ovirt.node.tui.UrwidTUI(self)

    def __load_plugins(self):
        self.plugins = [m.Plugin() for m in ovirt.node.plugins.load_all()]

        for plugin in self.plugins:
            LOGGER.debug("Loading plugin %s" % plugin)
            self.ui.register_plugin(plugin.ui_name(), plugin)

    def __drop_to_shell(self):
        with self.ui.suspended():
            ovirt.node.utils.process.system("reset ; bash")

    def run(self):
        self.__load_plugins()
        self.ui.register_hotkey("f12", self.__drop_to_shell)
        self.ui.footer = "Press ctrl+x or esc to quit."
        self.ui.run()
