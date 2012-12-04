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
"""
Network page plugin
"""

from ovirt.node import plugins, ui, valid, utils
from ovirt.node.config import defaults
import ovirt.node.utils.network
import time


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
        # Pull name-/timeservers from config files (not defaults)
        nameservers = defaults.Nameservers().retrieve()["servers"]
        if nameservers:
            for idx, nameserver in enumerate(nameservers):
                self._model["dns[%d]" % idx] = nameserver

        timeservers = defaults.Timeservers().retrieve()["servers"]
        if timeservers:
            for idx, timeserver in enumerate(timeservers):
                self._model["ntp[%d]" % idx] = timeserver

        return self._model

    def validators(self):
        ip_or_empty = valid.IPAddress() | valid.Empty()
        fqdn_ip_or_empty = valid.FQDNOrIPAddress() | valid.Empty()

        return {
                "hostname": valid.FQDNOrIPAddress(),
                "dns[0]": valid.IPAddress(),
                "dns[1]": ip_or_empty,
                "ntp[0]": valid.FQDNOrIPAddress(),
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
        for name, nic in sorted(ovirt.node.utils.network.node_nics().items()):
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
        self._model["nics"] = first_nic
        return node_nics

    def _build_dialog(self, path, txt, widgets):
        self._widgets.update(dict(widgets))
        self._widgets[path] = ui.Dialog(txt, widgets)
        return self._widgets[path]

    def _build_nic_details_dialog(self):
        self.logger.debug("Building NIC details dialog")
        # Populate model with nic specific informations
        iface = self._model["nics"]

        self.logger.debug("Getting informations for NIC details page")
        live = ovirt.node.utils.network.node_nics()[iface]
        cfg = defaults.Network().retrieve()

        self.logger.debug("live: %s" % live)
        self.logger.debug("cfg: %s" % cfg)

        ipaddr, netmask, gateway, vlanid = (cfg["ipaddr"], cfg["netmask"],
                                            cfg["gateway"], cfg["vlanid"])

        if cfg["bootproto"] == "dhcp":
            nic = utils.network.NIC(live["bridge"])
            routes = utils.network.Routes()
            ipaddr, netmask, gateway, vlanid = (nic.ipv4_address().items() +
                                               (routes.default(),) +
                                               (nic.vlanid(),))

        self._model.update({
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

        self.logger.debug("model: %s" % self._model)

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
        helper = plugins.ChangesHelper(changes)
        bootproto = helper["dialog.nic.ipv4.bootproto"]
        if bootproto:
            if bootproto in ["static"]:
                self._nic_details_group.enabled(True)
            else:
                self._nic_details_group.enabled(False)
            self._widgets["dialog.nic.ipv4.bootproto"].enabled(True)

    def on_merge(self, effective_changes):
        self.logger.info("Saving network stuff")
        changes = self.pending_changes(False)
        effective_model = dict(self._model)
        effective_model.update(effective_changes)
        self.logger.info("Effective model %s" % effective_model)
        self.logger.info("Effective changes %s" % effective_changes)
        self.logger.info("All changes %s" % changes)

        # Special case: A NIC was selected, display that dialog!
        if "nics" in changes and len(changes) == 1:
            iface = changes["nics"]
            self.logger.debug("Opening NIC Details dialog for '%s'" % iface)
            self._nic_dialog = self._build_nic_details_dialog()
            return self._nic_dialog

        if "dialog.nic.close" in changes:
            self._nic_dialog.close()
            return

        if "dialog.nic.save" in changes:
            self.logger.debug("Save and close NIC")
            self._nic_dialog.close()

        def set_progress(txt):
            set_progress.txt += txt + "\n"
            progress.set_text(set_progress.txt)
        set_progress.txt = "Applying changes ...\n"

        progress = ui.Label(set_progress.txt)
        _d = self._build_dialog("dialog.dia",
                                                               "fooo", [
            ("dialog.dia.text[0]", progress),
            ])
        _d.buttons = []
        d = self.application.ui.show_dialog(_d)

        # This object will contain all transaction elements to be executed
        txs = utils.Transaction("DNS and NTP configuration")

        e_changes_h = plugins.ChangesHelper(effective_changes)
        e_model_h = plugins.ChangesHelper(effective_model)

        nameservers = []
        dns_keys = ["dns[0]", "dns[1]"]
        if e_changes_h.any_key_in_change(dns_keys):
            nameservers += e_model_h.get_key_values(dns_keys)
        if nameservers:
            self.logger.info("Setting new nameservers: %s" % nameservers)
            model = defaults.Nameservers()
            model.update(nameservers)
            txs += model.transaction()

        timeservers = []
        ntp_keys = ["ntp[0]", "ntp[1]"]
        if e_changes_h.any_key_in_change(ntp_keys):
            timeservers += e_model_h.get_key_values(ntp_keys)
        if timeservers:
            self.logger.info("Setting new timeservers: %s" % timeservers)
            model = defaults.Timeservers()
            model.update(timeservers)
            txs += model.transaction()

        # For the NIC details dialog:
        if e_changes_h.any_key_in_change(self._nic_details_group):
            # If any networking related key was changed, reconfigure networking
            helper = plugins.ChangesHelper(effective_model)
            # Fetch the values for the nic keys, they are used as arguments
            args = helper.get_key_values(self._nic_details_group)
            txs += self._configure_nic(*args)

        # Commit all outstanding transactions
        txs.prepare()  # Just to display something in dry mode
        for idx, e in enumerate(txs):
            n = "(%s/%s) " % (idx + 1, len(txs))
            set_progress(n + e.title)
            self.dry_or(lambda: e.commit())

        set_progress("All changes were applied.")
        time.sleep(3)
        d.close()

        # Behaves like a page reload
        return self.ui_content()

    def _configure_nic(self, bootproto, ipaddr, netmask, gateway, vlanid):
        vlanid = vlanid or None
        model = defaults.Network()
        iface = self._model["dialog.nic.iface"]
        if bootproto == "none":
            self.logger.debug("Configuring no networking")
            name = iface + "-DISABLED"
            model.update(name, None, None, None, None, None)
        elif bootproto == "dhcp":
            self.logger.debug("Configuring dhcp")
            model.update(iface, "dhcp", None, None, None, vlanid)
        elif bootproto == "static":
            self.logger.debug("Configuring static ip")
            model.update(iface, "none", ipaddr, netmask, gateway, vlanid)
        else:
            self.logger.debug("No interface configuration found")
        # Return the resulting transaction
        return model.transaction()
