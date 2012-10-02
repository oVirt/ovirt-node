"""
Representing the whole application (not just the TUI).
Basically the application consists of two parts: Plugins and TUI
which communicate with each other.
"""

import logging

import ovirt.node.tui
import ovirt.node.utils

logging.basicConfig(level=logging.DEBUG,
                    filename="app.log", filemode="w")
LOGGER = logging.getLogger(__name__)


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
