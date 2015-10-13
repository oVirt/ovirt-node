#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# storage_vol_page.py - Copyright (C) 2014 Red Hat, Inc.
# Written by Ryan Barry <rbarry@redhat.com>
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
Confirmation page of the installer
"""
from ovirt.node import plugins, ui
from ovirt.node.installer.core.boot_device_page import StorageDiscovery
from ovirt.node.utils.system import LVM
import re


class Plugin(plugins.NodePlugin):
    _model = {}

    def __init__(self, app):
        super(Plugin, self).__init__(app)
        self.storage_discovery = StorageDiscovery(app.args.dry)
        self.storage_discovery.start()
        self._header = "{bus!s:8.8} {name!s:48.48} {size!s:9.9}"

    def name(self):
        return "Confirm disk selections"

    def rank(self):
        return 45

    def model(self):
        # Force rebuilding in case they go back and change a value
        self._build_model()

        return self._model

    def validators(self):
        return {}

    def ui_content(self):
        align = lambda l: l.ljust(16)
        if not self._model:
            self._build_model()

        ws = [ui.Header("header[0]", _("Confirm disk selections")),
              ui.Notice("notice[0]", _("The data on these disks will "
                                       "be erased!")),
              ui.KeywordLabel("boot.header", _("Boot device")),
              DiskDetails("boot.device.current", self,
                          self._model["boot.device.current"])]

        if self._storage_tagged(self._model["boot.device.current"]):
            ws.extend([ui.Notice("boot.notice", _("Boot device may be part "
                                                  "of a storage domain!"))])

        ws.extend([ui.KeywordLabel("install.header", "Install devices")])

        for i in range(len(self._model["installation.devices"])):
            ws.extend([DiskDetails("installation.device[%s]" % i, self,
                                   self._model["installation.devices"][i])])
            if self._storage_tagged(self._model["installation.devices"][i]):
                ws.extend([ui.Notice("installation.notice[%s]" % i,
                                     _("This device may be part of a storage "
                                       "domain!"))])

        ws.extend([ui.Divider("divider[0]"),
                   ui.KeywordLabel("storage.volumes", _("Volume sizes"))])

        intuples = lambda lst, n: [lst[x:x+n] for x in range(0, len(lst), n)]
        for xs in intuples(sorted(k for k in self._model.keys()
                           if k.startswith("storage.")), 2):
            chi = []
            for x in xs:
                chi.append(ui.KeywordLabel(x, _(align(
                    x.replace("_", " ").replace("storage.", "").title() + ":"))
                ))
            row = ui.Row("row[%s]" % xs, chi)
            ws.append(row)

        if int(self._model["storage.data_size"]) < (50*1024):
            ws.extend([ui.Divider("divider.he"),
                      ui.Notice("notice.he", "The size of the data volume is "
                                "not large enough to use the Engine "
                                "Appliance, must be at least 50GB (51200MB)")])

        page = ui.Page("confirmation", ws)
        page.buttons = [ui.QuitButton("button.quit", _("Quit")),
                        ui.Button("button.back", _("Back")),
                        ui.SaveButton("button.next", _("Confirm"))]

        self.widgets.add(page)
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        changes = self.pending_changes(False)
        if changes.contains_any(["button.back"]):
            self.application.ui.navigate.to_previous_plugin()
        elif changes.contains_any(["button.next"]):
            self.application.ui.navigate.to_next_plugin()

    def _build_model(self):
        _model = {}

        [_model.update(plugin.model()) for plugin in
         self.application.plugins().values() if not
         plugin.name() == "Confirm disk selections"]

        [_model.update({k: "%s" % _model[k]}) for k in _model.keys() if
         re.match(r'storage.*?size$', k) and not _model[k].endswith(" MB")]

        if "storage.fill_data" in _model:
            _model["storage.free_space"] = "0"
            del _model["storage.fill_data"]
        _model["installation.devices"].sort()

        self._model = _model
        self.logger.debug("SET %s" % _model)

    def _storage_tagged(self, dev):
        found = False
        for vg in LVM().vgs():
            if dev in vg.pv_names and "storage_domain" in \
                    " ".join(vg.tags):
                found = True
        return found


class DiskDetails(ui.Label):
    """Display basic disk information"""

    def __init__(self, path, plugin, dev):
        super(DiskDetails, self).__init__(path, "")
        self._plugin = plugin
        self.get_details(dev)

    def get_details(self, dev):
        all_devices = self._plugin.storage_discovery.all_devices()

        if dev in all_devices:
            device = all_devices[dev]
            txt = self._plugin._header.format(bus=device.bus, name=device.name,
                                              size="%sGB" % device.size)
        else:
            txt = self._plugin._header.format(bus="", name=dev, size="")

        self.text(txt)

    def value(self, value=None):
        if value:
            self.get_details(value)
        return value
