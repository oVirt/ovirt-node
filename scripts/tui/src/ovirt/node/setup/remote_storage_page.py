#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# remote_storage_page.py - Copyright (C) 2012 Red Hat, Inc.
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
from ovirt.node import utils, valid
from ovirt.node.config import defaults
from ovirt.node.plugins import ChangesHelper
import ovirt.node.plugins
import ovirt.node.ui

"""
Configure Remote Storage
"""


class Plugin(ovirt.node.plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Remote Storage"

    def rank(self):
        return 70

    def model(self):
        icfg = defaults.iSCSI().retrieve()
        ncfg = defaults.NFSv4().retrieve()
        model = {}
        model["iscsi.initiator_name"] = icfg["name"]
        model["nfsv4.domain"] = ncfg["domain"]
        return model

    def validators(self):
        return {
                "iscsi.initiator_name": valid.IQN(),
                "nfsv4.domain": valid.FQDN(),
            }

    def ui_content(self):
        widgets = [
            ("header", ovirt.node.ui.Header("Remote Storage")),

            ("iscsi.initiator_name", ovirt.node.ui.Entry("iSCSI Initiator " +
                                                         "Name:",
                                                         align_vertical=True)),

            ("divider", ovirt.node.ui.Divider()),

            ("nfsv4.domain", ovirt.node.ui.Entry("NFSv4 Domain " +
                                                 "(example.redhat.com):",
                                                 align_vertical=True)),
        ]

        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        self.logger.debug("Saving remote storage page")
        changes = ChangesHelper(self.pending_changes(False))
        model = self.model()
        model.update(effective_changes)
        effective_model = ChangesHelper(model)

        self.logger.debug("Saving remote storage page: %s" % changes.changes)
        self.logger.debug("Remote storage page model: %s" %
                          effective_model.changes)

        iscsi_keys = ["iscsi.initiator_name"]
        # FIXME nfsv4 is missing

        txs = utils.Transaction("Updating remote storage configuration")

        if changes.any_key_in_change(iscsi_keys):
            model = defaults.iSCSI()
            args = effective_model.get_key_values(iscsi_keys)
            args += [None, None, None]  # No target config
            model.update(*args)
            txs += model.transaction()

        txs.prepare()  # Just to display something in dry mode
        self.dry_or(lambda: txs())
