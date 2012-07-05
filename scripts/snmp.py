#!/usr/bin/python
# snmp.py - Copyright (C) 2012 Red Hat, Inc.
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

from ovirtnode.ovirtfunctions import *
import os

snmp_conf = "/etc/snmp/snmpd.conf"


def enable_snmpd(password):
    system("service snmpd stop")
    # get old password #
    if os.path.exists("/tmp/snmpd.conf"):
        conf = "/tmp/snmpd.conf"
    else:
        conf = snmp_conf
    cmd = "cat %s|grep createUser|awk '{print $4}'" % conf
    oldpwd = subprocess_closefds(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    oldpwd = oldpwd.stdout.read().strip()
    system("sed -c -ie '/^createUser root/d' %s" % snmp_conf)
    f = open(snmp_conf, "a")
    # create user account
    f.write("createUser root SHA %s AES\n" % password)
    f.close()
    system("service snmpd start")
    # change existing password
    if len(oldpwd) > 0:
        pwd_change_cmd = ("snmpusm -v 3 -u root -n \"\" -l authNoPriv -a " +
        "SHA -A %s localhost passwd %s %s -x AES") % (oldpwd, oldpwd, password)
        if system(pwd_change_cmd):
            system("rm -rf /tmp/snmpd.conf")
    ovirt_store_config(snmp_conf)


def disable_snmpd():
    system("service snmpd stop")
    # copy to /tmp for enable/disable toggles w/o reboot
    system("cp /etc/snmp/snmpd.conf /tmp")
    system("sed -c -ie '/^createUser root/d' %s" % snmp_conf)
    remove_config(snmp_conf)


def snmp_auto():
    if "OVIRT_SNMP_PASSWORD" in OVIRT_VARS:
        enable_snmpd(OVIRT_VARS["OVIRT_SNMP_PASSWORD"])
