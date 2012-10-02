"""
A plugin illustrating how to use the TUI
"""
import logging

import ovirt.node.plugins


LOGGER = logging.getLogger(__name__)

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

    rank = lambda self: 10

    def ui_content(self):
        widgets = [
            ("usage.info", ovirt.node.plugins.Label(usage))
        ]
        return widgets

    def ui_config(self):
        return {
            "save_button": False
        }
