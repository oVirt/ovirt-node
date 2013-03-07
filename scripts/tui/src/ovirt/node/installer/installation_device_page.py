#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# installation_devce_page.py - Copyright (C) 2013 Red Hat, Inc.
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
Installation device selection page of the installer
"""
from ovirt.node import plugins, ui
from ovirt.node.installer.boot_device_page import DeviceDetails, \
    CustomDeviceDialog, StorageDiscovery


class Plugin(plugins.NodePlugin):
    _model = {}

    def __init__(self, app):
        super(Plugin, self).__init__(app)
        self.storage_discovery = StorageDiscovery(app.args.dry)
        self.storage_discovery.start()

    def name(self):
        return "Data Device"

    def rank(self):
        return 30

    def model(self):
        devices = self.storage_discovery.all_devices_for_ui_table()
        self.logger.debug("Available devices: %s" % devices)
        if devices:
            first_dev = devices[0][0]
            self._model["installation.device.details"] = first_dev
            self._model["installation.device.current"] = first_dev
        return self._model

    def validators(self):
        has_selection = lambda v: "At least one installation device" \
            if not self.widgets["installation.device.current"].selection() \
            else True
        return {"installation.device.current": has_selection}

    def ui_content(self):
        page_title = "Please select the disk(s) to use for installation " \
                     "of %s" % self.application.product.PRODUCT_SHORT

        other_device = self._model.get("installation.device.custom", "")
        devices = self.storage_discovery.all_devices_for_ui_table(other_device)

        ws = [ui.Header("header[0]", page_title)]

        if devices:
            ws += [ui.Table("installation.device.current", "",
                            " %6s  %11s  %5s" %
                            ("Location", "Device Name", "Size"), devices,
                            multi=True),
                   DeviceDetails("installation.device.details", self,
                                 "(No device)")
                   ]
        else:
            ws += [ui.Label("installation.no_device",
                            "No Valid Install Devices Detected")]

        page = ui.Page("installation", ws)
        page.buttons = [ui.QuitButton("button.quit", "Quit"),
                        ui.Button("button.back", "Back"),
                        ui.SaveButton("button.next", "Continue")]

        self.widgets.add(page)
        return page

    def on_change(self, changes):
        self.logger.debug("Installation device changes: %s" % changes)
        if changes.contains_any(["installation.device.current"]):
            highlighted_device = changes["installation.device.current"]
            details = self.widgets["installation.device.details"]
            if highlighted_device == "other":
                details.text("")
                self._dialog = CustomDeviceDialog("custom", "x", "y")
                return self._dialog
            elif highlighted_device:
                selected_devices = \
                    self.widgets["installation.device.current"].selection()
                self.logger.debug("selected devices: %s" % selected_devices)
                changes["installation.devices"] = selected_devices
                self._model.update(changes)
                details.set_device(highlighted_device)

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        self.logger.debug("All inst changes: %s" % changes)
        if changes.contains_any(["button.back"]):
            self.application.ui.navigate.to_previous_plugin()
        elif changes.contains_any(["button.next"]):
            self.application.ui.navigate.to_next_plugin()

        elif changes.contains_any(["installation.device.custom",
                                   "dialog.device.custom.save"]):
            self._dialog.close()
            return self.ui_content()
