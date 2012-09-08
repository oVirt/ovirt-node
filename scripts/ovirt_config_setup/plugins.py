#!/usr/bin/python
#
# plugins.py - Copyright (C) 2012 Red Hat, Inc.
# Written by Joey Boggs <jboggs@redhat.com>
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

from ovirtnode.ovirtfunctions import *
from snack import *
import _snack
import glob

def get_plugins_list():
    plugin_dict = []
    plugin_dir = "/etc/ovirt-plugins.d/"
    if os.path.exists(plugin_dir):
        plugin_dict = {}
        for f in os.listdir(plugin_dir):
            if not f.endswith(".minimize"):
                p = open(plugin_dir + f)
                lines = p.readlines()
                name = lines[0].strip().split(":")[1]
                ver = lines[1].strip().split(":")[1]
                install_date = lines[2].strip().replace("Install Date:", "")
                p.close()
                plugin_dict[name] = "%s,%s" % (ver, install_date)
    return plugin_dict


class Plugin(PluginBase):
    """Plugin for Displaying Injected Installed Plugins/Packages.
    """

    def __init__(self, ncs):
        PluginBase.__init__(self, "Plugins", ncs)

    def plugin_details_callback(self):
        name = self.plugin_lb.current()
        ver, install_date = self.plugins[name].split(",")
        self.name_label.setText(name)
        self.version_label.setText(ver)
        self.install_date_label.setText(install_date)
        return

    def form(self):
        elements = Grid(2, 9)
        heading = Label("Installed Plugins")
        if is_console():
            heading.setColors(customColorset(1))
        elements.setField(heading, 0, 0, anchorLeft=1)
        self.plugins = get_plugins_list()
        elements.setField(Label(" "), 0, 1)
        if not os.path.exists("/etc/ovirt-plugins.d"):
            return [Label(""), elements]
        self.plugin_lb = Listbox(height=8, width=30, returnExit=1, scroll=1)
        self.plugin_lb.setCallback(self.plugin_details_callback)
        for key in sorted(self.plugins.iterkeys()):
            ver, install_date = self.plugins[key].split(",")
            self.plugin_lb.append(key, key)
        elements.setField(self.plugin_lb, 0, 2, anchorLeft=1)
        if len(self.plugins) > 0:
            # prepopulate plugin details
            name = self.plugin_lb.current()
            ver, install_date = self.plugins[name].split(",")
            elements.setField(Label("Plugin Details"), 0, 3, anchorLeft=1,
                              padding=(0, 1, 0, 1))
            detail_grid = Grid(2, 5)
            detail_grid.setField(Label("Name:           "), 0, 0, anchorLeft=1)
            detail_grid.setField(Label("Version         "), 0, 1, anchorLeft=1)
            detail_grid.setField(Label("Date Installed: "), 0, 2, anchorLeft=1)
            self.name_label = Label(name)
            self.version_label = Label(ver)
            self.install_date_label = Label(install_date)
            detail_grid.setField(self.name_label, 1, 0, anchorLeft=1)
            detail_grid.setField(self.version_label, 1, 1, anchorLeft=1)
            detail_grid.setField(self.install_date_label, 1, 2, anchorLeft=1)
            elements.setField(detail_grid, 0, 7, anchorLeft=1)
        return [Label(""), elements]

    def action(self):
        p_manifests_dir = "/etc/ovirt-plugins-manifests.d"
        try:
            p_name = self.plugin_lb.current()
        except:
            return
        # display rpm and srpm differences for now
        rpm_man = glob.glob("%s/delta-*-manifest-rpm-%s.txt" % \
                  (p_manifests_dir,p_name))[0]
        srpm_man = glob.glob("%s/delta-*-manifest-srpm-%s.txt" % \
                   (p_manifests_dir, p_name))[0]
        file_man = glob.glob("%s/delta-*-manifest-file-%s.txt" % \
                   (p_manifests_dir, p_name))[0]
        items = {}
        items["RPM Diff"] = rpm_man
        items["SRPM Diff"] = srpm_man
        items["File Diff"] = file_man
        loop = True
        while loop:
            self.ncs._create_warn_screen()
            (button, choice) = \
                ListboxChoiceWindow(self.ncs.screen, "Manifest Selection",
                        "Pick a manifest to view:", items,
                        buttons = ("View", "Return"), width = 15, scroll = 1,
                                height = 8)
            k = items.keys()[choice]
            if button == "return":
                loop = False
            else:
                self.ncs._create_blank_screen()
                self.ncs._set_title()
                self._gridform = GridForm(self.ncs.screen, "", 2, 2)
                self._gridform.add(Label("Reading Manifest..."), 0, 0)
                self._gridform.draw()
                self.ncs.screen.refresh()
                details = ""
                d = open(items[k])
                for line in d:
                    details += line
                d.close()
                if is_console():
                    self.ncs.screen.setColor("BUTTON", "black", "red")
                    self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
                ButtonChoiceWindow(self.ncs.screen, "Manifest Details", details,
                                   buttons=['Ok'], width=68)
                self.ncs.reset_screen_colors()
        return

def get_plugin(ncs):
    return Plugin(ncs)
