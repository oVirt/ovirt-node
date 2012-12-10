#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# system.py - Copyright (C) 2012 Red Hat, Inc.
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
A module to access system wide stuff
e.g. services, reboot ...
"""

from ovirt.node import base, utils
from ovirt.node.utils import process


def reboot():
    process.system("reboot")


def poweroff():
    process.system("poweroff")


class ProductInformation(base.Base):
    _version_filename = "/files/etc/default/version"
    PRODUCT_SHORT = None
    VERSION = None
    RLEASE = None

    def __init__(self):
        self.load()

    def load(self):
        aug = utils.AugeasWrapper()
        augg = lambda k: aug.get("\n%s/%s\n" % (self._version_filename, k),
                                                strip_quotes=True)

        # read product / version info
        self.PRODUCT_SHORT = augg("PRODUCT_SHORT") or "oVirt"
        self.VERSION = augg("VERSION")
        self.RELEASE = augg("RELEASE")
