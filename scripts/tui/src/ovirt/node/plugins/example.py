"""
Example plugin with TUI
"""
import logging

import ovirt.node.plugins
import ovirt.node.valid

LOGGER = logging.getLogger(__name__)


class Plugin(ovirt.node.plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Example Page"

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
                "foo.hostname": ovirt.node.valid.FQDN(),
                "foo.port": ovirt.node.valid.Port(),
                "foo.password": nospace
            }

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        widgets = [
            ("foo.section",
                ovirt.node.plugins.Header("Subsection")),
            ("foo.hostname",
                ovirt.node.plugins.Entry(label="Hostname")),
            ("foo.port",
                ovirt.node.plugins.Entry(label="Port")),
            ("foo.password",
                ovirt.node.plugins.PasswordEntry(label="Password")),
        ]
        self._widgets = dict(widgets)
        return widgets

    def on_change(self, changes):
        """Applies the changes to the plugins model, will do all required logic
        """
        LOGGER.debug("checking %s" % changes)
        if "foo.hostname" in changes:
            LOGGER.debug("Found foo.hostname")

            if "/" in changes["foo.hostname"]:
                raise ovirt.node.plugins.InvalidData("No slash allowed")

            if len(changes["foo.hostname"]) < 5:
                raise ovirt.node.plugins.Concern("Should be at least 5 chars")

            self._model.update(changes)

            if "dis" in changes["foo.hostname"]:
                self._widgets["foo.port"].enabled(False)
                LOGGER.debug("change to dis")
                self._widgets["foo.section"].text(changes["foo.hostname"])
                #raise ovirt.node.plugins.ContentRefreshRequest()
            else:
                self._widgets["foo.port"].enabled(True)

        if "foo.port" in changes:
            LOGGER.debug("Found foo.port")

            if "/" in changes["foo.port"]:
                raise ovirt.node.plugins.InvalidData("No slashes allowed")

        return True

    def on_merge(self, effective_changes):
        """Applies the changes to the plugins model, will do all required logic
        """
        LOGGER.debug("saving %s" % effective_changes)
        # Look for conflicts etc
        self._model.update(effective_changes)
