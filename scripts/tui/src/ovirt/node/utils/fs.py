#!/usr/bin/python
#
# fs.py - Copyright (C) 2012 Red Hat, Inc.
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
Some convenience functions realted to the filesystem
"""

import logging
import shutil
import os

LOGGER = logging.getLogger(__name__)


def copy_contents(src, dst):
    assert all([os.path.isfile(f) for f in [src, dst]]), \
           "Source and destination need to exist"
    with open(src, "r") as srcf, open(dst, "wb") as dstf:
        dstf.write(srcf.read())


class BackupedFiles(object):
    """This context manager can be used to keep backup of files while messing
    with them.

    >>> txt = "Hello World!"
    >>> dst = "example.txt"
    >>> with open(dst, "w") as f:
    ...     f.write(txt)
    >>> txt == open(dst).read()
    True

    >>> with BackupedFiles([dst]) as backup:
    ...     b = backup.of(dst)
    ...     txt == open(b).read()
    True

    >>> with BackupedFiles([dst]) as backup:
    ...     try:
    ...         open(dst, "w").write("Argh ...").close()
    ...         raise Exception("Something goes wrong ...")
    ...     except:
    ...         backup.restore(dst)
    >>> txt == open(dst).read()
    True

    >>> os.remove(dst)
    """

    files = []
    backups = {}
    suffix = ".backup"

    def __init__(self, files, suffix=".backup"):
        assert type(files) is list, "A list of files is required"
        assert all([os.path.isfile(f) for f in files]), \
               "Not all files exist: %s" % files
        self.files = files
        self.suffix = suffix

    def __enter__(self):
        """Create backups when starting
        """
        for fn in self.files:
            backup = "%s%s" % (fn, self.suffix)
            assert not os.path.exists(backup)
            shutil.copy(fn, backup)
            self.backups[fn] = backup
        return self

    def __exit__(self, a, b, c):
        """Remove all backups when done
        """
        for fn in self.files:
            backup = self.backups[fn]
            os.remove(backup)

    def of(self, fn):
        """Returns the backup file for the given file
        """
        assert fn in self.backups, "No backup for '%s'" % fn
        return self.backups[fn]

    def restore(self, fn):
        """Restore contens of a previously backupe file
        """
        copy_contents(self.of(fn), fn)
