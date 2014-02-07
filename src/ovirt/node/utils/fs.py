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

from ovirt.node import log
from ovirt.node.utils import process, parse_varfile
import shutil
import os
import re
import StringIO

from ovirt.node import base

LOGGER = log.getLogger(__name__)


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
    with open(src, "r") as srcf:
        with open(dst, "wb") as dstf:
            dstf.write(srcf.read())


def atomic_write(filename, contents, mode="wb"):
    backup = BackupedFiles([filename], ".temp")
    backup.create()
    backup_filename = backup.of(filename)

    with open(backup_filename, mode) as dst:
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


class File(base.Base):
    """Convenience API to access files.
    Used to make code testable
    """
    filename = None

    def __init__(self, filename):
        base.Base.__init__(self)
        self.filename = filename

    def read(self):
        """Read the contents of a file
        """
        return get_contents(self.filename)

    def write(self, contents, mode="wb"):
        """Write the contents of a file
        """
        try:
            atomic_write(self.filename, contents, mode)
        except:
            with open(self.filename, mode) as dst:
                dst.write(contents)

    def touch(self):
        """Touch a file
        """
        return truncate(self.filename)

    def exists(self):
        """Determin if a file exists
        """
        return os.path.exists(self.filename)

    def delete(self):
        """Delete a file
        """
        return os.unlink(self.filename)

    def access(self, mode):
        """Check if the file can be accessed
        """
        return os.access(self.filename, mode)

    def sed(self, expr, inplace=True):
        """Run a sed expression on the file
        """
        cmd = ["sed", "-c"]
        if inplace:
            cmd.append("-i")
        cmd += ["-e", expr, self.filename]
        return process.pipe(cmd)

    def sub(self, pat, repl, count=0, inplace=True):
        """Run a regexp subs. on each lien of the file

        Args:
            inplace: If the contents shall be directly replaced
        Returns:
            The new value
        """
        newval = ""
        for line in self:
            newval += re.sub(pat, repl, line, count)
        if inplace:
            self.write(newval)
        return newval

    def findall(self, pat, flags=0):
        """Find all regexps in all lines of the file
        """
        matches = []
        for line in self:
            matches += re.findall(pat, line, flags)
        return matches

    def __iter__(self):
        with open(self.filename, "r") as src:
            for line in src:
                yield line


