#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# tuned.py - Copyright (C) 2013 Red Hat, Inc.
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
from ovirt.node import utils
from ovirt.node.utils import tuned
from ovirt.node.config.defaults import NodeConfigFileSection
from ovirt.node.exceptions import InvalidData


class Tuned(NodeConfigFileSection):
    """Configure tuned
    """
    keys = ("OVIRT_TUNED_PROFILE",)

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, profile):
        all_profiles = tuned.get_available_profiles()
        if profile not in all_profiles:
            raise InvalidData("Unknown tuned profile: %s" % profile)
        return {"OVIRT_TUNED_PROFILE": profile}

    def transaction(self):
        # This method builds a transaction to modify the system
        # according to the values of self.keys
        # E.g. the value of OVIRT_TUNED_PROFILE needs to be passed to
        # the tuned client

        # We read the profile name from the defaults file
        profile = self.retrieve()["profile"]

        class CallTunedAdm(utils.Transaction.Element):
            title = "Requesting profile change"

            def commit(self):
                tuned.set_active_profile(profile)

        tx = utils.Transaction("Applying tuned configuration")
        if profile:
            # Only add the element if there is a profile to be set
            tx.append(CallTunedAdm())
        return tx
