#!/usr/bin/env python
#
# ovirt-auto-install.py - Copyright (C) 2011 Red Hat, Inc.
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

import os
import sys
from ovirtnode.ovirtfunctions import *
from ovirtnode.storage import *
from ovirtnode.install import *
from ovirtnode.network import *
from ovirtnode.log import *
from ovirtnode.kdump import *
from ovirtnode.snmp import *
from ovirt_config_setup.collectd import *

print "Performing automatic disk partitioning"
if storage_auto():
    print "Completed automatic disk partitioning"
    # store /etc/shadow if adminpw/rootpw are set, handled already in ovirt-early
    file = open("/proc/cmdline")
    args = file.read()
    if "adminpw" in args or "rootpw" in args:
        print "Storing /etc/shadow"
        ovirt_store_config("/etc/passwd")
        ovirt_store_config("/etc/shadow")
    file.close()
    # network configuration
    print "Configuring Network"
    if OVIRT_VARS["OVIRT_BOOTIF"] != "":
        network_auto()

    if OVIRT_VARS.has_key("OVIRT_HOSTNAME"):
        system("hostname %s" % OVIRT_VARS["OVIRT_HOSTNAME"])
    #set ssh_passwd_auth
    if OVIRT_VARS.has_key("OVIRT_SSH_PWAUTH"):
        if self.ssh_passwd_status.value() == 1:
            augtool("set","/files/etc/ssh/sshd_config/PasswordAuthentication", "yes")
        elif self.ssh_passwd_status.value() == 0:
            augtool("set","/files/etc/ssh/sshd_config/PasswordAuthentication", "no")

    # iscsi handled in install.py
    print "Configuring Logging"
    logging_auto()
    print "Configuring Collectd"
    collectd_auto()
    install = Install()
    print "Configuring KDump"
    kdump_auto()
    print "Configuring SNMP"
    snmp_auto()
    print "Installing Bootloader"
    if install.ovirt_boot_setup():
        print "Bootloader Installation Completed"
    else:
        print "Bootloader Installation Failed"
        sys.exit(1)
    print "Installation and Configuration Completed"
else:
    print "Automatic installation failed. Please review /tmp/ovirt.log"
    sys.exit(1)
