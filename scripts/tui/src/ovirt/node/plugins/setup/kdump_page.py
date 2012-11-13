#!/usr/bin/python
#
# kdump.py - Copyright (C) 2012 Red Hat, Inc.
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
Configure KDump
"""

import ovirt.node.plugins
import ovirt.node.valid
import ovirt.node.ui


class Plugin(ovirt.node.plugins.NodePlugin):
    _model = None
    _widgets = None

    _types = [
                 ("local", "Local"),
                 ("ssh", "SSH"),
                 ("nfs", "NFS")
             ]

    def name(self):
        return "Kdump"

    def rank(self):
        return 60

    def model(self):
        """Returns the model of this plugin
        This is expected to parse files and all stuff to build up the model.
        """
        if not self._model:
            self._model = {
                # The target address
                "kdump.type": "ssh",
                "kdump.ssh_location": "",
                "kdump.nfs_location": "",
            }
        return self._model

    def validators(self):
        """Validators validate the input on change and give UI feedback
        """
        return {
                "kdump.type": ovirt.node.valid.Options(self._types),
                "kdump.ssh_location": ovirt.node.valid.NoSpaces(),
                "kdump.nfs_location": ovirt.node.valid.NoSpaces(),
            }

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        widgets = [
            ("kdump._header", ovirt.node.ui.Header("Configure Kdump")),
            ("kdump.type", ovirt.node.ui.Options("Type", self._types)),
            ("kdump.ssh_location", ovirt.node.ui.Entry("SSH Location:",
                                                       align_vertical=True)),
            ("kdump.nfs_location", ovirt.node.ui.Entry("NFS Location:",
                                                       align_vertical=True)),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        return page

    def on_change(self, changes):
        """Applies the changes to the plugins model, will do all required logic
        """
        self.logger.debug("New (valid) address: %s" % changes)
        if "kdump.type" in changes:
            net_types = ["kdump.ssh_location", "kdump.nfs_location"]

            for w in net_types:
                self._widgets[w].enabled(False)

            w = "kdump.%s_location" % changes["kdump.type"]
            if w in net_types:
                self._widgets[w].enabled(True),

            self._model.update(changes)

    def on_merge(self, effective_changes):
        """Applies the changes to the plugins model, will do all required logic
        Normally on_merge is called by pushing the SaveButton instance, in this
        case it is called by on_change
        """

        if effective_changes:
            self.logger.debug("Generating conf according to model and changes")
        else:
            self.logger.debug("Generating no new conf as there are no changes")
