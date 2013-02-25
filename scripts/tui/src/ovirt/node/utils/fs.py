#!/usr/bin/python
# -*- coding: utf-8 -*-
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

from ovirt.node import base

LOGGER = logging.getLogger(__name__)


def get_contents(src):
    """Read the contents of a file

    Args:
        src: The file to be read
    Returns:
        The contents of src
    """
    with open(src, "r") as f:
        contents = f.read()
    return contents


def copy_contents(src, dst):
    assert all([os.path.isfile(f) for f in [src, dst]]), \
        "Source '%s' and destination '%s' need to exist" % (src, dst)
    with open(src, "r") as srcf, open(dst, "wb") as dstf:
        dstf.write(srcf.read())


def atomic_write(filename, contents):
    backup = BackupedFiles([filename], ".temp")
    backup.create()
    backup_filename = backup.of(filename)

    with open(backup_filename, "wb") as dst:
        dst.write(contents)

    fns = (backup_filename, filename)
    LOGGER.debug("Moving '%s' to '%s' atomically" % fns)
    try:
        os.rename(*fns)
    except Exception:
        backup.remove()
        LOGGER.debug("Error on moving file '%s'" % fns, exc_info=True)
        raise


def truncate(filename):
    """Truncate the given file to the length 0
    """
    with open(filename, "wb"):
        pass


class BackupedFiles(base.Base):
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
        super(BackupedFiles, self).__init__()
        assert type(files) is list, "A list of files is required"
        if any([not os.path.isfile(f) for f in files]):
            self.logger.warning("Not all files exist: %s" % files)
        self.files = files
        self.suffix = suffix

    def __enter__(self):
        """Create backups when starting
        """
        self.create()
        return self

    def __exit__(self, a, b, c):
        """Remove all backups when done
        """
        self.remove()

    def create(self, ignore_existing=False):
        """Create a backup of all files
        """
        for fn in self.files:
            backup = "%s%s" % (fn, self.suffix)
            if not ignore_existing and os.path.exists(backup):
                raise RuntimeError(("Backup '%s' for '%s " +
                                    "already exists") % (backup, fn))
            if os.path.exists(fn):
                shutil.copy(fn, backup)
                self.backups[fn] = backup
            else:
                self.logger.warning("Can not backup non-existent " +
                                    "file: %s" % fn)

    def remove(self):
        """Remove all backups
        """
        for fn in self.files:
            backup = self.backups[fn]
            self.logger.debug("Removing backup of '%s': %s" % (fn, backup))
            os.remove(backup)

    def of(self, fn):
        """Returns the backup file for the given file
        """
        #assert fn in self.backups, "No backup for '%s'" % fn
        if fn in self.backups:
            return self.backups[fn]
        return None

    def restore(self, fn):
        """Restore contens of a previously backupe file
        """
        copy_contents(self.of(fn), fn)


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


class Config(base.Base):
    """oVirt Node specififc way to persist files
    """
    basedir = "/config"

    def _config_path(self, fn=""):
        return os.path.join(self.basedir, fn.strip("/"))

    def persist(self, filename):
        """Persist a file and bind mount it
        """
        if filename:
            from ovirtnode import ovirtfunctions
            return ovirtfunctions.ovirt_store_config(filename)

    def unpersist(self, filename):
        """Remove the persistent version of a file and remove the bind mount
        """
        if filename:
            from ovirtnode import ovirtfunctions
            return ovirtfunctions.remove_config(filename)

    def exists(self, filename):
        """Check if the given file is persisted
        """
        return filename and os.path.exists(self._config_path(filename))

    def is_enabled(self):
        return is_bind_mount(self.basedir)

    def open_file(self, filename, mode="r"):
        return open(self._config_path(filename), mode)
