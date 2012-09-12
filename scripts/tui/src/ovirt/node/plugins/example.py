

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

    def ui_on_change(self, model):
        """Called when some widget was changed
        """
        LOGGER.debug("changed: " + str(model))

    def ui_on_save(self, model):
        """Called when data should be saved
        """
        LOGGER.debug("saved: " + str(model))
