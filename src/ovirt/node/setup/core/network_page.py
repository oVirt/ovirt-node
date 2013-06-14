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
from ovirt.node import plugins, ui, valid, utils, config
from ovirt.node.config import defaults
from ovirt.node.plugins import Changeset
from ovirt.node.setup.core import ping
from ovirt.node.utils import network

"""
Network page plugin

TODO use inotify+thread or so to monitor resolv.conf/ntp.conf for changes and
     update UI
"""


class Plugin(plugins.NodePlugin):
    """This is the network page
    """
    _model_extra = {}

    def __init__(self, app):
        super(Plugin, self).__init__(app)

            # Keys/Paths to widgets related to NIC settings
        self._nic_details_group = self.widgets.group([
            "dialog.nic.ipv4.bootproto", "dialog.nic.ipv4.address",
            "dialog.nic.ipv4.netmask", "dialog.nic.ipv4.gateway",
            "dialog.nic.ipv6.bootproto", "dialog.nic.ipv6.address",
            "dialog.nic.ipv6.netmask", "dialog.nic.ipv6.gateway",
            "dialog.nic.vlanid",
            "dialog.nic.layout_bridged"])

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
        nameservers = config.network.nameservers()
        if nameservers:
            for idx, nameserver in enumerate(nameservers):
                model["dns[%d]" % idx] = nameserver

        timeservers = config.network.timeservers()
        if timeservers:
            for idx, timeserver in enumerate(timeservers):
                model["ntp[%d]" % idx] = timeserver

        model.update(self._model_extra)

        return model

    def validators(self):
        ip_or_empty = valid.IPAddress() | valid.Empty()
        fqdn_ip_or_empty = valid.FQDNOrIPAddress() | valid.Empty()

        return {"hostname": fqdn_ip_or_empty,
                "dns[0]": ip_or_empty,
                "dns[1]": ip_or_empty,
                "ntp[0]": fqdn_ip_or_empty,
                "ntp[1]": fqdn_ip_or_empty,

                "dialog.nic.ipv4.address": valid.IPv4Address() | valid.Empty(),
                "dialog.nic.ipv4.netmask": valid.IPv4Address() | valid.Empty(),
                "dialog.nic.ipv4.gateway": valid.IPv4Address() | valid.Empty(),
                "dialog.nic.ipv6.address": valid.IPv6Address() | valid.Empty(),
                "dialog.nic.ipv6.netmask": valid.IPv6Address() | valid.Empty(),
                "dialog.nic.ipv6.gateway": valid.IPv6Address() | valid.Empty(),
                "dialog.nic.vlanid": (valid.Number(bounds=[0, 4096]) |
                                      valid.Empty()),
                }

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        ws = [ui.Header("header[0]", "System Identification"),
              ui.Entry("hostname", "Hostname:"),
              ui.Divider("divider[0]"),
              ui.Entry("dns[0]", "DNS Server 1:"),
              ui.Entry("dns[1]", "DNS Server 2:"),
              ui.Divider("divider[1]"),
              ui.Entry("ntp[0]", "NTP Server 1:"),
              ui.Entry("ntp[1]", "NTP Server 2:"),
              ui.Divider("divider[2]"),
              ui.Table("nics", "Available System NICs",
                       "Device  Status        Model          MAC Address",
                       self._get_nics()),
              ui.Button("button.ping", "Ping")
              ]

        page = ui.Page("page", ws)
        # Save it "locally" as a dict, for better accessability
        self.widgets.add(page)
        return page

    def _get_nics(self):
        def justify(txt, l):
            txt = txt if txt else ""
            return txt.ljust(l)[0:l]
        node_nics = []
        first_nic = None
        model = utils.network.NodeNetwork()
        for name, nic in sorted(model.nics().items()):
            if first_nic is None:
                first_nic = name
            is_cfg = "Configured" if nic.is_configured() else "Unconfigured"
            description = " ".join([justify(nic.ifname, 7),
                                    justify(is_cfg, 13),
                                    justify(nic.vendor, 14),
                                    justify(nic.hwaddr, 17)
                                    ])
            node_nics.append((name, description))
        return node_nics

    def _build_dialog(self, path, txt, widgets):
        self.widgets.add(widgets)
        self.widgets.add(ui.Dialog(path, txt, widgets))
        return self.widgets[path]

    def on_change(self, changes):
        self.logger.info("Checking network stuff")
        helper = plugins.Changeset(changes)
        nic_ipv4_group = ["dialog.nic.ipv4.bootproto",
                          "dialog.nic.ipv4.address",
                          "dialog.nic.ipv4.netmask",
                          "dialog.nic.ipv4.gateway"]

        nic_ipv6_group = ["dialog.nic.ipv6.bootproto",
                          "dialog.nic.ipv6.address",
                          "dialog.nic.ipv6.netmask",
                          "dialog.nic.ipv6.gateway"]

        ipv4_bootproto = helper["dialog.nic.ipv4.bootproto"]
        if ipv4_bootproto:
            if ipv4_bootproto in ["static"]:
                for w in nic_ipv4_group:
                    self.widgets[w].enabled(True)
            elif ipv4_bootproto in ["dhcp"]:
                for w in nic_ipv4_group:
                    self.widgets[w].enabled(False)
                    self.widgets["dialog.nic.vlanid"].enabled(True)
            else:
                for w in nic_ipv4_group:
                    self.widgets[w].enabled(False)
                    self.widgets["dialog.nic.vlanid"].enabled(True)
            self.widgets["dialog.nic.ipv4.bootproto"].enabled(True)

        ipv6_bootproto = helper["dialog.nic.ipv6.bootproto"]
        if ipv6_bootproto:
            if ipv6_bootproto in ["static"]:
                for w in nic_ipv6_group:
                    self.widgets[w].enabled(True)
            elif ipv6_bootproto in ["dhcp"]:
                for w in nic_ipv6_group:
                    self.widgets[w].enabled(False)
                    self.widgets["dialog.nic.vlanid"].enabled(True)
            else:
                for w in nic_ipv6_group:
                    self.widgets[w].enabled(False)
                    self.widgets["dialog.nic.vlanid"].enabled(True)
            self.widgets["dialog.nic.ipv6.bootproto"].enabled(True)

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
            self._model_extra["dialog.nic.ifname"] = iface
            self._nic_dialog = NicDetailsDialog(self, iface)
            return self._nic_dialog

        if "dialog.nic.close" in changes:
            self._nic_dialog.close()
            return

        if "button.ping" in changes:
            self.logger.debug("Opening ping page")
            self.application.switch_to_plugin(ping.Plugin)
            return

        if "dialog.nic.identify" in changes:
            ifname = self._model_extra["dialog.nic.ifname"]
            utils.network.NIC(ifname).identify()
            self.application.notice("Flashing lights now")
            return

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

        progress_dialog = ui.TransactionProgressDialog("dialog.txs", txs, self)
        progress_dialog.run()

        if "dialog.nic.save" in changes:
            # Close the remaing details dialog
            self._nic_dialog.close()

        # Behaves like a page reload
        return self.ui_content()

    def _configure_nic(self, bootproto, ipaddr, netmask, gateway,
                       ipv6_bootproto, ipv6_address, ipv6_netmask,
                       ipv6_gateway, vlanid, layout_bridged):
        vlanid = vlanid or None
        iface = self._model_extra["dialog.nic.ifname"]

        model = defaults.Network()
        ipv6model = defaults.IPv6()

        if bootproto == "none":
            self.logger.debug("Configuring no networking")
            model.configure_no_networking(iface)
        elif bootproto == "dhcp":
            self.logger.debug("Configuring dhcp")
            model.configure_dhcp(iface, vlanid)
        elif bootproto == "static":
            self.logger.debug("Configuring static ip")
            model.configure_static(iface, ipaddr, netmask, gateway, vlanid)
        else:
            self.logger.debug("No ipv4 interface configuration found")

        # A hack to also set the BOOTIF when IPv& is used in a second
        enable_bootif = lambda: model.update(iface=iface)

        if ipv6_bootproto == "none":
            self.logger.debug("Configuring no ipv6 networking")
            ipv6model.disable()

        elif ipv6_bootproto == "dhcp":
            self.logger.debug("Configuring ipv6 dhcp")
            enable_bootif()
            ipv6model.configure_dhcp()

        elif ipv6_bootproto == "auto":
            self.logger.debug("Configuring ipv6 auto")
            enable_bootif()
            ipv6model.configure_auto()

        elif ipv6_bootproto == "static":
            self.logger.debug("Configuring ipv6 static ip")
            enable_bootif()
            ipv6model.configure_static(ipv6_address, ipv6_netmask,
                                       ipv6_gateway)
        else:
            self.logger.debug("No ipv6 interface configuration found")

        mt = defaults.NetworkLayout()
        if layout_bridged:
            mt.configure_bridged()

        # Return the resulting transaction
        txs = model.transaction()

        # FIXME the ipv6 transaction is IDENTICAL to the model.tranasaction()
        # (just a call to the legacy code to reconfigure networking)
        # Therefor we don't add it, to not call it twice.
        # But it should be added to the ocmplete transaction when the backend
        # code is more fine granular.
        #txs += ipv6model.transaction()
        return txs


