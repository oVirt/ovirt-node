#!/usr/bin/env python
#
# kdump.py - Copyright (C) 2010 Red Hat, Inc.
# Written by Joey Boggs <jboggs@redhat.com>
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

import ovirtnode.ovirtfunctions as _functions


def write_kdump_config(config):
    kdump_config_file = open("/etc/kdump.conf", "w")
    kdump_config_file.write("default reboot\n")
    # adds a 60 sec delay to make sure the nic is up
    kdump_config_file.write("net " + config + "\n")
    kdump_config_file.close()
    _functions.ovirt_store_config("/etc/kdump.conf")
    return True


def restore_kdump_config():
    kdump_config_file = open("/etc/kdump.conf", "w")
    kdump_config_file.write("default reboot\n")
    kdump_config_file.write("ext4 /dev/HostVG/Data\n")
    kdump_config_file.write("path /core\n")
    kdump_config_file.close()
    return True


def kdump_auto():
    try:
        if "OVIRT_KDUMP_NFS" in _functions.OVIRT_VARS:
            write_kdump_config(_functions.OVIRT_VARS["OVIRT_KDUMP_NFS"])
            _functions.ovirt_store_config("/etc/kdump.conf")
            _functions.logger.info("Syslog Configuration Completed")
            return True
    except:
        _functions.logger.error("KDump Configuration Failed")
