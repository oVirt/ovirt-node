#!/usr/bin/python
# -*- coding: utf-8 -*-
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
oVirt Node specific exceptions
"""


class ExceptionWithMessage(Exception):
    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self.message)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, repr(self.message))


class InvalidData(ExceptionWithMessage):
    """E.g. if a string contains characters which are not allowed
    """
    pass


class Concern(InvalidData):
    """E.g. if a password is not secure enough
    FIXME very ... unspecific
    """
    pass


class TransactionError(ExceptionWithMessage):
    pass


class PreconditionError(TransactionError):
    pass