class FakeFs(base.Base):
    filemap = {}

    @staticmethod
    def erase():
        """Erase all files
        """
        FakeFs.filemap = {}

    @staticmethod
    def listdir(path):
        files = []
        for fn in FakeFs.filemap.keys():
            if os.path.dirname(fn) == path:
                files.append(os.path.basename(fn))
        return files

    class File(File):
        """A fake file - residing in a dictiniory for testing

        >>> FakeFs.filemap
        {}
        >>> f = FakeFs.File("/etc/foo")
        >>> f.write("Hello World!")
        >>> f.read()
        'Hello World!'
        >>> FakeFs.filemap.keys()
        ['/etc/foo']
        >>> f.write("Hey Mars!\\nWhat's up?")
        >>> f.read()
        "Hey Mars!\\nWhat's up?"
        >>> for line in f:
        ...     print("line: %s" % line)
        line: Hey Mars!
        <BLANKLINE>
        line: What's up?
        >>> f.delete()
        >>> FakeFs.filemap
        {}

        >>> FakeFs.File("foo").write("bar")
        >>> FakeFs.filemap
        {'foo': 'bar'}

        >>> b = FakeFs.File("foo")
        >>> b.sub("b(ar)", r"ro\\1")
        'roar'

        >>> b.findall("oa")
        ['oa']
        >>> b.findall("Boa")
        []

        >>> FakeFs.erase()
        >>> FakeFs.filemap
        {}
        """

        def _cond_create(self):
            if not self.exists():
                FakeFs.filemap[self.filename] = ""

        def read(self):
            self._cond_create()
            return FakeFs.filemap[self.filename]

        def write(self, contents, mode=None):
            self.logger.debug("Saving: %s" % self.filename)
            self.logger.debug("Writing:\n%s" % contents)
            self._cond_create()
            FakeFs.filemap[self.filename] = contents

        def touch(self):
            self._cond_create()

        def exists(self):
            return self.filename in FakeFs.filemap

        def delete(self):
            if self.exists():
                del FakeFs.filemap[self.filename]

        def access(self, mode):
            return self.filename in FakeFs.filemap

        def __iter__(self):
            for line in StringIO.StringIO(self.read()):
                yield line


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
            self.logger.debug("Not all files exist: %s" % files)
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
                self.logger.debug("Can not backup non-existent " +
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
    mounts = File("/proc/mounts")
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
        if filename and self.is_enabled():
            from ovirtnode import ovirtfunctions
            return ovirtfunctions.ovirt_store_config(filename)

    def unpersist(self, filename):
        """Remove the persistent version of a file and remove the bind mount
        """
        if filename and self.is_enabled():
            from ovirtnode import ovirtfunctions
            return ovirtfunctions.remove_config(filename)

    def delete(self, filename):
        """Remove the persiste version and the file
        """
        if filename and self.is_enabled():
            from ovirtnode import ovirtfunctions
            return ovirtfunctions.ovirt_safe_delete_config(filename)

    def exists(self, filename):
        """Check if the given file is persisted
        """
        return filename and File(self._config_path(filename)).exists()

    def is_enabled(self):
        return File("/proc").exists() and is_bind_mount(self.basedir)

    def open_file(self, filename, mode="r"):
        return open(self._config_path(filename), mode)


class ShellVarFile(base.Base):
    """ShellVarFile writes simple KEY=VALUE (shell-like) configuration file

    >>> cfg = {
    ... "IP_ADDR": "127.0.0.1",
    ... "NETMASK": "255.255.255.0",
    ... }
    >>> p = ShellVarFile(FakeFs.File("dst-file"))
    >>> p.get_dict()
    {}
    >>> p.update(cfg, True)
    >>> p.get_dict() == cfg
    True
    """
    filename = None
    _fileobj = None
    create = False

    def __init__(self, filename, create=False):
        super(ShellVarFile, self).__init__()
        self.filename = filename
        self.create = create
        if File in type(filename).mro():
            self._fileobj = filename
        else:
            self._fileobj = File(self.filename)
            if not create and not self._fileobj.exists():
                    raise RuntimeError("File does not exist: %s" %
                                       self.filename)

    def _read_contents(self):
        return self._fileobj.read()

    def raw_read(self):
        return self._read_contents()

    def _write_contents(self, data):
        self._fileobj.write(data)

    def exists(self):
        """Return true if this file exists
        """
        return self._fileobj.exists()

    def get_dict(self):
        """Returns a dict of (key, value) pairs
        """
        data = self._read_contents()
        return self._parse_dict(data)

    def write(self, cfg, remove_empty=True):
        """Write a dictinory as a key-val file
        """
        for key, value in cfg.items():
            if remove_empty and value is None:
                del cfg[key]
            if value is not None and type(value) not in [str, unicode]:
                raise TypeError("The type (%s) of %s is not allowed" %
                                (type(value), key))
        lines = []
        # Sort the dict, looks nicer
        for key in sorted(cfg.iterkeys()):
            lines.append("%s=\"%s\"" % (key, cfg[key]))
        contents = "\n".join(lines) + "\n"
        self._write_contents(contents)

    def update(self, new_dict, remove_empty):
        """Update the file using new_dict
        Keys not present in the dict, but present in the file will be kept in
        the file.

        Args:
            new_dict: A dictionary containing the keys to be updated
            remove_empty: Remove keys from file if their value in new_dict
                          is None.
                          If False then the keys will be added to the file
                          without any value. (Aka flags)
        """
        self.logger.debug("Updating defaults: %s" % new_dict)
        self.logger.debug("Removing empty entries? %s" % remove_empty)
        cfg = self.get_dict()
        cfg.update(new_dict)
        self.write(cfg, remove_empty)

    def _parse_dict(self, txt):
        """Parse a simple shell-var-style lines into a dict:

        >>> import StringIO
        >>> txt = "# A comment\\n"
        >>> txt += "A=ah\\n"
        >>> txt += "B=beh\\n"
        >>> txt += "C=\\"ceh\\"\\n"
        >>> txt += "D=\\"more=less\\"\\n"
        >>> p = ShellVarFile(StringIO.StringIO(), True)
        >>> sorted(p._parse_dict(txt).items())
        [('A', 'ah'), ('B', 'beh'), ('C', 'ceh'), ('D', 'more=less')]
        """
        return parse_varfile(txt)
