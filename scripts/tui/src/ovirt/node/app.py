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


import ovirt.node.ui.tui
import ovirt.node.utils
import ovirt.node.plugins


class Application(object):
    plugins = []

    ui = None

    def __init__(self, ui_backend="urwid"):
        ui_backend_class = {
            "urwid": ovirt.node.ui.tui.UrwidTUI
        }[ui_backend]
        self.ui = ui_backend_class(self)

    def __load_plugins(self):
        self.plugins = [m.Plugin(self) for m in ovirt.node.plugins.load_all()]

        for plugin in self.plugins:
            LOGGER.debug("Loading plugin %s" % plugin)
            self.ui.register_plugin(plugin.ui_name(), plugin)

    def __drop_to_shell(self):
        with self.ui.suspended():
            ovirt.node.utils.process.system("reset ; bash")

    def __check_terminal_size(self):
        cols, rows = self.ui.size()
        if cols < 80 or rows < 24:
            LOGGER.warning("Window size is too small: %dx%d" % (cols, rows))

    def model(self, plugin_name):
        model = None
        for plugin in self.plugins:
            if plugin.name() == plugin_name:
                model = plugin.model()
        return model

    def run(self):
        self.__load_plugins()
        self.ui.register_hotkey("f12", self.__drop_to_shell)
        self.ui.register_hotkey("window resize", self.__check_terminal_size)
        self.ui.footer = "Press esc to quit."
        self.ui.run()

    def quit(self):
        LOGGER.info("Quitting")
        self.ui.quit()
