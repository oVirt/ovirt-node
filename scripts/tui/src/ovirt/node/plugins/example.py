

import os.path
import logging

import ovirt.node.plugins
import ovirt.node.valid
from ovirt.node.plugins import Header, Entry, Password

LOGGER = logging.getLogger(__name__)


class Plugin(ovirt.node.plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return os.path.basename(__file__)

    def model(self):
        """Returns the model of this plugin
        This is expected to parse files and all stuff to build up the model.
        """
        if not self._model:
            self._model = {
                "foo.hostname": "example.com",
                "foo.port": "8080",
                "foo.password": "secret",
            }
        return self._model

    def validators(self):
        nospace = lambda v: "No space allowed." if " " in v else None

        return {
                "foo.hostname": ovirt.node.valid.Hostname(),
                "foo.port": ovirt.node.valid.Number(),
                "foo.password": nospace
            }

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        widgets = [
            ("foo.section", Header("Subsection")),
            ("foo.hostname", Entry(label="Hostname")),
            ("foo.port", Entry(label="Port")),
            ("foo.password", Password(label="Password")),
        ]
        self._widgets = dict(widgets)
        return widgets

    def on_change(self, changes):
        """Applies the changes to the plugins model, will do all required logic
        """
        LOGGER.debug("checking %s" % changes)
        if "foo.bar" in changes:
            LOGGER.debug("Found foo.bar")

            if "/" in changes["foo.bar"]:
                raise ovirt.node.plugins.InvalidData("No slash allowed")

            if len(changes["foo.bar"]) < 5:
                raise ovirt.node.plugins.Concern("Should be at least 5 chars")

            self._model.update(changes)

            if "dis" in changes["foo.bar"]:
                self._widgets["foo.bar2"].enabled(False)
                LOGGER.debug("change to dis")
                #raise ovirt.node.plugins.ContentRefreshRequest()
            else:
                self._widgets["foo.bar2"].enabled(True)

        if "foo.bar2" in changes:
            LOGGER.debug("Found foo.bar2")

            if "/" in changes["foo.bar2"]:
                raise ovirt.node.plugins.InvalidData("No slashes allowed")

        return True

    def on_merge(self, changes):
        """Applies the changes to the plugins model, will do all required logic
        """
        LOGGER.debug("saving %s" % changes)
        # Look for conflicts etc
        self._model.update(changes)
