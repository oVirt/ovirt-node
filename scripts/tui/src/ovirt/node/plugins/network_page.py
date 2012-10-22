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

    _model = {
        "hostname": "localhost.example.com",
        "dns[0]": "192.168.122.1",
        "dns[1]": "",
        "ntp[0]": "fedora.pool.ntp.org",
        "ntp[1]": "",
    }
    _widgets = None

    def name(self):
        return "Network"

    def rank(self):
        return 10

    def model(self):
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
                ovirt.node.ui.Entry("Hostname:")),
            ("hostname._space", ovirt.node.ui.Divider()),

            ("nics", ovirt.node.ui.Table(
                        "Device   Status         Model    MAC Address",
                        self._get_nics())),
            ("nics._space", ovirt.node.ui.Divider()),

            ("dns[0]", ovirt.node.ui.Entry("DNS Server 1:")),
            ("dns[1]", ovirt.node.ui.Entry("DNS Server 2:")),
            ("dns._space", ovirt.node.ui.Divider()),

            ("ntp[0]", ovirt.node.ui.Entry("NTP Server 1:")),
            ("ntp[1]", ovirt.node.ui.Entry("NTP Server 2:")),
            ("ntp._space", ovirt.node.ui.Divider()),
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
        first_nic = None
        for name, nic in ovirt.node.utils.network.node_nics().items():
            if first_nic == None:
                first_nic = name
            bootproto = "Configured" if nic["bootproto"] else "Unconfigured"
            description = " ".join([
                justify(nic["name"], 8),
                justify(bootproto, 14),
                justify(nic["driver"], 8),
                justify(nic["hwaddr"], 17)
                ])
            node_nics.append((name, description))
        self._model["nics"] = first_nic
        return node_nics

    def _build_dialog(self, path, txt, widgets):
        self._widgets.update(dict(widgets))
        self._widgets[path] = ovirt.node.ui.Dialog(txt, widgets)
        return self._widgets[path]

    def _build_nic_details_dialog(self):
        # Populate model with nic specific informations
        iface = self._model["nics"]
        LOGGER.debug("Getting informations for NIC details page")
        info = ovirt.node.utils.network.node_nics(with_live=True)[iface]

        self._model.update({
            "dialog.nic.iface": info["name"],
            "dialog.nic.driver": info["driver"],
            "dialog.nic.protocol": info["bootproto"] or "N/A",
            "dialog.nic.vendor": info["vendor"],
            "dialog.nic.link_status": "Connected" if info["link_detected"]
                                                  else "Disconnected",
            "dialog.nic.hwaddress": info["hwaddr"],
            "dialog.nic.ipv4.bootproto": info["bootproto"],
            "dialog.nic.ipv4.address": info["ipaddr"] or "",
            "dialog.nic.ipv4.netmask": info["netmask"] or "",
            "dialog.nic.ipv4.gateway": info["gateway"] or "",
            "dialog.nic.vlanid": "none",
        })

        padd = lambda l: l.ljust(14)
        return self._build_dialog("dialog.nic", "NIC Details: %s" % iface, [
            ("dialog.nic._row[0]", ovirt.node.ui.Row([
                ("dialog.nic.iface",
                    ovirt.node.ui.KeywordLabel(padd("Interface: "))),
                ("dialog.nic.driver",
                    ovirt.node.ui.KeywordLabel(padd("Driver: "))),
                ])),

            ("dialog.nic._row[1]", ovirt.node.ui.Row([
                ("dialog.nic.protocol",
                    ovirt.node.ui.KeywordLabel(padd("Protocol: "))),
                ("dialog.nic.vendor",
                    ovirt.node.ui.KeywordLabel(padd("Vendor: "))),
                ])),

            ("dialog.nic._row[2]", ovirt.node.ui.Row([
                ("dialog.nic.link_status",
                    ovirt.node.ui.KeywordLabel(padd("Link Status: "))),
                ("dialog.nic.hwaddress",
                    ovirt.node.ui.KeywordLabel(padd("MAC Address: "))),
                ])),

            ("dialog.nic._divider[0]", ovirt.node.ui.Divider()),

            ("dialog.nic.ipv4._header", ovirt.node.ui.Header("IPv4 Settings")),
            ("dialog.nic.ipv4.bootproto", ovirt.node.ui.Options(
                "Bootprotocol: ", [
                    ("none", "Disabled"),
                    ("dhcp", "DHCP"),
                    ("static", "Static")
                ])),
            ("dialog.nic.ipv4.address",
                    ovirt.node.ui.Entry(padd("IP Address: "))),
            ("dialog.nic.ipv4.netmask",
                    ovirt.node.ui.Entry(padd("Netmask: "))),
            ("dialog.nic.ipv4.gateway",
                    ovirt.node.ui.Entry(padd("Gateway: "))),

            ("dialog.nic._divider[1]", ovirt.node.ui.Divider()),

            ("dialog.nic.vlanid",
                    ovirt.node.ui.Entry(padd("VLAN ID: "))),
        ])

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        effective_model = dict(self._model)
        effective_model.update(effective_changes)
        LOGGER.info("effm %s" % effective_model)
        LOGGER.info("effc %s" % effective_changes)
        LOGGER.info("allc %s" % changes)

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

        if "nics" in changes:
            iface = changes["nics"]
            LOGGER.debug("Opening NIC Details dialog for '%s'" % iface)
            return self._build_nic_details_dialog()
