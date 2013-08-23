#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# welcome_page.py - Copyright (C) 2013 Red Hat, Inc.
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
from ovirt.node import plugins, ui, utils
from ovirt.node.utils import virt, system
import os

"""
Welcome page of the installer

The idea is that every page modifies it's own model, which is at the end pulled
using the plugin.model() call and used to build a stream of
transaction_elements (see progress_page.py)

NOTE: Each page stores the information in the config page
NOTE II: Or shall we build the transactions per page?
"""


class Plugin(plugins.NodePlugin):
    """The welcome page plugin
    """
    _model = {}

    def name(self):
        return _("Welcome")

    def rank(self):
        return 0

    def model(self):
        return self._model

    def validators(self):
        return {}

    def ui_content(self):
        ws = [ui.Header("header[0]", _("Installation"))]
        ws += self.___installation_options()
        ws += [ui.Divider("divider[0]")]
        ws += self.__additional_infos()
        self.widgets.add(ws)
        page = ui.Page("welcome", ws)
        page.buttons = [ui.QuitButton("button.quit", _("Quit"))]
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        if "button.install" in effective_changes:
            self._model["method"] = "install"

        elif "button.upgrade" in effective_changes:
            self._model["method"] = "upgrade"

        elif "button.downgrade" in effective_changes:
            self._model["method"] = "downgrade"

        elif "button.reinstall" in effective_changes:
            self._model["method"] = "reinstall"

        self.application.ui.navigate.to_next_plugin()

    def ___installation_options(self):
        if self.application.args.dry:
            return [ui.Button("button.install", _("Install (dry)")),
                    ui.Button("button.upgrade", _("Upgrade (dry)")),
                    ui.Button("button.downgrade", _("Downgrade (dry)")),
                    ui.Button("button.reinstall", _("Reinstall (dry)"))]

        media = utils.system.InstallationMedia()

        has_hostvg = utils.system.has_hostvg()
        has_root = os.path.exists("/dev/disk/by-label/ROOT")

        if has_hostvg and has_root:
            return [ui.Label(_("Major version upgrades are unsupported, ") +
                             _("uninstall existing version first"))]

        if has_hostvg:
            try:
                installed = utils.system.InstalledMedia()
                if media > installed:
                    return [ui.Button("button.upgrade",
                                      _("Upgrade %s to %s") %
                                      (installed, media))]
                elif media < installed:
                    return [ui.Button("button.downgrade",
                                      _("Downgrade %s to %s") %
                                      (installed, media))]
                return [ui.Button("button.reinstall",
                                  _("Reinstall %s") % installed)]
            except:
                self.logger.error("Unable to get version numbers for " +
                                  "upgrade, invalid installation or media")
                return [ui.Label(
                    "lbl.failinstall",
                    _("Invalid installation, please reboot from ") +
                    _("media and choose Reinstall"))]

        return [ui.Button("button.install",
                          _("Install Hypervisor %s") % media)]

    def __additional_infos(self):
        ws = []
        ws.append(ui.Label("welcome.virt", _("Info: %s") %
                           virt.hardware_status()))
        if system.is_efi():
            ws.append(ui.Label("welcome.efi",
                               _("Info: Machine is booted in EFI mode")))
        if self.application.args.dry:
            ws.append(ui.Label("dry", _("Info: DRY MODE")))
        return ws
