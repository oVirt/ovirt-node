#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# network_page.py - Copyright (C) 2012 Red Hat, Inc.
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
from ovirt.node import plugins, ui, valid, utils
from ovirt.node.config import defaults
from ovirt.node.plugins import Changeset
from ovirt.node.utils import network
"""
Network page plugin
"""


class Plugin(plugins.NodePlugin):
    """This is the network page
    """

    _widgets = None
    _model_extra = {}

    def __init__(self, app):
        super(Plugin, self).__init__(app)
        self._widgets = plugins.WidgetsHelper()

            # Keys/Paths to widgets related to NIC settings
        self._nic_details_group = self._widgets.group([
                                                "dialog.nic.ipv4.bootproto",
                                                "dialog.nic.ipv4.address",
                                                "dialog.nic.ipv4.netmask",
                                                "dialog.nic.ipv4.gateway",
                                                "dialog.nic.vlanid"])

    def name(self):
        return "Network"

    def rank(self):
        return 10

    def model(self):
        model = {
            "hostname": "",
            "dns[0]": "",
            "dns[1]": "",
            "ntp[0]": "",
            "ntp[1]": "",
        }

        model["hostname"] = defaults.Hostname().retrieve()["hostname"] or \
                            network.hostname()

        # Pull name-/timeservers from config files (not defaults)
        nameservers = defaults.Nameservers().retrieve()["servers"]
        if nameservers:
            for idx, nameserver in enumerate(nameservers):
                model["dns[%d]" % idx] = nameserver

        timeservers = defaults.Timeservers().retrieve()["servers"]
        if timeservers:
            for idx, timeserver in enumerate(timeservers):
                model["ntp[%d]" % idx] = timeserver

        model.update(self._model_extra)

        return model

    def validators(self):
        ip_or_empty = valid.IPAddress() | valid.Empty()
        fqdn_ip_or_empty = valid.FQDNOrIPAddress() | valid.Empty()

        return {
                "hostname": fqdn_ip_or_empty,
                "dns[0]": ip_or_empty,
                "dns[1]": ip_or_empty,
                "ntp[0]": fqdn_ip_or_empty,
                "ntp[1]": fqdn_ip_or_empty,

                "dialog.nic.ipv4.address": valid.IPv4Address() | valid.Empty(),
                "dialog.nic.ipv4.netmask": valid.IPv4Address() | valid.Empty(),
                "dialog.nic.ipv4.gateway": valid.IPv4Address() | valid.Empty(),
                "dialog.nic.vlanid": (valid.Number(range=[0, 4096]) |
                                      valid.Empty()),
            }

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        widgets = [
            ("headers[0]", ui.Header("System Identification")),
            ("hostname", ui.Entry("Hostname:")),
            ("hostname._space", ui.Divider()),

            ("dns[0]", ui.Entry("DNS Server 1:")),
            ("dns[1]", ui.Entry("DNS Server 2:")),
            ("dns._space", ui.Divider()),

            ("ntp[0]", ui.Entry("NTP Server 1:")),
            ("ntp[1]", ui.Entry("NTP Server 2:")),
            ("ntp._space", ui.Divider()),

            ("nics", ui.Table("Available System NICs",
                        "Device   Status         Model          MAC Address",
                        self._get_nics())),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets.update(dict(widgets))

        page = ui.Page(widgets)
        return page

    def _get_nics(self):
        justify = lambda txt, l: txt.ljust(l)[0:l]
        node_nics = []
        first_nic = None
        for name, nic in sorted(utils.network.node_nics().items()):
            if first_nic == None:
                first_nic = name
            bootproto = "Configured" if nic["bootproto"] else "Unconfigured"
            description = " ".join([
                justify(nic["name"], 8),
                justify(bootproto, 14),
                justify(nic["vendor"], 14),
                justify(nic["hwaddr"], 17)
                ])
            node_nics.append((name, description))
        return node_nics

    def _build_dialog(self, path, txt, widgets):
        self._widgets.update(dict(widgets))
        self._widgets[path] = ui.Dialog(txt, widgets)
        return self._widgets[path]

    def _build_nic_details_dialog(self, iface):
        # Populate model with nic specific informations
        self.logger.debug("Building NIC details dialog for %s" % iface)

        self.logger.debug("Getting informations for NIC details page")
        live = utils.network.node_nics()[iface]
        cfg = defaults.Network().retrieve()

        self.logger.debug("live: %s" % live)
        self.logger.debug("cfg: %s" % cfg)

        if cfg["iface"] != iface:
            # create empty config if we are not editing the bootif
            cfg = {k: "" for k in cfg.keys()}

        ipaddr, netmask, gateway, vlanid = (cfg["ipaddr"], cfg["netmask"],
                                            cfg["gateway"], cfg["vlanid"])

        if cfg["bootproto"] == "dhcp":
            nic = utils.network.NIC(live["bridge"])
            routes = utils.network.Routes()
            ipaddr, netmask, gateway, vlanid = (nic.ipv4_address().items() +
                                               (routes.default(),) +
                                               (nic.vlanid(),))

        self._model_extra.update({
            "dialog.nic.iface": live["name"],
            "dialog.nic.driver": live["driver"],
            "dialog.nic.protocol": live["bootproto"] or "N/A",
            "dialog.nic.vendor": live["vendor"],
            "dialog.nic.link_status": "Connected" if live["link_detected"]
                                                  else "Disconnected",
            "dialog.nic.hwaddress": live["hwaddr"],

            "dialog.nic.ipv4.bootproto": cfg["bootproto"],
            "dialog.nic.ipv4.address": ipaddr,
            "dialog.nic.ipv4.netmask": netmask,
            "dialog.nic.ipv4.gateway": gateway,
            "dialog.nic.vlanid": vlanid,
        })

        self.logger.debug("model: %s" % self.model())

        padd = lambda l: l.ljust(14)
        dialog = self._build_dialog("dialog.nic", "NIC Details: %s" % iface, [
            ("dialog.nic._row[0]", ui.Row([
                ("dialog.nic.iface",
                    ui.KeywordLabel(padd("Interface: "))),
                ("dialog.nic.driver",
                    ui.KeywordLabel(padd("Driver: "))),
                ])),

            ("dialog.nic._row[1]", ui.Row([
                ("dialog.nic.protocol",
                    ui.KeywordLabel(padd("Protocol: "))),
                ("dialog.nic.vendor",
                    ui.KeywordLabel(padd("Vendor: "))),
                ])),

            ("dialog.nic._row[2]", ui.Row([
                ("dialog.nic.link_status",
                    ui.KeywordLabel(padd("Link Status: "))),
                ("dialog.nic.hwaddress",
                    ui.KeywordLabel(padd("MAC Address: "))),
                ])),

            ("dialog.nic._divider[0]", ui.Divider()),

            ("dialog.nic.ipv4._header", ui.Header("IPv4 Settings")),
            ("dialog.nic.ipv4.bootproto", ui.Options(
                "Bootprotocol: ", [
                    ("none", "Disabled"),
                    ("dhcp", "DHCP"),
                    ("static", "Static")
                ])),
            ("dialog.nic.ipv4.address",
                    ui.Entry(padd("IP Address: "))),
            ("dialog.nic.ipv4.netmask",
                    ui.Entry(padd("Netmask: "))),
            ("dialog.nic.ipv4.gateway",
                    ui.Entry(padd("Gateway: "))),

            ("dialog.nic._divider[1]", ui.Divider()),

            ("dialog.nic.vlanid",
                    ui.Entry(padd("VLAN ID: "))),

            ("dialog.nic._buttons", ui.Row([
                ("dialog.nic.save",
                        ui.Button("Save & Close")),
                ("dialog.nic.close",
                        ui.Button("Close")),
            ]))
        ])

        dialog.buttons = []

        self._nic_details_group.enabled(False)

        return dialog

    def on_change(self, changes):
        self.logger.info("Checking network stuff")
        helper = plugins.Changeset(changes)
        bootproto = helper["dialog.nic.ipv4.bootproto"]
        if bootproto:
            if bootproto in ["static"]:
                self._nic_details_group.enabled(True)
            else:
                self._nic_details_group.enabled(False)
            self._widgets["dialog.nic.ipv4.bootproto"].enabled(True)

    def on_merge(self, effective_changes):
        self.logger.info("Saving network stuff")
        changes = Changeset(self.pending_changes(False))
        effective_model = Changeset(self.model())
        effective_model.update(effective_changes)

        self.logger.debug("Changes: %s" % changes)
        self.logger.info("Effective changes %s" % effective_changes)
        self.logger.debug("Effective Model: %s" % effective_model)

        # Special case: A NIC was selected, display that dialog!
        if "nics" in changes and len(changes) == 1:
            iface = changes["nics"]
            self.logger.debug("Opening NIC Details dialog for '%s'" % iface)
            self._nic_dialog = self._build_nic_details_dialog(iface)
            return self._nic_dialog

        if "dialog.nic.close" in changes:
            self._nic_dialog.close()
            return

        if "dialog.nic.save" in changes:
            self.logger.debug("Save and close NIC")
            self._nic_dialog.close()

        # This object will contain all transaction elements to be executed
        txs = utils.Transaction("DNS and NTP configuration")

        e_changes_h = plugins.Changeset(effective_changes)

        nameservers = []
        dns_keys = ["dns[0]", "dns[1]"]
        if e_changes_h.contains_any(dns_keys):
            nameservers += effective_model.values_for(dns_keys)
        if nameservers:
            self.logger.info("Setting new nameservers: %s" % nameservers)
            model = defaults.Nameservers()
            model.update(nameservers)
            txs += model.transaction()

        timeservers = []
        ntp_keys = ["ntp[0]", "ntp[1]"]
        if e_changes_h.contains_any(ntp_keys):
            timeservers += effective_model.values_for(ntp_keys)
        if timeservers:
            self.logger.info("Setting new timeservers: %s" % timeservers)
            model = defaults.Timeservers()
            model.update(timeservers)
            txs += model.transaction()

        hostname_keys = ["hostname"]
        if e_changes_h.contains_any(hostname_keys):
            value = effective_model.values_for(hostname_keys)
            self.logger.info("Setting new hostname: %s" % value)
            model = defaults.Hostname()
            model.update(*value)
            txs += model.transaction()

        # For the NIC details dialog:
        if e_changes_h.contains_any(self._nic_details_group):
            # If any networking related key was changed, reconfigure networking
            # Fetch the values for the nic keys, they are used as arguments
            args = effective_model.values_for(self._nic_details_group)
            txs += self._configure_nic(*args)

        progress_dialog = ui.TransactionProgressDialog(txs, self)
        progress_dialog.run()

        # Behaves like a page reload
        return self.ui_content()

    def _configure_nic(self, bootproto, ipaddr, netmask, gateway, vlanid):
        vlanid = vlanid or None
        model = defaults.Network()
        iface = self._model_extra["dialog.nic.iface"]
        if bootproto == "none":
            self.logger.debug("Configuring no networking")
            name = iface + "-DISABLED"
            model.update(name, None, None, None, None, None)
        elif bootproto == "dhcp":
            self.logger.debug("Configuring dhcp")
            model.update(iface, "dhcp", None, None, None, vlanid)
        elif bootproto == "static":
            self.logger.debug("Configuring static ip")
            model.update(iface, "static", ipaddr, netmask, gateway, vlanid)
        else:
            self.logger.debug("No interface configuration found")
        # Return the resulting transaction
        return model.transaction()
