#!/usr/bin/python
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

"""
Configure Remote Storage
"""
import logging

import ovirt.node.plugins
import ovirt.node.valid
import ovirt.node.ui
import ovirt.node.utils

LOGGER = logging.getLogger(__name__)


class Plugin(ovirt.node.plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Remote Storage"

    def rank(self):
        return 70

    def model(self):
        if not self._model:
            self._model = {
                "iscsi.initiator_name": "",
            }
        return self._model

    def validators(self):
        is_initiator_name = lambda v: (None if len(v.split(":")) == 2
                                            else "Invalid IQN.")
        return {
                "iscsi.initiator_name": is_initiator_name,
            }

    def ui_content(self):
        widgets = [
            ("header", ovirt.node.ui.Header("Remote Storage")),

            ("iscsi.initiator_name", ovirt.node.ui.Entry("iSCSI Initiator " +
                                                         "Name:",
                                                         align_vertical=True)),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ovirt.node.ui.Page(widgets)
        return page

    def on_change(self, changes):
        pass
        self._model.update(changes)

    def on_merge(self, effective_changes):
        pass
