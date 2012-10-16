#!/usr/bin/python
#
# status.py - Copyright (C) 2012 Red Hat, Inc.
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
Network plugin
"""
import logging

import ovirt.node.plugins
import ovirt.node.valid
import ovirt.node.ui
import ovirt.node.utils
import ovirt.node.utils.network

LOGGER = logging.getLogger(__name__)


class Plugin(ovirt.node.plugins.NodePlugin):
    """This is the network page
    """

    _model = None
    _widgets = None

    def name(self):
        return "Network"

    def rank(self):
        return 10

    def model(self):
        if not self._model:
            self._model = {
                "hostname": "localhost.example.com",
                "dns[0]": "192.168.122.1",
                "dns[1]": "",
                "ntp[0]": "fedora.pool.ntp.org",
                "ntp[1]": "",
            }

        nameservers = ovirt.node.utils.network.nameservers()
        for idx, nameserver in enumerate(nameservers):
            self._model["dns[%d]" % idx] = nameserver

        timeservers = ovirt.node.utils.network.timeservers()
        for idx, timeserver in enumerate(timeservers):
            self._model["ntp[%d]" % idx] = timeserver

        return self._model

    def validators(self):
        Empty = ovirt.node.valid.Empty
        ip_or_empty = ovirt.node.valid.IPAddress() | Empty()
        fqdn_ip_or_empty = ovirt.node.valid.FQDNOrIPAddress() | Empty()
        return {
                "hostname": ovirt.node.valid.FQDNOrIPAddress(),
                "dns[0]": ovirt.node.valid.IPAddress(),
                "dns[1]": ip_or_empty,
                "ntp[0]": ovirt.node.valid.FQDNOrIPAddress(),
                "ntp[1]": fqdn_ip_or_empty,
            }

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        widgets = [
            ("hostname",
                ovirt.node.ui.Entry("Hostname")),
            ("hostname._space", ovirt.node.ui.Divider()),

            ("nics", ovirt.node.ui.Table(
                        "Device   Status         Model    MAC Address",
                        self._get_nics())),
            ("nics._space", ovirt.node.ui.Divider()),

            ("dns[0]", ovirt.node.ui.Entry("DNS Server 1")),
            ("dns[1]", ovirt.node.ui.Entry("DNS Server 2")),
            ("dns._space", ovirt.node.ui.Divider()),

            ("ntp[0]", ovirt.node.ui.Entry("NTP Server 1")),
            ("ntp[1]", ovirt.node.ui.Entry("NTP Server 2")),
            ("ntp._space", ovirt.node.ui.Divider()),

#            ("action", ovirt.node.ui.Buttons(["Lock", "Log Off", "Restart",
#                                              "Power Off"])),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        return page

    def _get_nics(self):
        justify = lambda txt, l: txt.ljust(l)[0:l]
        node_nics = [
                ("em1",
                    "em1      Configured     e1000    00:11:22:33:44:55"),
                ("p1p6",
                    "p1p6     Unconfigured   bnx2     10:21:32:43:54:65"),
                ]
        node_nics = []
        for name, nic in ovirt.node.utils.network.node_nics().items():
            bootproto = "Configured" if nic["bootproto"] else "Unconfigured"
            description = " ".join([
                justify(nic["name"], 8),
                justify(bootproto, 14),
                justify(nic["driver"], 8),
                justify(nic["hwaddr"], 17)
                ])
            node_nics.append((name, description))
        return node_nics

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        effective_model = self._model.update(effective_changes)

        if "dns[0]" in effective_changes or \
           "dns[1]" in effective_changes:
            new_servers = [v for k, v in effective_model \
                             if k.startswith("dns[")]
            LOGGER.info("Setting new nameservers: %s" % new_servers)
            ovirt.node.utils.network.nameservers(new_servers)

        if "ntp[0]" in effective_changes or \
           "ntp[1]" in effective_changes:
            new_servers = [v for k, v in effective_model \
                             if k.startswith("ntp[")]
            LOGGER.info("Setting new timeservers: %s" % new_servers)
            ovirt.node.utils.network.timeservers(new_servers)
