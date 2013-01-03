#!/usr/bin/python
# -*- coding: utf-8 -*-
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

import argparse
import logging
import logging.config

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(name)s ' +
                      '%(process)d %(message)s'
        },
        'simple': {
            'format': '%(asctime)s %(levelname)10s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'simple',
            'filename': '/tmp/ovirt.log',
            'mode': 'w'
        },
        'debug': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'formatter': 'verbose',
            'filename': '/tmp/ovirt.debug.log',
            'mode': 'w'
        },
    },
    'loggers': {
        'ovirt.node': {
            'handlers': ['debug'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'ovirt.node': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    }
}
logging.config.dictConfig(LOGGING)
#logging.basicConfig(level=logging.DEBUG,
#                    filename="/tmp/app.log", filemode="w",
#                    format="%(asctime)s %(levelname)s %(name)s %(message)s")


import ovirt.node.ui.tui
from ovirt.node import base, utils, plugins
from ovirt.node.config import defaults


class Application(base.Base):
    plugins = []

    ui = None

    def __init__(self, plugin_base, ui_backend="urwid"):
        super(Application, self).__init__()
        self.logger.info(("Starting '%s' application " +
                          "with '%s' UI") % (plugin_base, ui_backend))

        self.__parse_cmdline()

        ui_backend_class = {
            "urwid": ovirt.node.ui.tui.UrwidTUI
        }[ui_backend]
        self.ui = ui_backend_class(self)
        self.plugin_base = plugin_base

    def __parse_cmdline(self):
        parser = argparse.ArgumentParser(description='oVirt Node Utility')
        parser.add_argument("--defaults",
                            type=str,
                            help="Central oVirt Node configuration file")
        parser.add_argument("--dry",
                            action='store_true',
                            help="Just write defaults, nothing else")
        self.args = parser.parse_args()
        self.logger.debug("Parsed args: %s" % self.args)
        if self.args.defaults:
            # FIXME Should be read by clients
            defaults.OVIRT_NODE_DEFAULTS_FILENAME = self.args.defaults
            self.logger.debug("Setting config file: %s (%s)" % (
                                        self.args.defaults,
                                        defaults.OVIRT_NODE_DEFAULTS_FILENAME))

        self.logger.debug("Commandline arguments: %s" % self.args)

    def __load_plugins(self):
        self.plugins = []
        for m in plugins.load(self.plugin_base):
            if hasattr(m, "Plugin"):
                self.logger.debug("Found plugin in module: %s" % m)
                plugin = m.Plugin(self)
                self.plugins.append(plugin)
            else:
                self.logger.debug("Found no plugin in module: %s" % m)

        for plugin in self.plugins:
            self.logger.debug("Loading plugin %s" % plugin)
            self.ui.register_plugin(plugin.ui_name(), plugin)

    def __drop_to_shell(self):
        with self.ui.suspended():
            utils.process.system("reset ; bash")

    def __check_terminal_size(self):
        cols, rows = self.ui.size()
        if cols < 80 or rows < 24:
            self.logger.warning("Window size is too small: %dx%d" % (cols,
                                                                     rows))

    def model(self, plugin_name):
        model = None
        for plugin in self.plugins:
            if plugin.name() == plugin_name:
                model = plugin.model()
        return model

    @property
    def product(self):
        return utils.system.ProductInformation()

    def run(self):
        self.__load_plugins()
        if not self.plugins:
            raise Exception("No plugins found in '%s'" % self.plugin_base)
        self.ui.register_hotkey("f2", self.__drop_to_shell)
        self.ui.register_hotkey("window resize", self.__check_terminal_size)

        p = self.product
        self.ui.header = "\n %s %s-%s\n" % (p.PRODUCT_SHORT, p.VERSION,
                                          p.RELEASE)
        self.ui.footer = "Press esc to quit."
        self.ui.run()

    def quit(self):
        self.logger.info("Quitting")
        self.ui.quit()
