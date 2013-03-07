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


class Plugin(plugins.NodePlugin):
    _model = {}

    def name(self):
        return "Storage Sizes"

    def rank(self):
        return 40

    def model(self):
        if not self._model:
            self._model = self.__get_default_sizes()
            self.logger.debug("Predefined sizes: %s" % self._model)
        return self._model

    def validators(self):
        is_zero = valid.Number(exactly=0)
        min_swap, min_logging = self.__get_min_sizes()
        return {"storage.efi_size":
                valid.Number(bounds=[0, None]),
                "storage.root_size":
                valid.Number(bounds=[0, None]),
                "storage.swap_size":
                valid.Number(bounds=[min_swap, None]) | is_zero,
                "storage.config_size":
                valid.Number(bounds=[5, None]),
                "storage.logging_size":
                valid.Number(bounds=[min_logging, None]) | is_zero,
                "storage.data_size":
                valid.Number(bounds=[0, None]),
                }

    def ui_content(self):
        ws = [ui.Header("header[0]", "Storage Volumes"),
              ui.Label("label[0]", "Please enter the sizes for the " +
                       "following partitions in MB"),
              ui.Divider("divider[0]"),
              ui.Entry("storage.efi_size", "UEFI/Bios:", enabled=False),
              ui.Divider("divider[1]"),
              ui.Entry("storage.root_size", "Root & RootBackup:",
                       enabled=False),
              ui.Label("label[1]", "(2 partitions at 256MB each)"),
              ui.Divider("divider[2]"),
              ui.Entry("storage.swap_size", "Swap:"),
              ui.Entry("storage.config_size", "Config:"),
              ui.Entry("storage.logging_size", "Logging:"),
              ui.Entry("storage.data_size", "Data:"),
              ]
        self.widgets.add(ws)
        page = ui.Page("storage", ws)
        page.buttons = [ui.QuitButton("button.quit", "Quit"),
                        ui.Button("button.back", "Back"),
                        ui.SaveButton("button.next", "Next")]
        return page

    def on_change(self, changes):
        self._model.update(changes)

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        if changes.contains_any(["button.back"]):
            self.application.ui.navigate.to_previous_plugin()
        elif changes.contains_any(["button.next"]):
            self.application.ui.navigate.to_next_plugin()

    def __get_min_sizes(self):
        if self.application.args.dry:
            return 2048, 256
        from ovirtnode.storage import Storage
        stor = Storage()
        return stor.MIN_SWAP_SIZE, stor.MIN_LOGGING_SIZE

    def __get_default_sizes(self):
        if self.application.args.dry:
            return {"storage.efi_size": "256",
                    "storage.root_size": "50",
                    "storage.swap_size": "0",
                    "storage.config_size": "5",
                    "storage.logging_size": "2048",
                    "storage.data_size": "0",
                    }
        from ovirtnode.storage import Storage
        stor = Storage()
        sizes = {"storage.efi_size": "%s" % stor.EFI_SIZE,
                 "storage.root_size": "%s" % stor.ROOT_SIZE,
                 "storage.swap_size": "%s" % stor.SWAP_SIZE,
                 "storage.config_size": "%s" % stor.CONFIG_SIZE,
                 "storage.logging_size": "%s" % stor.LOGGING_SIZE,
                 "storage.data_size": "%s" % stor.DATA_SIZE,
                 }
        return sizes
