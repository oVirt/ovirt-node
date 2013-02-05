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

"""
Boot device selection page of the installer
"""
from ovirt.node import plugins, ui, utils


class Plugin(plugins.NodePlugin):
    _model = None
    _elements = None

    def name(self):
        return "Boot Device"

    def rank(self):
        return 30

    def model(self):
        return self._model or {}

    def validators(self):
        return {}

    def ui_content(self):
        page_title = "Please select the disk to use for booting %s" % \
                     self.application.product.PRODUCT_SHORT

        ws = [ui.Header("header[0]", page_title),
              ui.Table("boot.device", "", " %6s  %11s  %5s" %
                       ("Location", "Device Name", "Size"),
                       self._device_list()),
              DeviceDetails("label.details", "(No device)")
              ]

        self.widgets.add(ws)
        page = ui.Page("boot", ws)
        page.buttons = [ui.Button("button.quit", "Quit"),
                        ui.Button("button.back", "Back"),
                        ui.Button("button.next", "Continue")]
        return page

    def _device_list(self):
        devices = utils.storage.Devices(fake=True)
        all_devices = devices.get_all().items()
        return [(name, " %6s  %11s  %5s GB" % (d.bus, d.name, d.size))
                for name, d in all_devices]

    def on_change(self, changes):
        if "button.next" in changes:
            self._elements["label.details"].set_device(changes["button.next"])

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        if changes.contains_any(["button.next", "boot.device"]):
            self.transaction = "a"
            self.application.ui.navigate.to_next_plugin()


class DeviceDetails(ui.Label):
    def set_device(self, device):
        devices = utils.storage.Devices(fake=True)
        all_devices = devices.get_all()
        if not all_devices:
            pass
        """lines = [("Disk Details",),
                 ("Device", ""),
                 ("Model", ""),
                 ("Bus Type", ""),
                 ("Serial", ""),
                 ("Size", ""),
                 ("Description", ""),
                 ]"""
        self.text("%s" % device)
