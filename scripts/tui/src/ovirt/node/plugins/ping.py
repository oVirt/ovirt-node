"""
A ping tool page
"""
import logging

import ovirt.node.plugins
import ovirt.node.valid
from ovirt.node.plugins import Header, Label, Entry, PasswordEntry
import ovirt.node.utils

LOGGER = logging.getLogger(__name__)


class Plugin(ovirt.node.plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Tools (ping)"

    def model(self):
        """Returns the model of this plugin
        This is expected to parse files and all stuff to build up the model.
        """
        if not self._model:
            self._model = {
                # The target address
                "ping.address": "127.0.0.1",
                "ping.count": "3",
                # The result field
                "ping.result": ""
            }
        return self._model

    def validators(self):
        """Validators validate the input on change and give UI feedback
        """
        return {
                # The address must be fqdn, ipv4 or ipv6 address
                "ping.address": ovirt.node.valid.FQDNOrIPAddress(),
                "ping.count": ovirt.node.valid.Number(min=1, max=20),
            }

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        widgets = [
            ("ping.header", Header("Ping a remote host")),
            ("ping.address", Entry("Address")),
            ("ping.count", Entry("Count")),
            ("ping.result", Label("Result:")),
        ]
        self._widgets = dict(widgets)
        return widgets

    def on_change(self, changes):
        """Applies the changes to the plugins model, will do all required logic
        """
        LOGGER.debug("New (valid) address: %s" % changes)
        if "ping.address" in changes:
            self._model.update(changes)
        if "ping.count" in changes:
            self._model.update(changes)

    def on_merge(self, changes):
        """Applies the changes to the plugins model, will do all required logic
        """

        if "ping.address" in self._model:
            addr = self._model["ping.address"]
            count = self._model["ping.count"]
            LOGGER.debug("Pinging %s" % addr)

            cmd = "ping"
            if ovirt.node.valid.IPv6Address().validate(addr):
                cmd = "ping6"

            cmd = "%s -c %s %s" % (cmd, count, addr)
            out = cmd
            for line in ovirt.node.utils.pipe_async(cmd):
                LOGGER.debug("xx" + line)
                out += line
                self._widgets["ping.result"].text("Result:\n\n%s" % out)
