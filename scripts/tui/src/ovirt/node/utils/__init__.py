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

import logging
import hashlib
import re
import augeas as _augeas

LOGGER = logging.getLogger(__name__)


class AugeasWrapper(object):
    _aug = _augeas.Augeas()

    def __init__(self):
#        self._aug = _augeas.Augeas() # Is broken
        self._aug.set("/augeas/save/copy_if_rename_fails", "")

    def get(self, p, strip_quotes=False):
        v = self._aug.get(p)
        if v and strip_quotes:
            v = v.strip("'\"")
        return v

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


def checksum(filename, algo="md5"):
    """Calculcate the checksum for a file.
    """
    # FIXME switch to some other later on
    m = hashlib.md5()
    with open(filename) as f:
        data = f.read(4096)
        while data:
            m.update(data)
            data = f.read(4096)
        return m.hexdigest()


def is_bind_mount(filename, fsprefix="ext"):
    """Checks if a given file is bind mounted

    Args:
        filename: File to be checked
    Returns:
        True if the file is a bind mount target
    """
    bind_mount_found = False
    with open("/proc/mounts") as mounts:
        pattern = "%s %s" % (filename, fsprefix)
        for mount in mounts:
            if pattern in mount:
                bind_mount_found = True
    return bind_mount_found


def parse_bool(txt):
    """Parse common "bool" values (yes, no, true, false, 1)

    >>> parse_bool(True)
    True

    >>> txts = ["yes", "YES!", "1", 1]
    >>> all((parse_bool(txt) for txt in txts))
    True

    >>> txts = ["no", "NO!", "0", 0, False, None, "foo"]
    >>> all((not parse_bool(txt) for txt in txts))
    True

    Args:
        txt: Text to be parsed
    Returns:
        True if it looks like a bool representing True, False otherwise
    """
    if txt != None and type(txt) in [str, unicode, int, bool]:
        utxt = unicode(txt)
        if len(utxt) > 0 and utxt[0] in ["y", "t", "Y", "T", "1"]:
            return True
    return False
