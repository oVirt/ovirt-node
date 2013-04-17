#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# kdump_page.py - Copyright (C) 2012 Red Hat, Inc.
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

from ovirt.node import utils, plugins, ui, valid
from ovirt.node.config import defaults
from ovirt.node.plugins import Changeset
from ovirt.node.utils import console


class Plugin(plugins.NodePlugin):
    _model = None

    _types = [("disabled", "Disable"),
              ("local", "Local"),
              ("ssh", "SSH"),
              ("nfs", "NFS")]

    def name(self):
        return "Kdump"

    def rank(self):
        return 60

    def model(self):
        """Returns the model of this plugin
        This is expected to parse files and all stuff to build up the model.
        """
        cfg = defaults.KDump().retrieve()

        ktype = "disabled"
        for k in ["local", "ssh", "nfs"]:
            if cfg[k]:
                ktype = k
                break

        model = {
            # The target address
            "kdump.type": ktype,
            "kdump.ssh_location": cfg["ssh"]or "",
            "kdump.nfs_location": cfg["nfs"]or "",
        }
        self.logger.debug(model)
        return model

    def validators(self):
        """Validators validate the input on change and give UI feedback
        """
        # FIXME improve validation for ssh and nfs
        return {"kdump.type": valid.Options(dict(self._types).keys()),
                "kdump.ssh_location": valid.Empty() | valid.NoSpaces(),
                "kdump.nfs_location": valid.Empty() | valid.NoSpaces(),
                }

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        ws = [ui.Header("kdump._header", "Configure Kdump"),
              ui.Options("kdump.type", "Type", self._types),
              ui.Entry("kdump.nfs_location", "NFS Location " +
                       "(example.com:/var/crash):",
                       align_vertical=True),
              ui.Divider("divider[0]"),
              ui.Entry("kdump.ssh_location", "SSH Location " +
                       "(root@example.com):",
                       align_vertical=True),
              ]
        page = ui.Page("page", ws)
        self.widgets.add(page)
        return page

    def on_change(self, changes):
        """Applies the changes to the plugins model, will do all required logic
        """
        self.logger.debug("New (valid) address: %s" % changes)
        if "kdump.type" in changes:
            net_types = ["kdump.ssh_location", "kdump.nfs_location"]

            for w in net_types:
                self.widgets[w].enabled(False)

            w = "kdump.%s_location" % changes["kdump.type"]
            if w in net_types:
                self.widgets[w].enabled(True),
                self.validate({w: ""})

    def on_merge(self, effective_changes):
        """Applies the changes to the plugins model, will do all required logic
        Normally on_merge is called by pushing the SaveButton instance, in this
        case it is called by on_change
        """
        self.logger.debug("Saving kdump page")
        changes = Changeset(self.pending_changes(False))
        effective_model = Changeset(self.model())
        effective_model.update(effective_changes)

        self.logger.debug("Changes: %s" % changes)
        self.logger.debug("Effective Model: %s" % effective_model)

        kdump_keys = ["kdump.type", "kdump.ssh_location", "kdump.nfs_location"]

        txs = utils.Transaction("Updating kdump related configuration")

        if changes.contains_any(kdump_keys):
            model = defaults.KDump()
            ktype, sshloc, nfsloc = effective_model.values_for(kdump_keys)
            if ktype == "nfs":
                model.update(nfsloc, None, None)
            elif ktype == "ssh":
                model.update(None, sshloc, None)
            elif ktype == "local":
                model.update(None, None, True)
            else:
                model.update(None, None, None)
            txs += model.transaction()

        with self.application.ui.suspended():
            utils.process.call("reset")
            progress_dialog = console.TransactionProgress(txs, self)
            progress_dialog.run()
            console.writeln("\nPlease press any key to continue")
            console.wait_for_keypress()