class NicDetailsDialog(ui.Dialog):
    plugin = None

    def __init__(self, plugin, ifname):
        super(NicDetailsDialog, self).__init__("dialog.nic",
                                               "NIC Details: %s" % ifname, [])
        self.plugin = plugin

        # Populate model with nic specific informations
        self.logger.debug("Building NIC details dialog for %s" % ifname)

        nic = utils.network.NodeNetwork().nics()[ifname]

        model = defaults.Network().retrieve()
        ip6model = defaults.IPv6().retrieve()

        self.logger.debug("nic: %s" % nic)
        self.logger.debug("model: %s" % model)
        self.logger.debug("ip6model: %s" % ip6model)

        is_primary_interface = model["iface"] == ifname

        if not is_primary_interface:
            # The config contains the information for the primary ifnamee,
            # because this ifnamee is not the primaryifnameme we clear the
            # config
            model = dict((k, "") for k in model.keys())

        ipaddr, netmask, gateway, vlanid = (model["ipaddr"], model["netmask"],
                                            model["gateway"], model["vlanid"])

        ip6addr, ip6netmask, ip6gateway, ip6bootproto = (ip6model["ipaddr"],
                                                         ip6model["netmask"],
                                                         ip6model["gateway"],
                                                         ip6model["bootproto"])

        if model["bootproto"] == "dhcp":
            if nic.exists():
                routes = utils.network.Routes()
                gateway = routes.default()
                ipaddr, netmask = nic.ipv4_address().items()
                vlanid = ",".join(nic.vlanids())

        link_status_txt = ("Connected" if nic.has_link()
                           else "Disconnected")
        vendor_txt = nic.vendor[:24] if nic.vendor else ""

        self.plugin._model_extra.update({
            "dialog.nic.driver": nic.driver,
            "dialog.nic.vendor": vendor_txt,
            "dialog.nic.link_status": link_status_txt,
            "dialog.nic.hwaddress": nic.hwaddr,

            "dialog.nic.ipv4.bootproto": model["bootproto"],
            "dialog.nic.ipv4.address": ipaddr,
            "dialog.nic.ipv4.netmask": netmask,
            "dialog.nic.ipv4.gateway": gateway,
            "dialog.nic.ipv6.bootproto": ip6bootproto,
            "dialog.nic.ipv6.address": ip6addr,
            "dialog.nic.ipv6.netmask": ip6netmask,
            "dialog.nic.ipv6.gateway": ip6gateway,
            "dialog.nic.vlanid": vlanid,
        })

        self.logger.debug("model: %s" % self.plugin.model())

        padd = lambda l: l.ljust(12)
        ws = [ui.Row("dialog.nic._row[0]",
                     [ui.KeywordLabel("dialog.nic.driver", padd("Driver: ")),
                      ui.KeywordLabel("dialog.nic.vendor", padd("Vendor: ")),
                      ]),

              ui.Row("dialog.nic._row[2]",
                     [ui.KeywordLabel("dialog.nic.link_status",
                                      padd("Link Status: ")),
                      ui.KeywordLabel("dialog.nic.hwaddress",
                                      padd("MAC Address: ")),
                      ]),

              ui.Divider("dialog.nic._divider[0]"),

              ui.Label("dialog.nic.ipv4._header", "IPv4 Settings"),

              ui.Options("dialog.nic.ipv4.bootproto",
                         "Bootprotocol: ", [("none", "Disabled"),
                                            ("dhcp", "DHCP"),
                                            ("static", "Static")
                                            ]),

              ui.Row("dialog.nic._row[4]",
                     [ui.Entry("dialog.nic.ipv4.address",
                               padd("IP Address: ")),
                      ui.Entry("dialog.nic.ipv4.netmask",
                               padd("  Netmask: "))]),
              ui.Row("dialog.nic._row[5]",
                     [ui.Entry("dialog.nic.ipv4.gateway",
                               padd("Gateway: ")),
                      ui.Label("dummy[0]", "")]),

              ui.Divider("dialog.nic._divider[1]"),

              ui.Label("dialog.nic.ipv6._header", "IPv6 Settings"),

              ui.Options("dialog.nic.ipv6.bootproto",
                         "Bootprotocol: ", [("none", "Disabled"),
                                            ("auto", "Auto"),
                                            ("dhcp", "DHCP"),
                                            ("static", "Static")
                                            ]),

              ui.Row("dialog.nic._row[6]",
                     [ui.Entry("dialog.nic.ipv6.address",
                               padd("IP Address: ")),
                      ui.Entry("dialog.nic.ipv6.netmask",
                               padd("  Netmask: "))]),
              ui.Row("dialog.nic._row[7]",
                     [ui.Entry("dialog.nic.ipv6.gateway",
                               padd("Gateway: ")),
                      ui.Label("dummy[1]", "")]),

              ui.Divider("dialog.nic._divider[2]"),

              ui.Row("dialog.nic._row[8]",
                     [ui.Entry("dialog.nic.vlanid",
                               padd("VLAN ID: ")),
                      ui.Label("dummy[2]", "")]),

              ui.Divider("dialog.nic._divider[3]"),

              ui.Checkbox("dialog.nic.layout_bridged",
                          "Use Bridge: "),

              ui.Divider("dialog.nic._divider[4]"),
              ui.Button("dialog.nic.identify", "Flash Lights to Identify"),
              ]

        self.plugin.widgets.add(ws)
        self.children = ws
        self.buttons = [ui.SaveButton("dialog.nic.save", "Save"),
                        ui.CloseButton("dialog.nic.close", "Close")
                        ]
        self.plugin._nic_details_group.enabled(False)
