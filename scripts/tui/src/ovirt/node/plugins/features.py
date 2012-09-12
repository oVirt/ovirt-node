

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

    def ui_content(self):
        widgets = [
            ("features.info", ovirt.node.plugins.Label(features))
        ]
        return widgets
