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
from ovirt.node import exceptions, plugins, ui, utils, valid
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
        return _("Boot Device")

    def rank(self):
        return 20

    def model(self):
        self._model.update({"boot.device": "",
                            "label.details": ""})
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
        page_title = _("Please select the disk to use for booting %s") % \
            self.application.product.PRODUCT_SHORT

        other_device = self._model.get("boot.device.custom", "")
        devices = self.storage_discovery.all_devices_for_ui_table()

        ws = [ui.Header("header[0]", page_title)]

        tbl_head = self.storage_discovery.tbl_tpl.format(bus=_("Location"),
                                                         name=_("Device Name"),
                                                         size=_("Size (GB)"))
        if devices:
            ws += [ui.Table("boot.device", "", tbl_head, devices),
                   ui.Divider("divider[0]"),
                   ui.Button("button.other_device", "Other device: %s" %
                             other_device),
                   DeviceDetails("label.details", self, _("(No device)"))
                   ]
        else:
            ws += [ui.Label("boot.no_device",
                            _("No Valid Boot Devices Detected"))]

        page = ui.Page("boot", ws)
        page.buttons = [ui.QuitButton("button.quit", _("Quit")),
                        ui.Button("button.back", _("Back")),
                        ui.SaveButton("button.next", _("Continue"))]

        self.widgets.add(page)
        return page

    def on_change(self, changes):
        self.logger.debug("Boot device changes: %s" % changes)
        if changes.contains_any(["boot.device"]):
            device = changes["boot.device"]
            if device == "other":
                self.widgets["label.details"].text("")
            else:
                changes["boot.device.current"] = device
                self._model.update(changes)
                self.widgets["label.details"].set_device(device)

        if changes.contains_any(["boot.device.custom"]):
            if self.storage_discovery.devices.live_disk_name() == \
                    self.storage_discovery.devices.translate_device_name(
                        changes["boot.device.custom"]):
                raise exceptions.InvalidData("Can't be the same as "
                                             "the live device")
            else:
                self._model.update(changes)

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        self.logger.debug("Pending changes: %s" % changes)

        if "button.other_device" in changes:
            description = ("Please enter the disk to use " +
                           "for booting %s" %
                           self.application.product.PRODUCT_SHORT)
            self._dialog = CustomDeviceDialog("boot.device.custom",
                                              "Specify a boot device",
                                              description)
            self.widgets.add(self._dialog)
            return self._dialog

        if changes.contains_any(["boot.device.custom",
                                 "dialog.device.custom.save"]):
            self._dialog.close()
            cdev = self._model["boot.device.custom"]
            self._model["boot.device.current"] = cdev
            self.application.ui.navigate.to_next_plugin()

        if changes.contains_any(["boot.device"]):
            self.application.ui.navigate.to_next_plugin()

        if changes.contains_any(["button.back"]):
            self.application.ui.navigate.to_previous_plugin()

        elif changes.contains_any(["button.next"]):
            if "boot.device.custom" in self._model:
                cdev = self._model["boot.device.custom"]
                self._model["boot.device.current"] = cdev
            self.application.ui.navigate.to_next_plugin()


class StorageDiscovery(threading.Thread):
    """Probing for available devices is pulled out into a thread
    because it can tae several seconds
    """
    _all_devices = None
    devices = None
    do_fake = False

    tbl_tpl = " {bus!s:8.8}  {name!s:48.48} {size!s:9.9}"

    def __init__(self, do_fake):
        super(StorageDiscovery, self).__init__()
        self.do_fake = do_fake

    def run(self):
        self.devices = utils.storage.Devices(fake=self.do_fake)
        self._all_devices = self.devices.get_all()

    def all_devices(self):
        """Return a list of all devices
        """
        try:
            self.join(30)
        except RuntimeError:
            pass
            # I suppose the thread was not started
        return self._all_devices

    def all_devices_for_ui_table(self):
        """Returns a ui.Table ready list of strings with all useable storage
        devices

        Returns:
            A list of strings to be used with ui.Table
        """
        all_devices = self.all_devices().items()
        devices = sorted([(name, self.tbl_tpl.format(bus=d.bus, name=d.name,
                                                     size=d.size))
                          for name, d in all_devices], key=lambda t: t[0])

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

        lines = [(_("Device"), device.name),
                 (_("Model"), device.model),
                 (_("Bus Type"), device.bus),
                 (_("Serial"), device.serial),
                 (_("Size (GB)"), device.size),
                 (_("Description"), device.desc),
                 ]

        width = max([len(o[0]) for o in lines])
        txt = _("Disk Details\n")
        txt += "\n".join(["%s: %s" % (("{0:%d}" % width).format(a), b)
                          for a, b in lines])
        self.text(txt)

    def value(self, value=None):
        if value:
            self.set_device(value)
        return value


class CustomDeviceDialog(ui.Dialog):
    """The dialog to input a custom root/boot device
    """
    def __init__(self, path_prefix, title, description):
        title = _("Custom Block Device")

        device_entry = ui.Entry(path_prefix, _("Device path:"))
        children = [ui.Label("label[0]", description),
                    ui.Divider("divider[0]"),
                    device_entry]
        super(CustomDeviceDialog, self).__init__("%s.dialog" % path_prefix,
                                                 title, children)
        self.buttons = [ui.SaveButton("dialog.device.custom.save", _("Save"),
                                      enabled=False),
                        ui.CloseButton("dialog.device.custom.close",
                                       _("Cancel"))]
