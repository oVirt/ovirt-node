

import os.path
import logging

import ovirt.node.plugins

LOGGER = logging.getLogger(__name__)

class Plugin(ovirt.node.plugins.NodePlugin):
    def name(self):
        return os.path.basename(__file__)

    def ui_content(self):
        widgets = []
        widgets.append(ovirt.node.plugins.Label("Subsection"))
        widgets.append(ovirt.node.plugins.Entry("foo.bar", label=__file__))
        return widgets
