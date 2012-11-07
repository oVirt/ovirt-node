#!/usr/bin/python
#
# cim.py - Copyright (C) 2010 Red Hat, Inc.
# Written by Mike Burns <mburns@redhat.com>
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
from ovirtnode.password import *
from snack import *
import _snack
import grp
import pwd


def enable_cim():
    augtool("set", "/files/etc/default/ovirt/OVIRT_CIM_ENABLED", "1")
    if system("service ovirt-cim restart"):
        return True


def disable_cim():
    augtool("set", "/files/etc/default/ovirt/OVIRT_CIM_ENABLED", "0")
    if system("service ovirt-cim restart &> /dev/null"):
        return True


class Plugin(PluginBase):
    """Plugin for Monitoring configuration option.
    """

    valid_password = False
    valid_password_msg = ""

    def __init__(self, ncs):
        PluginBase.__init__(self, "CIM", ncs)
        self.username = "cim"
        self.shell = "/sbin/nologin"
        self.main_group = "cim"
        self.group_list = ["sfcb"]

    def form(self):
        elements = Grid(2, 9)
        heading = Label("CIM Configuation")
        if is_console():
            heading.setColors(customColorset(1))
        elements.setField(heading, 0, 0, anchorLeft=1)
        pw_elements = Grid(3, 3)
        if is_cim_enabled():
            self.current_cim_status = 1
        else:
            self.current_cim_status = 0
        self.cim_status = Checkbox("Enable CIM", isOn=self.current_cim_status)
        elements.setField(self.cim_status, 0, 1, anchorLeft=1)
        aug.load()
        local_heading = Label("CIM Access")
        if is_console():
            local_heading.setColors(customColorset(1))
        elements.setField(local_heading, 0, 3, anchorLeft=1,
            padding=(0, 2, 0, 0))
        elements.setField(Label(" "), 0, 6)
        pw_elements.setField(Label("Password: "), 0, 1, anchorLeft=1)
        pw_elements.setField(Label("Confirm Password: "), 0, 2, anchorLeft=1)
        self.cim_password_1 = Entry(15, password=1)
        self.cim_password_1.setCallback(self.password_check_callback)
        self.cim_password_2 = Entry(15, password=1)
        self.cim_password_2.setCallback(self.password_check_callback)
        pw_elements.setField(self.cim_password_1, 1, 1)
        pw_elements.setField(self.cim_password_2, 1, 2)
        self.pw_msg = Textbox(60, 6, "", wrap=1)
        elements.setField(pw_elements, 0, 7, anchorLeft=1)
        elements.setField(self.pw_msg, 0, 8, padding=(0, 1, 0, 0))
        return [Label(""), elements]

    def action(self):
        self.ncs.screen.setColor("BUTTON", "black", "red")
        self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
        is_transition_to_disabled = (self.cim_status.value() == 0 and
                self.current_cim_status == 1)
        is_transition_to_enabled = (self.cim_status.value() == 1 and
                self.current_cim_status == 0)
        is_enabled = self.cim_status.value() == 1

        setting_password_failed = False
        if (len(self.cim_password_1.value()) > 0  or
            len(self.cim_password_2.value()) > 0):
            if is_enabled:
                setting_password_failed = self.__set_cim_password()
                if setting_password_failed:
                    ButtonChoiceWindow(self.ncs.screen, "CIM Configuration",
                        "Unable to Set CIM Password", buttons=['Ok'])
                    self.ncs.reset_screen_colors()
                    return False
            else:
                ButtonChoiceWindow(self.ncs.screen, "CIM Configuration",
                    "CIM Must Be Enabled to Set Password", buttons=['Ok'])
                self.ncs.reset_screen_colors()
                return False

        if is_transition_to_disabled:
            if disable_cim():
                ButtonChoiceWindow(self.ncs.screen, "CIM Configuration",
                    "CIM Successfully Disabled", buttons=['Ok'])
                self.ncs.reset_screen_colors()
                return True
        elif is_transition_to_enabled or is_enabled:
            if len(self.cim_password_1.value()) > 0:
                if enable_cim():
                    ButtonChoiceWindow(self.ncs.screen, "CIM Configuration",
                        "CIM Successfully Enabled", buttons=['Ok'])
                    self.ncs.reset_screen_colors()
                else:
                    ButtonChoiceWindow(self.ncs.screen, "CIM Configuration",
                        "CIM Configuration Failed", buttons=['Ok'])
                    self.ncs.reset_screen_colors()
            else:
                ButtonChoiceWindow(self.ncs.screen, "CIM Configuration",
                    "Please Enter a Password", buttons=['Ok'])
                self.ncs.reset_screen_colors()

    def __set_cim_password(self):
        msg = None
        failed = True
        self.create_cim_user()
        if self.valid_password:
            if set_password(self.cim_password_1.value(), "cim"):
                msg = "CIM Password Successfully Set"
                failed = False
            else:
                msg = "CIM Password Failed"
        else:
            self.ncs._create_warn_screen()
            msg = "CIM Password Is Invalid: %s" % self.valid_password_msg
        ButtonChoiceWindow(self.ncs.screen, "CIM Access", msg,
            buttons=['Ok'])
        self.ncs.reset_screen_colors()
        return failed

    def password_check_callback(self):
        resp, msg = password_check(self.cim_password_1.value(),
            self.cim_password_2.value())
        self.pw_msg.setText(msg)

        self.valid_password = resp == 0
        self.valid_password_msg = msg

        return

    def create_cim_user(self):
        if not check_user_exists(self.username):
            add_user(self.username, self.shell, self.main_group, self.group_list)
        else:
            userinfo = pwd.getpwnam(self.username)
            if not userinfo.pw_gid == grp.getgrnam(self.main_group).gr_gid:
                system_closefds("usermod -g %s %s" % (self.main_group,
                                                      self.username))
            if not userinfo.pw_shell == self.shell:
                system_closefds("usermod -s %s %s" % (self.shell,
                                                      self.username))
            for group in self.group_list:
                if self.username not in grp.getgrnam(group).gr_mem:
                    system_closefds("usermod -G %s %s" % (self.group_list.join(",",
                                                          self.username)))
                    break


def get_plugin(ncs):
    return Plugin(ncs)
