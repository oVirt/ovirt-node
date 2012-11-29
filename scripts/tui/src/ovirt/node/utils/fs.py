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

from ovirt.node.utils import checksum, is_bind_mount
from ovirt.node import base
from process import system

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
           "Source and destination need to exist"
    with open(src, "r") as srcf, open(dst, "wb") as dstf:
        dstf.write(srcf.read())


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

    def create(self):
        """Create a backup of all files
        """
        for fn in self.files:
            backup = "%s%s" % (fn, self.suffix)
            assert not os.path.exists(backup)
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


def persist_config(filename):
    LOGGER.info("Persisting: %s" % filename)
    filenames = []

#    if is_stateless():
#        return True
    if not os.path.ismount(persist_path()):
        LOGGER.warning("/config is not mounted")
        return False
    if type(filename) in [str, unicode]:
        filenames.append(filename)
    elif type(filename) is list:
        filenames = filename
    else:
        LOGGER.error("Unknown type: %s" % filename)
        return False

    persist_failed = False
    for f in filenames:
        filename = os.path.abspath(f)

        if os.path.isdir(filename):
            # ensure that, if this is a directory
            # that it's not already persisted
            if os.path.isdir(persist_path(filename)):
                LOGGER.warn("Directory already persisted: %s" % filename)
                LOGGER.warn("You need to unpersist its child directories " +
                            "and/or files and try again.")
                continue

        elif os.path.isfile(filename):
            # if it's a file then make sure it's not already persisted
            persist_filename = persist_path(filename)
            if os.path.isfile(persist_filename):
                if checksum(filename) == checksum(persist_filename):
                    # FIXME yes, there could be collisions ...
                    LOGGER.info("Persisted file is equal: %s" % filename)
                    continue
                else:
                    # Remove persistent copy - needs refresh
                    if system("umount -n %s 2> /dev/null" % filename):
                        system("rm -f %s" % persist_filename)

        else:
            # skip if file does not exist
            LOGGER.warn("Skipping, file '%s' does not exist" % filename)
            continue

        # At this poitn we know that we want to persist the file.

        # skip if already bind-mounted
        if is_bind_mount(filename):
            LOGGER.warn("%s is already persisted" % filename)
        else:
            dirname = os.path.dirname(filename)
            system("mkdir -p %s" % persist_path(dirname))
            persist_filename = persist_path(filename)
            if system("cp -a %s %s" % (filename, persist_filename)):
                if not system("mount -n --bind %s %s" % (persist_filename,
                                                         filename)):
                    LOGGER.error("Failed to persist: " + filename)
                    persist_failed = True
                else:
                    LOGGER.info("Persisted: $s" % filename)

        with open(persist_path("files"), "r") as files:
            if filename not in files.read().split("\n"):
                # register in /config/files used by rc.sysinit
                system("echo " + filename + " >> /config/files")
                LOGGER.info("Successfully persisted (reg): %s" % filename)
    return not persist_failed


def persist_path(filename=""):
    """Returns the path a file will be persisted in

    Returns:
        Path to the persisted variant of the file.
    """
    return os.path.join("/config", os.path.abspath(filename))


def is_persisted(filename):
    """Check if the file is persisted

    Args:
        filename: Filename to be checked
    Returns:
        True if the file exists in the /config hierarchy
    """
    return os.path.exists(persist_path(filename))


def unpersist_config(filename):
    LOGGER.info("Unpersisting: %s" % filename)
    # FIXME
