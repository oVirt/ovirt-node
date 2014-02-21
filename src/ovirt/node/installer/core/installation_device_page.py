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
from ovirt.node import exceptions, plugins, ui, valid
from ovirt.node.installer.core.boot_device_page import DeviceDetails, \
    CustomDeviceDialog, StorageDiscovery


class Plugin(plugins.NodePlugin):
    _model = {}

    def __init__(self, app):
        super(Plugin, self).__init__(app)
        self.storage_discovery = StorageDiscovery(app.args.dry)
        self.storage_discovery.start()

    def name(self):
        return _("Data Device")

    def rank(self):
        return 30

    def model(self):
        devices = self.storage_discovery.all_devices_for_ui_table()
        self.logger.debug("Available devices: %s" % devices)
        if devices:
            selected_boot_dev = \
                self.application.plugins()["Boot Device"]\
                .model().get("boot.device.current", "")
            self.logger.debug("Selected boot device: %s" %
                              selected_boot_dev)
            first_dev = devices[0][0]
            if selected_boot_dev in [dev[0] for dev in devices]:
                first_dev = selected_boot_dev
            self.logger.debug("First installation device: %s" % first_dev)
            self._model["installation.device.details"] = first_dev
            self._model["installation.device.current"] = first_dev
        return self._model

    def validators(self):
        def has_selection(v):
            if (self.widgets["installation.device.current"].selection() or
                    "installation.device.custom" in self._model):
                return True
            else:
                return "Please select at least one installation device."

        def multiple_block_devices(v):
            if all(valid.BlockDevice().validate(b) for b in v.split(",")):
                return True
            else:
                return "Please enter only valid block devices."

        return {"installation.device.current": has_selection,
                "installation.device.custom": multiple_block_devices}

    def ui_content(self):
        page_title = \
            _("Please select the disk(s) to use for installation of %s") \
            % self.application.product.PRODUCT_SHORT

        other_device = self._model.get("installation.device.custom", "")
        devices = self.storage_discovery.all_devices_for_ui_table()

        ws = [ui.Header("header[0]", page_title)]

        tbl_head = self.storage_discovery.tbl_tpl.format(bus="Location",
                                                         name="Device Name",
                                                         size="Size (GB)")
        if devices:
            ws += [ui.Table("installation.device.current", "", tbl_head,
                            devices, height=3, multi=True),
                   ui.Button("button.other_device", "Other Device: %s" %
                             other_device),
                   ui.Divider("divider[0]"),
                   DeviceDetails("installation.device.details", self,
                                 _("(No device)"))
                   ]
        else:
            ws += [ui.Label("installation.no_device",
                            _("No Valid Install Devices Detected"))]

        page = ui.Page("installation", ws)
        page.buttons = [ui.QuitButton("button.quit", _("Quit")),
                        ui.Button("button.back", _("Back")),
                        ui.SaveButton("button.next", _("Continue"))]

        self.widgets.add(page)

        # We are directly connecting to the table's on_change event
        # The tables on_change event is fired (in the multi-case)
        # when the highlighted entry is changed.
        table = self.widgets["installation.device.current"]
        table.on_change.connect(self.__update_details)

        return page

    def __update_details(self, target, change):
        details = self.widgets["installation.device.details"]
        highlighted_device = change[target.path]

        if highlighted_device is "other":
            details.text("")
        else:
            details.set_device(highlighted_device)

    def on_change(self, changes):
        self.logger.debug("Installation device changes: %s" % changes)
        if changes.contains_any(["installation.device.current"]):
            changed_device = changes["installation.device.current"]
            if changed_device:
                selected_devices = \
                    self.widgets["installation.device.current"].selection()
                self.logger.debug("selected devices: %s" % selected_devices)
                changes["installation.devices"] = selected_devices
                self._model.update(changes)
        if changes.contains_any(["installation.device.custom"]):
            if self.storage_discovery.devices.live_disk_name() == \
                    self.storage_discovery.devices.translate_device_name(
                        changes["installation.device.custom"]):
                raise exceptions.InvalidData("Can't be the same as " +
                                             "the live device")
            else:
                self._model.update(changes)

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        self.logger.debug("All inst changes: %s" % changes)

        if "button.other_device" in changes:
            details = self.widgets["installation.device.details"]
            details.text("")
            description = (("Please enter one or more disks to use " +
                            "for installing %s. Multiple devices can be " +
                            "separated by comma.") %
                           self.application.product.PRODUCT_SHORT)
            self._dialog = CustomDeviceDialog("installation.device.custom",
                                              "Installation devices.",
                                              description)
            self.widgets.add(self._dialog)
            return self._dialog

        elif changes.contains_any(["installation.device.custom",
                                   "dialog.device.custom.save"]):
            self._dialog.close()
            return self.ui_content()

        if changes.contains_any(["button.back"]):
            self.application.ui.navigate.to_previous_plugin()
        elif changes.contains_any(["button.next"]):
            if "installation.device.custom" in self._model:
                cdev = self._model["installation.device.custom"]
                self._model["installation.devices"].append(cdev)
            self.application.ui.navigate.to_next_plugin()
