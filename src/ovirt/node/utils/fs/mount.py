#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# mount.py - Copyright (C) 2014 Red Hat, Inc.
# Written by Antoni Segura Puimedon <asegurap@redhat.com>
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
File system mounting bindings
"""

import collections
import ctypes
import os

LIBC = ctypes.CDLL('libc.so.6', use_errno=True)

MS_RDONLY = 1  # Mount read-only.
MS_NOSUID = 2  # Ignore suid and sgid bits.
MS_NODEV = 4  # Disallow access to device special files.
MS_NOEXEC = 8  # Disallow program execution.
MS_SYNCHRONOUS = 16  # Writes are synced at once.
MS_REMOUNT = 32  # Alter flags of a mounted FS.
MS_MANDLOCK = 64  # Allow mandatory locks on an FS.
MS_DIRSYNC = 128  # Directory modifications are synchronous.
MS_NOATIME = 1024  # Do not update access times.
MS_NODIRATIME = 2048  # Do not update directory access times.
MS_BIND = 4096  # Bind directory at different place.
MS_MOVE = 8192  # Atomically move a subtree to a new location
MS_REC = 16384  # Recurse
MS_SILENT = 32768  # Suppress kernel printk warnings
MS_POSIXACL = 1 << 16  # VFS does not apply the umask.
MS_UNBINDABLE = 1 << 17  # Change to unbindable.
MS_PRIVATE = 1 << 18  # Change to private.
MS_SLAVE = 1 << 19  # Change to slave.
MS_SHARED = 1 << 20  # Change to shared.
MS_RELATIME = 1 << 21  # Update atime relative to mtime/ctime.
MS_KERNMOUNT = 1 << 22  # This is a kern_mount call.
MS_I_VERSION = 1 << 23  # Update inode I_version field.
MS_STRICTATIME = 1 << 24  # Always perform atime updates.

_MountEntry = collections.namedtuple(
    '_MountEntry',
    ('mount_id',  # Unique ID of the mount (may be reused after umount
     'parent_id',  # ID of the parent (self for the top of the mount tree)
     'major_minor',  # st_dev value for files on fs, e.g. 0:26
     'root',  # Root of the mount withing the filesystem
     'mount_point',  # mount point relative to the process root
     'mount_opts',  # per mount options
     'opts',  # optional tag:value fields
     'type',  # name of the filesystem, e.g. ext3
     'mount_src',  # fs specific info (or 'none'), e.g. /dev/mapper/foo
     'super_opts',  # super block options, e.g. rw,seclabel,data=ordered
     ))


def _entries():
    """Generates _MountEntries with the information in /proc/self/mountinfo"""
    with open('/proc/self/mountinfo') as mount_file:
        for line in mount_file:
            tokens = line.split()
            yield _MountEntry(*(tokens[:6] + [' '.join(tokens[6:-4])] +
                              tokens[-3:]))


def ismount(path):
    if os.path.islink(path):  # Must be tested first
        return False
    elif os.path.isdir(path):
        return os.path.ismount(path)
    else:  # os.path.ismount does not operate with file mount points
        path = os.path.abspath(path)
        return any(entry for entry in _entries() if entry.mount_point == path)


def isbindmount(path):
    path = os.path.abspath(path)
    return any(entry for entry in _entries() if
               entry.mount_point == path and entry.root != '/')


def mount(source, target, fstype='', flags=0L, data=None):
    """Mount a filesystem source to the target of type fstype"""
    ret = _mount(source, target, fstype, flags, data)
    if ret == -1:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))


def umount(target):
    """Unmount a target filesystem mount"""
    ret = _umount(target)
    if ret == -1:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))


_mount = ctypes.CFUNCTYPE(
    ctypes.c_int,  # ret
    ctypes.c_char_p,  # source
    ctypes.c_char_p,  # target
    ctypes.c_char_p,  # filesystem type
    ctypes.c_ulong,  # mount flags
    ctypes.c_void_p,  # data (fs specific)
    use_errno=True)(('mount', LIBC))


_umount = ctypes.CFUNCTYPE(
    ctypes.c_int,  # ret
    ctypes.c_char_p,  # target
    use_errno=True)(('umount', LIBC))
