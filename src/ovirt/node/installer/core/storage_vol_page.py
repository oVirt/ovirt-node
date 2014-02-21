#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# storage_vol_page.py - Copyright (C) 2013 Red Hat, Inc.
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
Storage Volume page of the installer
"""

from ovirt.node import plugins, ui, valid
from ovirt.node.utils import process
from ovirt.node.exceptions import InvalidData


class Plugin(plugins.NodePlugin):
    _model = {}
    _free_space = 0
    _fill = True

    def name(self):
        return _("Storage Sizes")

    def rank(self):
        return 40

    def model(self):
        if not self._model:
            self._model = self.__get_default_sizes()
            self._model["storage.data_size"] = "%s" %\
                                               self.__calculate_free_space()
            self.logger.debug("Predefined sizes: %s" % self._model)
        return self._model

    def validators(self):
        min_swap, min_logging = self.__get_min_sizes()
        return {"storage.efi_size":
                valid.Number(bounds=[0, None]),
                "storage.root_size":
                valid.Number(bounds=[0, None]),
                "storage.swap_size":
                valid.Number(bounds=[min_swap, None]),
                "storage.config_size":
                valid.Number(bounds=[5, None]),
                "storage.logging_size":
                valid.Number(bounds=[min_logging, None]),
                "storage.data_size":
                valid.Number(bounds=[-1, None]),
                }

    def ui_content(self):
        ws = [ui.Header("header[0]", _("Storage Volumes")),
              ui.KeywordLabel("storage.drive_size", "Drive size: ")]

        if not self._fill:
            ws.extend([ui.KeywordLabel("storage.free_space",
                                       "Remaining Space: ")])

        ws.extend([ui.Label("label[0]", "Please enter the sizes for the " +
                            "following partitions in MB"),
                   ui.Checkbox("storage.fill_data", "Fill disk with Data " +
                               "partition", True),
                   ui.Entry("storage.efi_size", _("UEFI/Bios:"),
                            enabled=False),
                   ui.Entry("storage.root_size", _("Root & RootBackup:"),
                            enabled=False),
                   ui.Label("label[1]", _("(2 partitions at %sMB each)") %
                            self.model().get("storage.efi_size")),
                   ui.Divider("divider[2]"),
                   ui.Entry("storage.swap_size", _("Swap:")),
                   ui.Entry("storage.config_size", _("Config:")),
                   ui.Entry("storage.logging_size", _("Logging:")),
                   ui.Entry("storage.data_size", _("Data:"),
                            enabled=not self._fill),
                   ])

        if not self._fill:
            ws.extend([ui.Label("label[2]", "(-1 fills all free space)")])

        self.widgets.add(ws)
        page = ui.Page("storage", ws)
        page.buttons = [ui.QuitButton("button.quit", _("Quit")),
                        ui.Button("button.back", _("Back")),
                        ui.SaveButton("button.next", _("Continue"))]
        return page

    def on_change(self, changes):
        self._model.update(changes)

        if "storage.fill_data" in changes:
            if self._fill is not changes["storage.fill_data"]:
                self._fill = changes["storage.fill_data"]
                self.application.show(self.ui_content())
        size_keys = ["storage.efi_size", "storage.root_size",
                     "storage.swap_size", "storage.config_size",
                     "storage.logging_size"]
        if not self._fill:
            size_keys.append("storage.data_size")
        if changes.contains_any(size_keys):
            self._free_space = self.__calculate_free_space()
            if "storage.free_space" in self.widgets:
                self.widgets["storage.free_space"].text("%s MB" %
                                                        self._free_space)
            if self._fill:
                self.widgets["storage.data_size"].text("%s" % self._free_space)
            if self._free_space < 0:
                if self._fill:
                    raise InvalidData("Data partition must be at least 0 MB")
                else:
                    raise InvalidData("Free space must not be negative")
            else:
                for w in self.widgets:
                    if hasattr(self.widgets[w], "notice"):
                        self.widgets[w].notice("")
                self._on_ui_change(self._NodePlugin__invalid_changes)

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        if changes.contains_any(["button.back"]):
            self.application.ui.navigate.to_previous_plugin()
        elif changes.contains_any(["button.next"]):
            self._model.update(effective_changes)
            self.logger.debug("Nowdefined sizes: %s" % self._model)
            self.application.ui.navigate.to_next_plugin()

    def __get_min_sizes(self):
        if self.application.args.dry:
            return 2048, 256
        from ovirtnode.storage import Storage
        stor = Storage()
        return stor.MIN_SWAP_SIZE, stor.MIN_LOGGING_SIZE

    def __get_default_sizes(self):
        if self.application.args.dry:
            udiskscmd = "udisksctl info -b /dev/[sv]da* | grep Size"
            stdout = process.check_output(udiskscmd,
                                          shell=True)
            self._drive_size = (int(stdout.strip().split(":")[1].strip())
                                / 1024 / 1024)
            return {"storage.efi_size": "256",
                    "storage.root_size": "50",
                    "storage.swap_size": "0",
                    "storage.config_size": "5",
                    "storage.logging_size": "2048",
                    "storage.data_size": "0",
                    }
        from ovirtnode.storage import Storage
        stor = Storage()
        self._drive_size = self.__get_drives_size(self.__get_install_drive())
        sizes = {"storage.efi_size": "%s" % stor.EFI_SIZE,
                 "storage.root_size": "%s" % stor.ROOT_SIZE,
                 "storage.swap_size": "%s" % stor.SWAP_SIZE,
                 "storage.config_size": "%s" % stor.CONFIG_SIZE,
                 "storage.logging_size": "%s" % stor.LOGGING_SIZE,
                 "storage.data_size": "%s" % "0",
                 "storage.free_space": "0 MB",
                 "storage.drive_size": "%s MB" % self._drive_size
                 }
        return sizes

    def __get_drives_size(self, drives):
        self.logger.debug("Getting Drives Size For: %s" % drives)
        from ovirtnode.storage import Storage
        stor = Storage()
        drives_size = 0
        for drive in drives:
            drives_size += int(stor.get_drive_size(drive))
        self.logger.debug(drives_size)
        return drives_size

    def __get_install_drive(self):
        app = self.application
        return app.plugins()["Data Device"].model().get(
            "installation.devices", [])

    def __calculate_free_space(self):

        # Get these from the model because users can't change them and they
        # may change in the future. Root size is doubled to account for
        # rootbackup
        free_space = self._drive_size - (int(self._model["storage.root_size"])
                                         * 2 + int(self._model[
                                             "storage.efi_size"]))

        size_keys = ["storage.swap_size", "storage.config_size",
                     "storage.logging_size"]

        if int(self._model["storage.data_size"]) > -1 and not self._fill:
            size_keys.append("storage.data_size")

        for key in size_keys:
            free_space -= int(self._model[key])

        if int(self._model["storage.data_size"]) == -1 and free_space > 0:
            free_space = 0

        return free_space
