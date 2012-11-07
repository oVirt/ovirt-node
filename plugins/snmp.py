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

import ovirtnode.ovirtfunctions as _functions
from ovirtnode.ovirtfunctions import PluginBase
import os
from subprocess import Popen, PIPE, STDOUT
from snack import *
import subprocess

snmp_conf = "/etc/snmp/snmpd.conf"


def enable_snmpd(password):
    _functions.system("service snmpd stop")
    # get old password #
    if os.path.exists("/tmp/snmpd.conf"):
        conf = "/tmp/snmpd.conf"
    else:
        conf = snmp_conf
    cmd = "cat %s|grep createUser|awk '{print $4}'" % conf
    oldpwd = _functions.subprocess_closefds(cmd, shell=True,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
    oldpwd = oldpwd.stdout.read().strip()
    _functions.system("sed -c -ie '/^createUser root/d' %s" % snmp_conf)
    f = open(snmp_conf, "a")
    # create user account
    f.write("createUser root SHA %s AES\n" % password)
    f.close()
    _functions.system("service snmpd start")
    # change existing password
    if len(oldpwd) > 0:
        pwd_change_cmd = ("snmpusm -v 3 -u root -n \"\" -l authNoPriv -a " +
        "SHA -A %s localhost passwd %s %s -x AES") % (oldpwd, oldpwd, password)
        if _functions.system(pwd_change_cmd):
            _functions.system("rm -rf /tmp/snmpd.conf")
    _functions.ovirt_store_config(snmp_conf)


def disable_snmpd():
    _functions.system("service snmpd stop")
    # copy to /tmp for enable/disable toggles w/o reboot
    _functions.system("cp /etc/snmp/snmpd.conf /tmp")
    _functions.system("sed -c -ie '/^createUser root/d' %s" % snmp_conf)
    _functions.remove_config(snmp_conf)


class Plugin(PluginBase):
    """Plugin for SNMP Configuration
    """

    def __init__(self, ncs):
        PluginBase.__init__(self, "SNMP", ncs)

    def password_check_callback(self):
        resp, msg = _functions.password_check(self.root_password_1.value(),
                                              self.root_password_2.value())
        if (len(self.root_password_1.value()) < 8) and \
           (len(self.root_password_2.value()) < 8):
            self.root_password_1.set("")
            self.root_password_2.set("")
            msg = "Password must be at least 8 characters\n\n\n\n\n"
        elif (" " in self.root_password_1.value()) or \
             (" " in self.root_password_2.value()):
            self.root_password_1.set("")
            self.root_password_2.set("")
            msg = "Password may not contain spaces\n\n\n\n\n"
        self.pw_msg.setText(msg)
        return

    def form(self):
        elements = Grid(2, 9)
        heading = Label("SNMP")
        if _functions.is_console():
            heading.setColors(customColorset(1))
        elements.setField(heading, 0, 0, anchorLeft=1)
        pw_elements = Grid(3, 3)
        self.current_snmp_status = 0
        if os.path.exists("/etc/snmp/snmpd.conf"):
            f = open("/etc/snmp/snmpd.conf")
            for line in f:
                if "createUser" in line:
                    self.current_snmp_status = 1
            f.close()
        self.snmp_status = Checkbox("Enable SNMP",
                                    isOn=self.current_snmp_status)
        elements.setField(self.snmp_status, 0, 1, anchorLeft=1)

        local_heading = Label("SNMP Password")
        if _functions.is_console():
            local_heading.setColors(customColorset(1))
        elements.setField(local_heading, 0, 3, anchorLeft=1,
                          padding=(0, 2, 0, 0))
        elements.setField(Label(" "), 0, 6)
        pw_elements.setField(Label("Password: "), 0, 1, anchorLeft=1)
        pw_elements.setField(Label("Confirm Password: "), 0, 2, anchorLeft=1)
        self.root_password_1 = Entry(15, password=1)
        self.root_password_1.setCallback(self.password_check_callback)
        self.root_password_2 = Entry(15, password=1)
        self.root_password_2.setCallback(self.password_check_callback)
        pw_elements.setField(self.root_password_1, 1, 1)
        pw_elements.setField(self.root_password_2, 1, 2)
        self.pw_msg = Textbox(60, 6, "", wrap=1)
        elements.setField(pw_elements, 0, 7, anchorLeft=1)
        elements.setField(self.pw_msg, 0, 8, padding=(0, 1, 0, 0))
        return [Label(""), elements]

    def action(self):
        if self.snmp_status.value() == 1:
            if len(self.root_password_1.value()) > 0:
                if (self.root_password_1.value() != "" or
                    self.root_password_2.value() != ""):
                    if (self.root_password_1.value() !=
                        self.root_password_2.value()):
                        self.ncs._create_warn_screen()
                        ButtonChoiceWindow(self.ncs.screen, "SNMP", "SNMP was " +
                                           "not enabled because passwords " +
                                           "do not match", buttons=['Ok'])
                        return
                enable_snmpd(self.root_password_1.value())
            else:
                self.ncs._create_warn_screen()
                ButtonChoiceWindow(self.ncs.screen, "SNMP Error",
                              "Unable to configure SNMP without a password!",
                              buttons=['Ok'])
                self.ncs.reset_screen_colors()
        elif self.snmp_status.value() == 0:
            if len(self.root_password_1.value()) > 0:
                ButtonChoiceWindow(self.screen, "SNMP Error",
                      "SNMP must be enabled to set a password!",
                      buttons=['Ok'])
            else:
                disable_snmpd()

            disable_snmpd()

def snmp_auto():
    if "OVIRT_SNMP_PASSWORD" in _functions.OVIRT_VARS:
        enable_snmpd(_functions.OVIRT_VARS["OVIRT_SNMP_PASSWORD"])


def get_plugin(ncs):
    return Plugin(ncs)
