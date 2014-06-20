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
