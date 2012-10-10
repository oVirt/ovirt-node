#!/usr/bin/python
#
# __init__.py - Copyright (C) 2012 Red Hat, Inc.
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
Utility functions
"""

import augeas as _augeas
import logging

LOGGER = logging.getLogger(__name__)


class AugeasWrapper(object):
    _aug = _augeas.Augeas()

    def __init__(self):
#        self._aug = _augeas.Augeas() # Is broken
        self._aug.set("/augeas/save/copy_if_rename_fails", "")

    def get(self, p):
        return self._aug.get(p)

    def set(self, p, v):
        self._aug.set(p, v)
        self.save()

    def remove(self, p):
        self._aug.remove(p)
        self.save()

    def save(self):
        return self._aug.save()

    def match(self, p):
        return self._aug.match(p)
