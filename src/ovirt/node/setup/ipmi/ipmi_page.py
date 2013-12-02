#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# cim_page.py - Copyright (C) 2012 Red Hat, Inc.
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
from ovirt.node import base, plugins, ui
from ovirt.node.utils import process
from subprocess import CalledProcessError
"""
IPMI Status
"""


class Plugin(plugins.NodePlugin):
    _model = None

    def __init__(self, app):
        super(Plugin, self).__init__(app)
        self._model = {}

    def has_ui(self):
        return True

    def name(self):
        return "IPMI"

    def rank(self):
        return 50

    def model(self):
        model = {"ipmi.enabled": "%s" % Ipmi().check_status()
                 }
        return model

    def validators(self):
        return {}

    def ui_content(self):
        ws = [ui.Header("header[0]", "IPMI"),
              ui.KeywordLabel("ipmi.enabled", "IPMI Enabled: ")]
        if Ipmi().check_status():
            ws.extend([
                ui.Divider("divider[0]"),
                ui.Header("header[1]", "Fan Status:"),
                ui.Table("ipmi_output", "", "Fan status",
                         Ipmi().fan_status())
            ])

        page = ui.Page("page", ws)
        page.buttons = []
        self.widgets.add(ws)
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        pass


class Ipmi(base.Base):
    def _call_ipmi(self, args):
        assert type(args) is list
        return process.check_output(["ipmitool"] + args, stderr=process.PIPE)

    def fan_status(self):
        return self._call_ipmi(["-I", "open", "sdr", "elist", "full"])

    def check_status(self):
        try:
            process.check_output(["ipmitool", "-I", "open",
                                  "chassis", "status"])
            return True
        except CalledProcessError as e:
            self.logger.warning("IPMI status call failed with: %s" % e.output)
            return False
