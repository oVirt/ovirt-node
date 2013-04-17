#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# boot_device_page.py - Copyright (C) 2013 Red Hat, Inc.
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
from ovirt.node import plugins, ui, utils, valid
import threading

"""
Boot device selection page of the installer
"""


class Plugin(plugins.NodePlugin):
    _model = {}

    def __init__(self, app):
        super(Plugin, self).__init__(app)
        self.storage_discovery = StorageDiscovery(app.args.dry)
        self.storage_discovery.run()

    def name(self):
        return "Boot Device"

    def rank(self):
        return 20

    def model(self):
        self._model.update({"boot.device": ""})
        devices = self.storage_discovery.all_devices_for_ui_table()
        self.logger.debug("Using devices: %s" % devices)
        if devices:
            first_dev = devices[0][0]
            self._model["label.details"] = first_dev
            self._model["boot.device"] = first_dev
        return self._model

    def validators(self):
        return {"boot.device": lambda v: None if v else "No device given",
                "boot.device.custom": valid.BlockDevice()
                }

    def ui_content(self):
        page_title = "Please select the disk to use for booting %s" % \
                     self.application.product.PRODUCT_SHORT

        other_device = self._model.get("boot.device.custom", "")
        devices = self.storage_discovery.all_devices_for_ui_table(other_device)

        ws = [ui.Header("header[0]", page_title)]

        if devices:
            ws += [ui.Table("boot.device", "", " %6s  %11s  %5s" %
                            ("Location", "Device Name", "Size"), devices),
                   DeviceDetails("label.details", self, "(No device)")
                   ]
        else:
            ws += [ui.Label("boot.no_device",
                            "No Valid Boot Devices Detected")]

        page = ui.Page("boot", ws)
        page.buttons = [ui.QuitButton("button.quit", "Quit"),
                        ui.Button("button.back", "Back"),
                        ui.SaveButton("button.next", "Continue")]

        self.widgets.add(page)
        return page

    def on_change(self, changes):
        self.logger.debug("Boot device changes: %s" % changes)
        if changes.contains_any(["boot.device"]):
            device = changes["boot.device"]
            if device == "other":
                self.widgets["label.details"].text("")
            else:
                self._model.update(changes)
                self.widgets["label.details"].set_device(device)

        if changes.contains_any(["boot.device.custom"]):
            self._model.update(changes)

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        self.logger.debug("Pending changes: %s" % changes)
        if changes.contains_any(["button.back"]):
            self.application.ui.navigate.to_previous_plugin()

        elif changes.contains_any(["button.next"]):
            self.application.ui.navigate.to_next_plugin()

        elif changes.contains_any(["boot.device"]):
            device = changes["boot.device"]
            if device == "other":
                self._dialog = CustomDeviceDialog("custom", "x", "y")
                return self._dialog
            else:
                self.application.ui.navigate.to_next_plugin()

        elif changes.contains_any(["boot.device.custom",
                                   "dialog.device.custom.save"]):
            self._dialog.close()
            return self.ui_content()


class StorageDiscovery(threading.Thread):
    """Probing for available devices is pulled out into a thread
    because it can tae several seconds
    """
    _all_devices = None
    do_fake = False

    def __init__(self, do_fake):
        super(StorageDiscovery, self).__init__()
        self.do_fake = do_fake

    def run(self):
        devices = utils.storage.Devices(fake=self.do_fake)
        self._all_devices = devices.get_all()

    def all_devices(self):
        """Return a list of all devices
        """
        try:
            self.join(30)
        except RuntimeError:
            pass
            # I suppose the thread was not started
        return self._all_devices

    def all_devices_for_ui_table(self, other_device=""):
        """Returns a ui.Table ready list of strings with all useable storage
        devices

        Args:
            other_devices: String-like to be used for the "Other"-Entry
        Returns:
            A list of strings to be used with ui.Table
        """
        all_devices = self.all_devices().items()
        devices = sorted([(name, " %6s  %11s  %5s GB" % (d.bus, d.name,
                                                         d.size))
                          for name, d in all_devices], key=lambda t: t[0])

        devices += [("other", "Other Device: %s" % other_device)]

        return devices


class DeviceDetails(ui.Label):
    """A simple widget to display the details for a given device
    """
    def __init__(self, path, plugin, label):
        super(DeviceDetails, self).__init__(path, label)
        self._plugin = plugin

    def set_device(self, device_name):
        """
        """
        all_devices = self._plugin.storage_discovery.all_devices()
        device = all_devices[device_name]

        lines = [("Device", device.name),
                 ("Model", device.model),
                 ("Bus Type", device.bus),
                 ("Serial", device.serial),
                 ("Size (GB)", device.size),
                 ("Description", device.desc),
                 ]

        width = max([len(o[0]) for o in lines])
        txt = "Disk Details\n"
        txt += "\n".join(["%s: %s" % (("{:%d}" % width).format(a), b)
                          for a, b in lines])
        self.text(txt)

    def value(self, value=None):
        if value:
            self.set_device(value)
        return value


class CustomDeviceDialog(ui.Dialog):
    """The dialog to input a custom root/boot device
    """
    def __init__(self, path, title, description):
        title = "Custom Block Device"
        description = "Please select the disk to use for booting PRODUCT_NAME"
        device_entry = ui.Entry("boot.device.custom", "Device path:")
        children = [ui.Label("label[0]", description),
                    ui.Divider("divider[0]"),
                    device_entry]
        super(CustomDeviceDialog, self).__init__(path, title, children)
        self.buttons = [ui.SaveButton("dialog.device.custom.save"),
                        ui.CloseButton("dialog.device.custom.close", "Cancel")]
