#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# fs/__init__.py - Copyright (C) 2012-2014 Red Hat, Inc.
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
from __future__ import print_function

import shutil
import errno
import os
import stat
import StringIO
import re
import hashlib
import logging


from . import mount
from .. import process, parse_varfile
from ... import base

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())


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


def restorecon(path):
    """Restore the context of the given path

    Import is inside the function to address circular imports
    """
    from ...utils import security
    security.Selinux().restorecon(path)


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

        >>> f = File("/tmp/afile")
        >>> f.write("Woot")

        Replacement without inplace modifcation:

        >>> f.sed("s/oo/ha/", False)
        u'What'

        Replacement with inplace modifications:

        >>> f.sed("s/oo/alle/")
        >>> f.read()
        'Wallet'

        Chaining of expressions also works:

        >>> f.sed("s/alle/oo/ ; s/oo/ha/", False)
        u'What'

        >>> f.delete()
        """
        cmd = ["sed"]
        if inplace:
            cmd.append("-ci")
        cmd += ["-e", expr, self.filename]
        stdout = process.check_output(cmd)
        return None if inplace else stdout

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

        def sed(self, expr, inplace=True):
            newval = process.pipe(["sed", "-e", expr],
                                  stdin=self.read())
            if inplace:
                self.write(newval)
            return newval

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
        # assert fn in self.backups, "No backup for '%s'" % fn
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
    mounts = File("/proc/mounts")
    pattern = "%s %s" % (filename, fsprefix)
    return any(pattern in mountp for mountp in mounts)


class Config(base.Base):
    """oVirt Node specififc way to persist files
    """
    basedir = '/config'
    path_entries = '/config/files'

    def _config_path(self, fn=""):
        return os.path.join(self.basedir, fn.strip("/"))

    def persist(self, path):
        """Persist path and bind mount it back to its current location
        """
        # TODO: Abort if it is stateless
        if not self.is_enabled():
            return

        if path is None:
            return

        abspath = os.path.abspath(path)
        if os.path.exists(abspath):
            # Check first for symlinks as os.path file type detection follows
            # links and will give the type of the target
            try:
                if os.path.islink(abspath):
                    self._persist_symlink(abspath)
                elif os.path.isdir(abspath):
                    self._persist_dir(abspath)
                elif os.path.isfile(abspath):
                    self._persist_file(abspath)
            except Exception:
                self._logger.error('Failed to persist "%s"', path,
                                   exc_info=True)
                return -1

            restorecon(abspath)
            return True

    def copy_attributes(self, abspath, destpath):
        """Copy the owner/group, selinux context from abspath to destpath"""

        if not os.path.exists(abspath) or not os.path.exists(destpath):
            raise RuntimeError("Cannot proceed, check if paths exist!")

        abspath_stat = os.stat(abspath)
        owner = abspath_stat[stat.ST_UID]
        group = abspath_stat[stat.ST_GID]
        os.chown(destpath, owner, group)

        from ...utils import security
        security.Selinux().chcon(destpath,
                                 security.Selinux().getcon(abspath))

    def _persist_dir(self, abspath):
        """Persist directory and bind mount it back to its current location
        """
        persisted_path = self._config_path(abspath)
        if os.path.exists(persisted_path):
            self._logger.warn('Directory "%s" had already been persisted',
                              abspath)
            return

        shutil.copytree(abspath, persisted_path, symlinks=True)
        self.copy_attributes(abspath, persisted_path)
        mount.mount(persisted_path, abspath, flags=mount.MS_BIND)
        self._logger.info('Directory "%s" successfully persisted', abspath)
        self._add_path_entry(abspath)

    def cksum(self, filename):
        try:
            m = hashlib.md5()
        except:
            m = hashlib.sha1()

        with open(filename) as f:
            data = f.read(4096)
            while data:
                m.update(data)
                data = f.read(4096)
            return m.hexdigest()

    def _persist_file(self, abspath):
        """Persist file and bind mount it back to its current location
        """

        persisted_path = self._config_path(abspath)
        if os.path.exists(persisted_path):
            current_checksum = self.cksum(abspath)
            stored_checksum = self.cksum(persisted_path)
            if stored_checksum == current_checksum:
                self._logger.warn('File "%s" had already been persisted',
                                  abspath)
                return
            else:
                # If this happens, somehow the bind mount was undone, so we try
                # and clean up before re-persisting
                try:
                    if mount.ismount(abspath):
                        mount.umount(abspath)
                    os.unlink(persisted_path)
                except OSError as ose:
                    self._logger.error('Failed to clean up persisted file '
                                       '"%s": %s', abspath, ose.message)
        self._prepare_dir(abspath, persisted_path)
        shutil.copy2(abspath, persisted_path)
        self.copy_attributes(abspath, persisted_path)
        mount.mount(persisted_path, abspath, flags=mount.MS_BIND)
        self._logger.info('File "%s" successfully persisted', abspath)
        self._add_path_entry(abspath)

    def _persist_symlink(self, abspath):
        """Persist symbolic link and bind mount it back to its current location
        """
        persisted_path = self._config_path(abspath)
        current_target = os.readlink(abspath)
        if os.path.exists(persisted_path):
            stored_target = os.readlink(persisted_path)
            if stored_target == current_target:
                self._logger.warn('Symlink "%s" had already been persisted',
                                  abspath)
                return
            else:
                # Write the new symlink to an alternate location and atomically
                # rename
                self._prepare_dir(abspath, persisted_path)
                tmp_path = persisted_path + '.ovirtnode.atom'
                try:
                    os.symlink(current_target, tmp_path)
                except Exception:
                    raise
                else:
                    os.rename(tmp_path, persisted_path)
        else:
            self._prepare_dir(abspath, persisted_path)
            os.symlink(current_target, persisted_path)

        self.copy_attributes(abspath, persisted_path)
        self._logger.info('Symbolic link "%s" successfully persisted', abspath)
        self._add_path_entry(abspath)

    def _prepare_dir(self, abspath, persisted_path):
        """Creates the necessary directory structure for persisted abspath
        """
        dir_path = os.path.dirname(persisted_path)
        try:
            os.makedirs(dir_path)
        except OSError as ose:
            if ose.errno != errno.EEXIST:
                self._logger.error('Failed to create the directories '
                                   'necessary to persist %s: %s', abspath, ose)
                raise

    def _persisted_path_entries(self):
        """Generates the entries in /config/files
        """
        with open(self.path_entries) as path_entries:
            for entry in path_entries:
                yield entry.strip()

    def _add_path_entry(self, abspath):
        """Adds abspath to /config/files
        """
        matches = (entry for entry in self._persisted_path_entries() if
                   entry == abspath)
        if any(matches):
            pass  # Entry already present
        else:
            matches.close()  # Close iterator so that path_entries is closed
            with open(self.path_entries, 'a') as path_entries:
                print(abspath, file=path_entries)

    def _del_path_entry(self, abspath):
        """Removes a path entry from the /config/files entries
        """
        filtered = '\n'.join(entry for entry in self._persisted_path_entries()
                             if entry != abspath)
        with open(self.path_entries, 'w') as path_entries:
            print(filtered, file=path_entries)

    def unpersist(self, path):
        """Remove the persistent version of a file and remove the bind mount
        """
        if not self.is_enabled():
            return

        if path is None:
            return

        abspath = os.path.abspath(path)
        if os.path.exists(abspath):
            # Check first for symlinks as os.path file type detection follows
            # links and will give the type of the target
            try:
                if os.path.islink(abspath):
                    self._unpersist_symlink(abspath)
                elif os.path.isdir(abspath):
                    self._unpersist_dir(abspath)
                elif os.path.isfile(abspath):
                    self._unpersist_file(abspath)
            except Exception:
                self._logger.error('Failed to unpersist "%s"', path,
                                   exc_info=True)
                return -1
        return True

    def _cleanup_tree(self, dirpath):
        """Removes empty directories in the structure. abspath must be a dir"""
        path = dirpath
        while True:
            try:
                os.rmdir(path)
            except OSError as ose:
                if ose.errno == errno.ENOTEMPTY:
                    self._logger.debug('Cleaned up "%s" all the way up to '
                                       '(not including) "%s"', dirpath, path)
                    break
                else:
                    raise
            path = os.path.dirname(path)

    def _unpersist_dir(self, abspath):
        """Remove the persistent version of a directory and refresh the version
        in the live filesystem with what was persisted"""
        persisted_path = self._config_path(abspath)
        if not mount.isbindmount(abspath):
            self._logger.warn('The directory "%s" is not a persisted element',
                              abspath)
            return
        mount.umount(abspath)
        # Remove the original contents and replace them with what was persisted
        # up until now
        shutil.rmtree(abspath)
        shutil.copytree(persisted_path, abspath, symlinks=True)
        shutil.rmtree(persisted_path)
        self._del_path_entry(abspath)
        self._cleanup_tree(os.path.dirname(persisted_path))
        self._logger.info('Successfully unpersisted directory "%s"', abspath)

    def _unpersist_file(self, abspath):
        """Remove the persistent version of a file and refresh the version in
        the live filesystem with what was persisted"""
        persisted_path = self._config_path(abspath)
        if not mount.ismount(abspath):
            self._logger.warn('The file "%s" is not a persisted element',
                              abspath)
            return
        mount.umount(abspath)
        shutil.copy2(persisted_path, abspath)
        os.unlink(persisted_path)
        self._del_path_entry(abspath)
        self._cleanup_tree(os.path.dirname(persisted_path))
        self._logger.info('Successfully unpersisted file "%s"', abspath)

    def _unpersist_symlink(self, abspath):
        """Remove the persistent version of a symlink. Symlinks are not bind
        mounted so that won't be necessary"""
        persisted_path = self._config_path(abspath)
        try:
            stored_target = os.readlink(persisted_path)
        except OSError as ose:
            if ose.errno == errno.ENOENT:
                self._logger.warn('The symlink "%s" is not a persisted '
                                  'element', abspath)
                return

        # Update the link with the current persisted version
        os.unlink(abspath)
        os.symlink(stored_target, abspath)
        os.unlink(persisted_path)
        self._del_path_entry(abspath)
        self._cleanup_tree(os.path.dirname(persisted_path))
        self._logger.info('Successfully unpersisted symlink "%s"', abspath)

    def delete(self, filename):
        """Remove the persiste version and the file
        """
        if filename and self.is_enabled():
            from ovirtnode import ovirtfunctions
            return ovirtfunctions.ovirt_safe_delete_config(filename)

    def exists(self, filename):
        """Check if the given file is persisted
        """
        filename = os.path.abspath(filename)
        persisted_path = self._config_path(filename)

        if not os.path.exists(persisted_path) or \
                not os.path.exists(filename):
            return False

        if os.path.isfile(filename):
            current_checksum = self.cksum(filename)
            stored_checksum = self.cksum(persisted_path)
            if stored_checksum != current_checksum:
                return False

        return True

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
