#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# performance_page.py - Copyright (C) 2013 Red Hat, Inc.
# Written by Mike Burns <mburns@redhat.com>
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
from ovirt.node import plugins, ui
import ovirt.node.utils.tuned as tuned
from ovirt.node.config import tuned as tunedconf

"""
Configure Performance Profiles
"""


class Plugin(plugins.NodePlugin):
    _model = None

    def name(self):
        return _("Performance")

    def rank(self):
        return 100

    def model(self):
        profile = tuned.get_active_profile()
        model = {
            "tuned.profile": profile,
        }
        return model

    def validators(self):
        return {}

    def ui_content(self):
        profiles = [(profile, profile) for profile in
                    tuned.get_available_profiles()]

        ws = [ui.Header("header", _("Tuned Configuration")),
              ui.Label("label", _("Choose the tuned profile you would ") +
                       _("like to apply to this system.")),
              ui.Divider("divider[0]"),
              ui.KeywordLabel("tuned.profile", _("Current Active Profile:  ")),
              ui.Table("tuned.profile", "", _("Available tuned Profiles"),
                       profiles),
              ]
        page = ui.Page("page", ws)
        page.buttons = [ui.SaveButton("page.save", _("Save"))]
        self.widgets.add(page)
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        # changes will only contain changes compared to the original
        # contents

        effective_model = self.model()
        effective_model.update(effective_changes)
        # Using the effective_model ensures that we've always got a
        # profile
        if "tuned.profile" in effective_changes:
            model = tunedconf.Tuned()

            # Set keys:
            model.update(effective_model["tuned.profile"])

            # Get transaction for keys:
            txs = model.transaction()

            # Run transaction in nice UI:
            ui.TransactionProgressDialog("dialog.txs", txs, self).run()

        return self.ui_content()
