#!/usr/bin/env python
#
# ovirt-config-setup.py - Copyright (C) 2010 Red Hat, Inc.
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

from snack import *
import _snack
import os
import traceback
import fcntl
import libvirt
import PAM
import gudev
import pkgutil
import ovirt_config_setup
import sys
from ovirtnode.ovirtfunctions import *
from ovirtnode.password import *
from ovirtnode.log import *
from ovirtnode.network import *
from ovirtnode.kdump import *
from ovirtnode.iscsi import *
from ovirtnode.snmp import *

OK_BUTTON = "OK"
BACK_BUTTON = "Back"
RESET_BUTTON = "Reset"
CANCEL_BUTTON = "Cancel"
APPLY_BUTTON = "Apply"
IDENTIFY_BUTTON = "Identify NIC"
LOCK_BUTTON = "Lock"
RESTART_BUTTON = "Restart"
POWER_OFF_BUTTON = "Power Off"
UNLOCK_BUTTON = "Unlock"
MENU_BUTTON = "Back to Menu"
LOG_OFF_BUTTON = "Log Off"
login_password = ""

STATUS_PAGE = 1
NETWORK_PAGE = 2
AUTHENTICATION_PAGE = 3
KEYBOARD_PAGE = 4
SNMP_PAGE = 5
LOGGING_PAGE = 6
KDUMP_PAGE = 7
LAST_OPTION = REMOTE_STORAGE_PAGE = 8
# max. 3 plugin menu options/pages: 13,15,17
FIRST_PLUGIN_PAGE = 9
LAST_PLUGIN_PAGE = 13
#
NETWORK_DETAILS_PAGE = 19
SUPPORT_PAGE = 21
LOCKED_PAGE = 99

OVIRT_VARS = parse_defaults()

def pam_conv(auth, query_list):
    global login_password
    resp = []
    for i in range(len(query_list)):
        resp.append((login_password, 0))
    return resp

class NodeConfigScreen():
      """
      User interface for Hypervisor Node Configuration.
      """

      def __init__(self):
        _console_colorset = {
                        "ROOT"           : ("gray",  "magenta"),
                        "BORDER"         : ("magenta", "magenta"),
                        "WINDOW"         : ("magenta", "magenta"),
                         "ACTBUTTON"     : ("blue",  "white"),
                         "BUTTON"        : ("blue",  "white"),
                         "COMPACTBUTTON" : ("black", "magenta"),
                         "LISTBOX"       : ("green",  "red"),
                         "ACTLISTBOX"    : ("cyan", "red"),
                         "ACTSELLISTBOX" : ("blue",  "white"),
                         "TEXTBOX"       : ("cyan",  "magenta"),
                         "ENTRY"         : ("cyan", "magenta"),
                         "DISENTRY"      : ("white", "cyan"),
                         "SHADOW"        : ("magenta",  "magenta"),
                         "LABEL"         : ("brown",  "magenta"),
                         "TITLE"         : ("white",  "blue"),
                         "HELPLINE"      : ("cyan",  "magenta"),
                         "EMPTYSCALE"    : ("white",  "cyan"),
                         "FULLSCALE"     : ("cyan",  "white"),
                         "CHECKBOX"      : ("black",  "red"),
                         "ACTCHECKBOX"   : ("blue", "white")
                         }
        _alternate_colorset = {
                        "ROOT"          : ("white",  "white"),
                        "HELPLINE"      : ("white",  "white"),
                        "SHADOW"        : ("white",  "white"),
                        "BORDER"        : ("white", "white"),
                        "ACTBUTTON"     : ("white",  "blue"),
                        "BUTTON"        : ("blue",  "white"),
                        "TITLE"         : ("white",  "blue"),
                        "EMPTYSCALE"    : ("white",  "cyan"),
                        "FULLSCALE"     : ("black",  "white"),
                        "CHECKBOX"      : ("blue",  "white"),
                        "ROOTTEXT"      : ("white",  "blue"),
                        "ACTSELLISTBOX" : ("white",  "black"),
                        "LABEL"         : ("black",  "white"),
                         }

        if is_console():
            self.__colorset = _console_colorset
        else:
            self.__colorset = _alternate_colorset
        self.__current_page = 1
        self.__finished = False
        self.__nic_config_failed = 0
        self.net_apply_config = 0

      def _set_title(self):
          PRODUCT_TITLE = "%s %s-%s" % (PRODUCT_SHORT, PRODUCT_VERSION, PRODUCT_RELEASE)
          self.screen.drawRootText(1,0, "".ljust(78))
          self.screen.drawRootText(1,1, "  %s" % PRODUCT_TITLE.ljust(76))
          self.screen.drawRootText(1,2, "  %s" % os.uname()[1].ljust(76))

      def _create_blank_screen(self):
          self.screen = SnackScreen()
          self.reset_screen_colors()
          self.gridform = GridForm(self.screen, "", 2, 2)
          self.screen.pushHelpLine(" ")
          self._set_title()

      def _create_warn_screen(self):
          self._create_blank_screen()
          if is_console():
              self.screen.setColor("BUTTON", "black", "red")
              self.screen.setColor("ACTBUTTON", "blue", "white")

      def set_console_colors(self):
          self.existing_color_array = None
          tty_file = None
          try:
            tty_file = open("/dev/tty", "rw")
          except:
            pass
          if tty_file == None:
            tty_file = open("/dev/console", "rw")
          try:
            self._set_colors(tty_file)
          except:
              pass
          finally:
              tty_file.close()

      def _set_colors(self, tty_file):
          GIO_CMAP = 0x4B70
          PIO_CMAP = 0x4B71
          self.existing_color_array = bytearray(fcntl.ioctl(tty_file.fileno(), GIO_CMAP, b"\x00" * 48))
          color_array = self.existing_color_array
          color_array[3] = 0xde
          color_array[4] = 0xde
          color_array[5] = 0xde
          color_array[6] = 0x30
          color_array[7] = 0x30
          color_array[8] = 0x30
          color_array[9] = 0x52
          color_array[10] = 0x52
          color_array[11] = 0x52
          color_array[12] = 0x00
          color_array[13] = 0xbb
          color_array[14] = 0xff
          color_array[15] = 0xea
          color_array[16] = 0xea
          color_array[17] = 0xea
          color_array[18] = 0x71
          color_array[19] = 0x71
          color_array[20] = 0x71
          color_array[21] = 0xff
          color_array[22] = 0xff
          color_array[23] = 0xff
          fcntl.ioctl(tty_file.fileno(), PIO_CMAP, bytes(color_array))

      def restore_console_colors(self):
          if is_console():
              if self.existing_color_array == None:
                return
              tty_file = None
              try:
                tty_file = open("/dev/tty", "rw")
              except:
                pass
              if tty_file == None:
                tty_file = open("/dev/console", "rw")
              try:
                  self._restore_colors(tty_file)
              except:
                  pass
              finally:
                  tty_file.close()

      def _restore_colors(self, tty_file):
          GIO_CMAP = 0x4B70
          PIO_CMAP = 0x4B71
          fcntl.ioctl(tty_file.fileno(), PIO_CMAP, bytes(self.existing_color_array))

      def reset_screen_colors(self):
          for item in self.__colorset.keys():
              colors = self.__colorset.get(item)
              self.screen.setColor(item, colors[0], colors[1])

      def get_elements_for_page(self, screen, page):
            if page == STATUS_PAGE :
                return self.status_page(screen)
            if page == NETWORK_PAGE :
                return self.network_configuration_page(screen)
            if page == AUTHENTICATION_PAGE :
                return self.authentication_configuration_page(screen)
            if page == KEYBOARD_PAGE:
                return self.keyboard_configuration_page(screen)
            if page == SNMP_PAGE:
                return self.snmp_configuration_page(screen)
            if page == LOGGING_PAGE :
                return self.logging_configuration_page(screen)
            if page == KDUMP_PAGE :
                return self.kdump_configuration_page(screen)
            if page == REMOTE_STORAGE_PAGE :
                return self.remote_storage_configuration_page(screen)
            if page == NETWORK_DETAILS_PAGE :
                return self.network_details_page(screen)
            if page == SUPPORT_PAGE :
                return self.support_page(screen)
            if page == LOCKED_PAGE :
                return self.screen_locked_page(screen)
            # plugin pages
            plugin_page=FIRST_PLUGIN_PAGE
            for p in self.plugins :
                if page == plugin_page:
                    return p.form()
                plugin_page+=1
                if plugin_page > LAST_PLUGIN_PAGE :
                    # should not happen
                    return None

      def network_proto_Callback(self):
          return

      def nic_lb_callback(self):
         try:
             get_ip_address(self.nic_lb.current())
             self.nic_disabled.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)
         except:
             self.nic_disabled.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
         return

      def nic_dhcp_callback(self):
          if self.nic_dhcp.value() == 1:
              flag = _snack.FLAGS_SET
          else:
              flag = _snack.FLAGS_RESET
          for i in self.netdevip, self.netdevmask, self.netdevgateway:
              i.setFlags(_snack.FLAG_DISABLED, flag)
          return

      def dns_host1_callback(self):
          warn = 0
          if not self.dns_host1.value() is None and not self.dns_host1.value() == "":
               if not is_valid_ipv4(self.dns_host1.value()):
                   if not is_valid_ipv6(self.dns_host1.value()):
                       warn = 1
          if warn == 1:
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Network", "Invalid IP Address", buttons = ['Ok'])
              self.dns_host1.set("")
              self.reset_screen_colors()
          return

      def dns_host2_callback(self):
          warn = 0
          if not self.dns_host2.value() is None and not self.dns_host2.value() == "":
              if not is_valid_ipv4(self.dns_host2.value()):
                   if not is_valid_ipv6(self.dns_host1.value()):
                       warn = 1
          if warn == 1:
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Network", "Invalid IP Address", buttons = ['Ok'])
              self.dns_host2.set("")
              self.reset_screen_colors()
          return

      def ntp_host1_callback(self):
          warn = 0
          if not self.ntp_host1.value() is None and not self.ntp_host1.value() == "":
               if not is_valid_ipv4(self.ntp_host1.value()):
                   if not is_valid_ipv6(self.ntp_host1.value()):
                       if not is_valid_hostname(self.ntp_host1.value()):
                           warn = 1
          if warn == 1:
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Network", "Invalid IP Address", buttons = ['Ok'])
              self.ntp_host1.set("")
              self.reset_screen_colors()
          return

      def ntp_host2_callback(self):
          warn = 0
          if not self.ntp_host2.value() is None and not self.ntp_host2.value() == "":
              if not is_valid_ipv4(self.ntp_host2.value()):
                   if not is_valid_ipv6(self.ntp_host2.value()):
                       if not is_valid_hostname(self.ntp_host2.value()):
                           warn = 1
          if warn == 1:
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Network", "Invalid IP Address", buttons = ['Ok'])
              self.ntp_host2.set("")
              self.reset_screen_colors()
          return

      def ipv4_ip_callback(self):
          warn = 0
          if not self.ipv4_netdevip.value() is None and not self.ipv4_netdevip.value() == "":
               if not is_valid_ipv4(self.ipv4_netdevip.value()):
                   warn = 1
          if warn == 1:
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Network", "Invalid IP Address", buttons = ['Ok'])
              self.ipv4_netdevip.set("")
              self.reset_screen_colors()
          return

      def ipv4_netmask_callback(self):
          warn = 0
          if not self.ipv4_netdevmask.value() is None and not self.ipv4_netdevmask.value() == "":
               if not is_valid_ipv4(self.ipv4_netdevmask.value()):
                   warn = 1
          if warn == 1:
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Network", "Invalid IP Address", buttons = ['Ok'])
              self.ipv4_netdevmask.set("")
              self.reset_screen_colors()
          return

      def ipv4_gateway_callback(self):
          warn = 0
          if not self.ipv4_netdevgateway.value() is None and not self.ipv4_netdevgateway.value() == "":
               if not is_valid_ipv4(self.ipv4_netdevgateway.value()):
                   warn = 1
          if warn == 1:
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Network", "Invalid IP Address", buttons = ['Ok'])
              self.ipv4_netdevgateway.set("")
              self.reset_screen_colors()
          return

      def ipv4_disabled_callback(self):
          if self.disabled_ipv4_nic_proto.value() == 1:
              flag = _snack.FLAGS_SET
              for i in self.ipv4_netdevip, self.ipv4_netdevmask, self.ipv4_netdevgateway:
                  i.setFlags(_snack.FLAG_DISABLED, flag)
                  self.dhcp_ipv4_nic_proto.setValue(" 0")
                  self.static_ipv4_nic_proto.setValue(" 0")

      def ipv4_dhcp_callback(self):
          if self.dhcp_ipv4_nic_proto.value() == 1:
              flag = _snack.FLAGS_SET
              for i in self.ipv4_netdevip, self.ipv4_netdevmask, self.ipv4_netdevgateway:
                  i.setFlags(_snack.FLAG_DISABLED, flag)
                  self.disabled_ipv4_nic_proto.setValue(" 0")
                  self.static_ipv4_nic_proto.setValue(" 0")

      def ipv4_static_callback(self):
          if self.static_ipv4_nic_proto.value() == 1:
              flag = _snack.FLAGS_RESET
              for i in self.ipv4_netdevip, self.ipv4_netdevmask, self.ipv4_netdevgateway:
                  i.setFlags(_snack.FLAG_DISABLED, flag)
                  self.disabled_ipv4_nic_proto.setValue(" 0")
                  self.dhcp_ipv4_nic_proto.setValue(" 0")

      def ipv6_disabled_callback(self):
          if self.disabled_ipv6_nic_proto.value() == 1:
              flag = _snack.FLAGS_SET
              for i in self.ipv6_netdevip, self.ipv6_netdevmask, self.ipv6_netdevgateway:
                  i.setFlags(_snack.FLAG_DISABLED, flag)
                  self.dhcp_ipv6_nic_proto.setValue(" 0")
                  self.static_ipv6_nic_proto.setValue(" 0")
                  self.auto_ipv6_nic_proto.setValue(" 0")

      def ipv6_dhcp_callback(self):
          if self.dhcp_ipv6_nic_proto.value() == 1:
              flag = _snack.FLAGS_SET
              for i in self.ipv6_netdevip, self.ipv6_netdevmask, self.ipv6_netdevgateway:
                  i.setFlags(_snack.FLAG_DISABLED, flag)
                  self.disabled_ipv6_nic_proto.setValue(" 0")
                  self.static_ipv6_nic_proto.setValue(" 0")
                  self.auto_ipv6_nic_proto.setValue(" 0")

      def ipv6_static_callback(self):
          if self.static_ipv6_nic_proto.value() == 1:
              flag = _snack.FLAGS_RESET
              for i in self.ipv6_netdevip, self.ipv6_netdevmask, self.ipv6_netdevgateway:
                  i.setFlags(_snack.FLAG_DISABLED, flag)
                  self.disabled_ipv6_nic_proto.setValue(" 0")
                  self.dhcp_ipv6_nic_proto.setValue(" 0")
                  self.auto_ipv6_nic_proto.setValue(" 0")

      def ipv6_auto_callback(self):
          if self.auto_ipv6_nic_proto.value() == 1:
              flag = _snack.FLAGS_SET
              for i in self.ipv6_netdevip, self.ipv6_netdevmask, self.ipv6_netdevgateway:
                  i.setFlags(_snack.FLAG_DISABLED, flag)
                  self.disabled_ipv6_nic_proto.setValue(" 0")
                  self.dhcp_ipv6_nic_proto.setValue(" 0")
                  self.static_ipv6_nic_proto.setValue(" 0")
      def ipv6_ip_callback(self):
          warn = 0
          if not self.ipv6_netdevip.value() is None and not self.ipv6_netdevip.value() == "":
               if not is_valid_ipv6(self.ipv6_netdevip.value()):
                   warn = 1
          if warn == 1:
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Network", "Invalid IP Address", buttons = ['Ok'])
              self.ipv6_netdevip.set("")
              self.reset_screen_colors()
          return

      def ipv6_netmask_callback(self):
          warn = 0
          if not self.ipv6_netdevmask.value() is None and not self.ipv6_netdevmask.value() == "":
              try:
                  if not int(self.ipv6_netdevmask.value()) in range(1,128):
                      warn = 1
              except:
                  warn = 1
          if warn == 1:
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Network", "Invalid IPv6 Netmask", buttons = ['Ok'])
              self.ipv6_netdevmask.set("")
              self.reset_screen_colors()
          return

      def ipv6_gateway_callback(self):
          warn = 0
          if not self.ipv6_netdevgateway.value() is None and not self.ipv6_netdevgateway.value() == "":
               if not is_valid_ipv6(self.ipv6_netdevgateway.value()):
                   warn = 1
          if warn == 1:
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Network", "Invalid IP Address", buttons = ['Ok'])
              self.ipv6_netdevgateway.set("")
              self.reset_screen_colors()
          return

      def netvlanid_callback(self):
          warn = 0
          try:
              if not self.netvlanid.value() == "":
                  if not int(self.netvlanid.value()) in range(1,4095) or " " in self.netvlanid.value():
                      warn = 1
          except:
              warn = 1
          finally:
              if warn == 1:
                  self._create_warn_screen()
                  ButtonChoiceWindow(self.screen, "Configuration Check", "Invalid VLAN ID", buttons = ['Ok'])
                  self.reset_screen_colors()
                  self.netvlanid.set("")
      def password_check_callback(self):
          resp, msg = password_check(self.root_password_1.value(), self.root_password_2.value())
          self.pw_msg.setText(msg)
          return

      def valid_logrotate_max_size_callback(self):
          if not self.logrotate_max_size.value().isdigit():
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Configuration Check", "Invalid Log File Size", buttons = ['Ok'])
              self.reset_screen_colors()

      def valid_syslog_port_callback(self):
          if not is_valid_port(self.syslog_port.value()):
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Configuration Check", "Invalid Port Number", buttons = ['Ok'])
              self.reset_screen_colors()

      def valid_syslog_server_callback(self):
          if not is_valid_host_or_ip(self.syslog_server.value()):
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Configuration Check", "Invalid Hostname or Address", buttons = ['Ok'])
              self.reset_screen_colors()

      def kdump_nfs_callback(self):
          self.kdump_ssh_type.setValue(" 0")
          self.kdump_restore_type.setValue(" 0")
          self.kdump_nfs_config.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)
          self.kdump_ssh_config.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)

      def kdump_valid_nfs_callback(self):
          if not is_valid_nfs(self.kdump_nfs_config.value()):
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Configuration Check", "Invalid NFS Entry", buttons = ['Ok'])
              self.reset_screen_colors()

      def kdump_ssh_callback(self):
          self.kdump_nfs_type.setValue(" 0")
          self.kdump_restore_type.setValue(" 0")
          self.kdump_nfs_config.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
          self.kdump_ssh_config.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_RESET)

      def kdump_valid_ssh_callback(self):
          if not is_valid_user_host(self.kdump_ssh_config.value()):
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Configuration Check", "Invalid SSH Entry", buttons = ['Ok'])
              self.reset_screen_colors()

      def kdump_restore_callback(self):
          self.kdump_ssh_type.setValue(" 0")
          self.kdump_nfs_type.setValue(" 0")
          self.kdump_nfs_config.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
          self.kdump_ssh_config.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)

      def valid_netconsole_server_callback(self):
          if not is_valid_host_or_ip(self.netconsole_server.value()):
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Configuration Check", "Invalid NetConsole Hostname or Address", buttons = ['Ok'])
              self.reset_screen_colors()

      def valid_netconsole_server_port_callback(self):
          if not is_valid_port(self.netconsole_server_port.value()):
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Configuration Check", "Invalid NetConsole Server Port", buttons = ['Ok'])
              self.reset_screen_colors()

      def valid_hostname_callback(self):
          if not self.net_hostname.value() == "":
              if not is_valid_hostname(self.net_hostname.value()):
                  self._create_warn_screen()
                  ButtonChoiceWindow(self.screen, "Configuration Check", "Invalid Hostname", buttons = ['Ok'])
                  self.reset_screen_colors()

      def valid_iqn_callback(self):
          if not self.iscsi_initiator_config.value() =="":
              if not is_valid_iqn(self.iscsi_initiator_config.value()):
                  self._create_warn_screen()
                  ButtonChoiceWindow(self.screen, "Configuration Check", "Invalid IQN Format", buttons = ['Ok'])
                  self.reset_screen_colors()



      def valid_fqdn_or_ipv4(self):
          warn = 0
          if not self.ntp_host1.value() == "":
               if not is_valid_ipv4(self.ntp_host1.value()):
                   if not is_valid_hostname(self.ntp_host1.value()):
                       if not is_valid_ipv6(self.ntp_host1.value()):
                           warn = 1
          if not self.ntp_host2.value() == "":
               if not is_valid_ipv4(self.ntp_host2.value()):
                   if not is_valid_hostname(self.ntp_host2.value()):
                       if not is_valid_ipv6(self.ntp_host2.value()):
                           warn = 1

          if not self.dns_host1.value() == "":
               if not is_valid_ipv4(self.dns_host1.value()):
                   if not is_valid_ipv6(self.dns_host1.value()):
                           warn = 1
          if not self.dns_host2.value() == "":
               if not is_valid_ipv4(self.dns_host2.value()):
                   if not is_valid_ipv6(self.dns_host2.value()):
                           warn = 1
          if warn == 1:
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "Network", "Invalid IP/Hostname", buttons = ['Ok'])
              self.reset_screen_colors()
          return

      def screen_locked_page(self, screen):
            self.screen_locked = True
            elements = Grid(1, 3)
            pw_elements = Grid(2, 2)
            pad = 34 - len(os.uname()[1]) / 2
            elements.setField(Label("Unlock " + os.uname()[1]), 0, 0, padding=(pad - 3,1,0,1))
            self.login_username = os.getlogin()
            self.login_password = Entry(15, "", password = 1)
            pw_elements.setField(Label("Username: "), 0, 0, padding=(pad,1,0,1))
            pw_elements.setField(Label(self.login_username), 1, 0)
            pw_elements.setField(Label("Password: "), 0, 1, padding=(pad,0,0,1))
            pw_elements.setField(self.login_password, 1, 1)
            elements.setField(pw_elements, 0, 1)
            return [Label(""), elements]

      def status_page(self, screen):
            elements = Grid(2, 10)
            main_grid = Grid(2, 10)
            if network_up():
                self.network_status = {}
                status_text = ""
                client = gudev.Client(['net'])
                # reload augeas tree
                aug.load()
                for nic in client.query_by_subsystem("net"):
                    try:
                        interface = nic.get_property("INTERFACE")
                        logger.debug(interface)
                        if not interface == "lo":
                            if has_ip_address(interface) or get_ipv6_address(interface):
                                ipv4_address = get_ip_address(interface)
                                try:
                                    ipv6_address, netmask = get_ipv6_address(interface)
                                except:
                                    ipv6_address = ""
                                self.network_status[interface] = (ipv4_address,ipv6_address)
                    except:
                        pass
                # remove parent/bridge duplicates
                for key in sorted(self.network_status.iterkeys()):
                    if key.startswith("br"):
                        parent_dev = key[+2:]
                        if self.network_status.has_key(parent_dev):
                            del self.network_status[parent_dev]
                for key in sorted(self.network_status.iterkeys()):
                    ipv4_addr, ipv6_addr = self.network_status[key]
                    cmd = "/files/etc/sysconfig/network-scripts/ifcfg-%s/BOOTPROTO" % str(key)
                    dev_bootproto = augtool_get(cmd)
                    if dev_bootproto is None:
                      cmd = "/files/etc/sysconfig/network-scripts/ifcfg-br%s/BOOTPROTO" % str(key)
                      dev_bootproto = augtool_get(cmd)
                      if dev_bootproto is None:
                          dev_bootproto = "Disabled"
                    link_status_cmd = "ethtool %s|grep \"Link detected\"" % key
                    link_status = subprocess.Popen(link_status_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
                    link_status = link_status.stdout.read()
                    if not "yes" in link_status:
                        ipv4_addr = "(Link Inactive)"
                    if ipv4_addr.strip() == "" and dev_bootproto.strip() == "dhcp":
                        if "Inactive" in ipv4_addr:
                            ipv4_addr = "(Link Inactive)"
                        else:
                            ipv4_addr = "(DHCP Failed)"
                    if OVIRT_VARS.has_key("OVIRT_IPV6") and ipv6_addr != "" :
                            status_text += "%1s: %5s %14s \nIPv6: %1s\n\n" % (key.strip(),dev_bootproto.strip(),ipv4_addr.strip(),ipv6_addr.strip())
                    else:
                        status_text += "%1s: %5s %14s \n" % (key.strip(),dev_bootproto.strip(),ipv4_addr.strip())
                    status_text.strip()
                    networking = TextboxReflowed(32, status_text, maxHeight=3)
                    networking.setText(status_text)
                logger.debug(status_text)
                logger.debug(self.network_status)
            else:
                networking = Textbox(25, 1, "Not Connected")
            elements.setField(Label("Networking:"), 0, 0, anchorLeft = 1, anchorTop = 1)
            elements.setField(networking, 1, 0, anchorLeft = 1, padding=(4, 0, 0, 1))
            elements.setField(Label("Logical Network   Device    MAC Address"),1,4,anchorLeft =1)
            networks = logical_to_physical_networks()
            if len(networks) >= 3:
               net_scroll = 1
            else:
                net_scroll = 0
            self.network_list = Textbox(50, 3, "", scroll = net_scroll)
            net_entry = ""
            for key in networks.iterkeys():
                device, mac = networks[key]
                key = pad_or_trim(12, key)
                device = pad_or_trim(8,device)
                net_entry += " %1s %6s  %9s\n" % (key, device, mac)
            elements.setField(self.network_list, 1, 5, anchorLeft = 1, padding=(4, 0, 0, 1))
            self.network_list.setText(net_entry)
            logging_status_text = ""
            if not get_rsyslog_config() is None:
                host,port = get_rsyslog_config()
                logging_status_text += "Rsyslog: %s:%s\n" % (host,port)
            netconsole_server = augtool_get("/files/etc/sysconfig/netconsole/SYSLOGADDR")
            netconsole_server_port = augtool_get("/files/etc/sysconfig/netconsole/SYSLOGPORT")
            if netconsole_server and netconsole_server_port:
                logging_status_text += "Netconsole: %s:%s" % (netconsole_server,netconsole_server_port)
            if len(logging_status_text) == 0:
                logging_status_text = "Local Only"
            logging_status = Textbox(45, 2, logging_status_text)
            elements.setField(Label("Logs:"), 0, 6, anchorLeft = 1)
            elements.setField(logging_status, 1, 6, anchorLeft = 1, padding=(4, 0, 0, 0))
            try:
                conn = libvirt.openReadOnly(None)
                self.dom_count = conn.numOfDomains()
                conn.close()
            except:
                self.dom_count = "Failed to connect"
            self.jobs_status = Textbox(18, 1, str(self.dom_count))
            running_vms_grid = Grid(2,1)
            running_vms_grid.setField(Label("Running VMs:   "), 0, 0, anchorLeft = 1)
            running_vms_grid.setField(self.jobs_status, 1, 0, anchorLeft = 1)
            main_grid.setField(elements, 0, 1, anchorLeft = 1)
            hwvirt_msg =  get_virt_hw_status()
            if not hwvirt_msg is "":
                self.hwvirt = Textbox(50, 1, hwvirt_msg)
                main_grid.setField(self.hwvirt, 0, 3, anchorLeft = 1, padding=(0,1,0,0))
            else:
                main_grid.setField(running_vms_grid, 0, 3, anchorLeft = 1, padding=(0,0,0,0))

            help_text = Textbox(62, 1, "Press F8 For Support Menu")
            main_grid.setField(help_text, 0, 4, anchorLeft = 1, padding=(0,0,0,0))

            self.ssh_hostkey_btn = CompactButton("View Host Key")
            main_grid.setField(self.ssh_hostkey_btn, 0, 5, anchorLeft = 1, padding=(1,1,0,0))

            return [Label(""), main_grid]

      def logging_configuration_page(self, screen):
          elements = Grid(2, 8)
          heading = Label("Logging")
          if is_console():
              heading.setColors(customColorset(1))
          elements.setField(heading, 0, 0, anchorLeft = 1)
          logrotate_grid = Grid(2,2)
          logrotate_grid.setField(Label("  Logrotate Max Log Size (KB): "), 0, 0, anchorLeft = 1)
          self.logrotate_max_size = Entry(5, "", scroll = 0)
          self.logrotate_max_size.setCallback(self.valid_logrotate_max_size_callback)
          logrotate_grid.setField(self.logrotate_max_size, 1, 0, anchorLeft = 1)
          current_logrotate_size = get_logrotate_size()
          self.logrotate_max_size.set(current_logrotate_size)
          elements.setField(logrotate_grid, 0, 1, anchorLeft = 1, padding = (0,1,0,0))
          elements.setField(Label(" "), 0, 2, anchorLeft = 1)
          elements.setField(Textbox(45,2,"Rsyslog is an enhanced multi-threaded syslogd"), 0, 3, anchorLeft = 1)
          rsyslog_grid = Grid(2,2)
          rsyslog_grid.setField(Label("  Server Address:"), 0, 0, anchorLeft = 1)
          self.syslog_server = Entry(25, "")
          self.syslog_server.setCallback(self.valid_syslog_server_callback)
          rsyslog_grid.setField(self.syslog_server, 1, 0, anchorLeft = 1, padding=(2, 0, 0, 1))
          self.syslog_port = Entry(6, "", scroll = 0)
          self.syslog_port.setCallback(self.valid_syslog_port_callback)
          rsyslog_grid.setField(Label("  Server Port:"), 0, 1, anchorLeft = 1, padding=(0, 0, 0, 1))
          rsyslog_grid.setField(self.syslog_port, 1, 1, anchorLeft = 1, padding=(2, 0, 0, 1))
          rsyslog_config = get_rsyslog_config()
          logger.debug(rsyslog_config)
          if not rsyslog_config is None:
              rsyslog_server, rsyslog_port = rsyslog_config
              self.syslog_server.set(rsyslog_server)
              self.syslog_port.set(rsyslog_port)
          else:
              self.syslog_port.set("514")
          elements.setField(rsyslog_grid, 0, 4, anchorLeft = 1)
          elements.setField(Textbox(48,3,"Netconsole service allows a remote syslog daemon\nto record kernel printk() messages"), 0, 5, anchorLeft = 1, padding = (0,0,0,0))
          netconsole_grid = Grid(2,2)
          netconsole_grid.setField(Label("  Server Address:"), 0, 0, anchorLeft = 1)
          self.netconsole_server = Entry(25, "")
          self.netconsole_server.setCallback(self.valid_netconsole_server_callback)
          netconsole_grid.setField(Label("  Server Port:"), 0, 1, anchorLeft = 1)
          self.netconsole_server_port = Entry(5, "", scroll = 0)
          self.netconsole_server_port.setCallback(self.valid_netconsole_server_port_callback)
          netconsole_grid.setField(self.netconsole_server, 1, 0, anchorLeft = 1, padding=(2, 0, 0, 1))
          netconsole_grid.setField(self.netconsole_server_port, 1, 1, anchorLeft = 1, padding=(2, 0, 0, 0))
          elements.setField(netconsole_grid, 0, 6, anchorLeft = 1, padding = (0,0,0,1))
          netconsole_server = augtool_get("/files/etc/sysconfig/netconsole/SYSLOGADDR")
          netconsole_server_port = augtool_get("/files/etc/sysconfig/netconsole/SYSLOGPORT")
          if netconsole_server is None:
              self.netconsole_server.set("")
          else:
              self.netconsole_server.set(netconsole_server)
          if netconsole_server_port is None:
              self.netconsole_server_port.set("6666")
          else:
              self.netconsole_server_port.set(netconsole_server_port)
          return [Label(""), elements]


      def authentication_configuration_page(self, screen):
          elements = Grid(2, 9)
          heading = Label("Remote Access")
          if is_console():
              heading.setColors(customColorset(1))
          elements.setField(heading, 0, 0, anchorLeft = 1)
          pw_elements = Grid (3,3)
          self.current_ssh_pwd_status = augtool_get("/files/etc/ssh/sshd_config/PasswordAuthentication")
          if self.current_ssh_pwd_status == "yes":
              self.current_ssh_pwd_status = 1
          else:
              self.current_ssh_pwd_status = 0
          self.ssh_passwd_status = Checkbox("Enable ssh password authentication", isOn=self.current_ssh_pwd_status)
          elements.setField(self.ssh_passwd_status, 0, 1, anchorLeft = 1)
          local_heading = Label("Local Access")
          if is_console():
              local_heading.setColors(customColorset(1))
          elements.setField(local_heading, 0, 3, anchorLeft = 1, padding = (0,2,0,0))
          elements.setField(Label(" "), 0, 6)
          pw_elements.setField(Label("Password: "), 0, 1, anchorLeft = 1)
          pw_elements.setField(Label("Confirm Password: "), 0, 2, anchorLeft = 1)
          self.root_password_1 = Entry(15,password = 1)
          self.root_password_1.setCallback(self.password_check_callback)
          self.root_password_2 = Entry(15,password = 1)
          self.root_password_2.setCallback(self.password_check_callback)
          pw_elements.setField(self.root_password_1, 1,1)
          pw_elements.setField(self.root_password_2, 1,2)
          self.pw_msg = Textbox(60, 6, "", wrap=1)
          elements.setField(pw_elements, 0, 7, anchorLeft=1)
          elements.setField(self.pw_msg, 0, 8, padding = (0,1,0,0))
          return [Label(""), elements]

      def network_configuration_page(self, screen):
          self.network_config_fields = []
          aug.load()
          grid = Grid(2,15)
          self.heading = Label("System Identification")
          grid.setField(self.heading, 0, 1, anchorLeft = 1)
          hostname_grid = Grid(2,2)
          hostname_grid.setField(Label("Hostname: "), 0, 1, anchorLeft = 1, padding=(0,0,4,0))
          self.current_hostname = os.uname()[1]
          hostname = os.uname()[1]
          self.net_hostname = Entry(35, hostname)
          self.network_config_fields += [self.net_hostname]
          self.net_hostname.setCallback(self.valid_hostname_callback)
          self.ntp_dhcp = 0
          hostname_grid.setField(self.net_hostname, 1, 1, anchorLeft = 1, padding=(0,0,0,0))
          grid.setField(hostname_grid, 0, 3, anchorLeft=1)
          dns_grid = Grid(2,2)
          self.dns_host1 = Entry(25)
          self.network_config_fields += [self.dns_host1]
          self.dns_host1.setCallback(self.dns_host1_callback)
          self.current_dns_host1 = augtool_get("/files/etc/resolv.conf/nameserver[1]")
          if self.current_dns_host1:
              self.dns_host1.set(self.current_dns_host1)
          else:
              self.dns_host1.set("")
          self.dns_host2 = Entry(25)
          self.network_config_fields += [self.dns_host2]
          self.dns_host2.setCallback(self.dns_host2_callback)
          self.current_dns_host2 = augtool_get("/files/etc/resolv.conf/nameserver[2]")
          if self.current_dns_host2:
              self.dns_host2.set(self.current_dns_host2)
          else:
              self.dns_host2.set("")
          dns_grid.setField(Label("DNS Server 1: "), 0, 0, anchorLeft = 1)
          dns_grid.setField(Label("DNS Server 2: "), 0, 1, anchorLeft = 1)
          dns_grid.setField(self.dns_host1, 1, 0, anchorLeft = 1)
          dns_grid.setField(self.dns_host2, 1, 1, anchorLeft = 1)
          grid.setField(Label("  "), 0, 4)
          grid.setField(dns_grid, 0, 6, anchorLeft =1)
          grid.setField(Label("  "), 0, 7)
          ntp_grid = Grid(2,2)
          self.ntp_host1 = Entry(25)
          self.network_config_fields += [self.ntp_host1]
          self.ntp_host1.setCallback(self.ntp_host1_callback)

          self.ntp_host2 = Entry(25)
          self.network_config_fields += [self.ntp_host2]
          self.ntp_host2.setCallback(self.ntp_host2_callback)

          self.current_ntp_host1 = augtool_get("/files/etc/ntp.conf/server[1]")
          if self.current_ntp_host1:
              self.ntp_host1.set(self.current_ntp_host1)
          self.current_ntp_host2 = augtool_get("/files/etc/ntp.conf/server[2]")
          if self.current_ntp_host2:
              self.ntp_host2.set(self.current_ntp_host2)
          ntp_grid.setField(Label("NTP Server 1: "), 0, 0, anchorLeft = 1)
          ntp_grid.setField(Label("NTP Server 2: "), 0, 1, anchorLeft = 1)
          ntp_grid.setField(self.ntp_host1, 1, 0, anchorLeft = 1)
          ntp_grid.setField(self.ntp_host2, 1, 1, anchorLeft = 1)
          grid.setField(Label("  "), 0, 10)
          grid.setField(ntp_grid, 0, 9, anchorLeft =1)
          self.nic_dict, self.configured_nics, self.ntp_dhcp = get_system_nics()
          if len(self.nic_dict) > 5:
              self.nic_lb = Listbox(height = 5, width = 56, returnExit = 1, scroll = 1)
          else:
              self.nic_lb = Listbox(height = 5, width = 56, returnExit = 1, scroll = 0)
          for key in sorted(self.nic_dict.iterkeys()):
              dev_interface,dev_bootproto,dev_vendor,dev_address,dev_driver,dev_conf_status,dev_bridge = self.nic_dict[key].split(",", 6)
              dev_vendor = pad_or_trim(10, dev_vendor)
              dev_interface = pad_or_trim(6, dev_interface)
              nic_option = '%2s %13s %10s %19s\n' % (dev_interface,dev_conf_status,dev_vendor,dev_address)
              self.nic_lb.append(nic_option, dev_interface.strip())
          NIC_LABEL = Label("Device  Status          Model     MAC Address")
          grid.setField(NIC_LABEL, 0, 11, (0, 0, 0, 0), anchorLeft = 1)
          grid.setField(self.nic_lb, 0, 12)
          if os.path.exists("/etc/sysconfig/network-scripts/ifcfg-rhevm"):
              for item in self.dns_host1, self.dns_host2, self.ntp_host1, self.ntp_host2:
                  item.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
              self.heading.setText("Managed by RHEV-M (Read Only)")
          if self.ntp_dhcp == 1:
              for item in self.ntp_host1, self.ntp_host2:
                  item.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)

          self.original_system_network_config = self.get_tui_field_network_config()
          if (hasattr(self, "preset_network_config") 
              and self.preset_network_config is not None):
              for field, value in zip(self.network_config_fields, self.preset_network_config):
                  field.set(value)

          return [Label(""),
                  grid]

      def network_details_page(self,screen):
          grid = Grid(1,15)
          if system("ethtool %s|grep \"Link detected\"|grep yes" % self.nic_lb.current()):
              link_status = "Active"
          else:
              link_status = "Inactive"
          dev = self.nic_lb.current()
          interface,bootproto,vendor,address,driver,conf_status,dev_bridge = self.nic_dict[dev].split(",", 6)
          nic_detail_grid = Grid(6, 10)
          nic_detail_grid.setField(Label("Interface:   "), 0, 1, anchorLeft = 1, padding=(0,0,1,0))
          nic_detail_grid.setField(Label("Protocol:    "), 0, 2, anchorLeft = 1, padding=(0,0,1,0))
          nic_detail_grid.setField(Label("Link Status: "), 0, 3, anchorLeft = 1, padding=(0,0,1,0))
          nic_detail_grid.setField(Label("Driver:      "), 3, 1, anchorLeft = 1, padding=(0,0,1,0))
          nic_detail_grid.setField(Label("Vendor:      "), 3, 2, anchorLeft = 1, padding=(0,0,1,0))
          nic_detail_grid.setField(Label("MAC Address: "), 3, 3, anchorLeft = 1, padding=(0,0,1,0))
          nic_detail_grid.setField(Label(interface), 1, 1, anchorLeft = 1, padding=(0,0,5,0))
          nic_detail_grid.setField(Label(bootproto), 1, 2, anchorLeft = 1, padding=(0,0,5,0))
          nic_detail_grid.setField(Label(link_status), 1, 3, anchorLeft = 1, padding=(0,0,5,0))
          nic_detail_grid.setField(Label(driver), 4, 1, anchorLeft = 1, padding=(0,0,0,0))
          nic_detail_grid.setField(Label(vendor), 4, 2, anchorLeft = 1, padding=(0,0,0,0))
          nic_detail_grid.setField(Label(address), 4, 3, anchorLeft = 1, padding=(0,0,0,0))
          grid.setField(nic_detail_grid, 0, 1)
          ipv4_main_grid = Grid(6,8)
          self.disabled_ipv4_nic_proto = Checkbox("Disabled ")
          self.disabled_ipv4_nic_proto.setCallback(self.ipv4_disabled_callback)
          self.dhcp_ipv4_nic_proto = Checkbox("DHCP ")
          self.dhcp_ipv4_nic_proto.setCallback(self.ipv4_dhcp_callback)
          self.static_ipv4_nic_proto = Checkbox("Static ")
          self.static_ipv4_nic_proto.setCallback(self.ipv4_static_callback)
          if bootproto.lower() == "dhcp":
              self.dhcp_ipv4_nic_proto.setValue("*")
          elif bootproto.lower() == "static":
              self.static_ipv4_nic_proto.setValue("*")
          else:
              self.disabled_ipv4_nic_proto.setValue("*")
          ipv4_proto_grid = Grid(6,1)
          ipv4_proto_grid.setField(self.disabled_ipv4_nic_proto, 0, 0, anchorLeft = 1)
          ipv4_proto_grid.setField(self.dhcp_ipv4_nic_proto, 2, 0, anchorLeft = 1)
          ipv4_proto_grid.setField(self.static_ipv4_nic_proto, 4, 0, anchorLeft = 1)
          ipv4_main_grid.setField(Label("IPv4 Settings"), 0, 0, anchorLeft = 1)
          ipv4_main_grid.setField(ipv4_proto_grid, 0, 2, anchorLeft = 1)
          self.ipv4_netdevip = Entry(16, "", scroll = 0)
          self.ipv4_netdevip.setCallback(self.ipv4_ip_callback)
          self.ipv4_netdevmask = Entry(16, "", scroll = 0)
          self.ipv4_netdevmask.setCallback(self.ipv4_netmask_callback)
          self.ipv4_netdevgateway = Entry(16, "", scroll = 0)
          self.ipv4_netdevgateway.setCallback(self.ipv4_gateway_callback)
          if not dev_bridge is None:
              dev = dev_bridge
          current_ip = get_ip_address(dev)
          if current_ip != "":
              self.ipv4_netdevip.set(current_ip)
          current_netmask = get_netmask(dev)
          if current_netmask != "":
              self.ipv4_netdevmask.set(current_netmask)
          current_gateway = get_gateway(dev)
          if is_valid_ipv4(current_gateway) or is_valid_ipv6(current_gateway):
              self.ipv4_netdevgateway.set(current_gateway)
          ipv4_grid = Grid (5,3)
          ipv4_grid.setField(Label("IP Address: "), 0, 1, anchorLeft = 1)
          ipv4_grid.setField(Label(" Netmask: "), 3, 1, anchorLeft = 1)
          ipv4_grid.setField(Label("Gateway:"), 0, 2, anchorLeft = 1)
          ipv4_grid.setField(self.ipv4_netdevip, 2, 1)
          ipv4_grid.setField(self.ipv4_netdevmask, 4, 1)
          ipv4_grid.setField(self.ipv4_netdevgateway, 2, 2)
          ipv4_main_grid.setField(ipv4_grid, 0,3)
          if self.dhcp_ipv4_nic_proto.value() == 1:
              self.ipv4_dhcp_callback()
          elif self.static_ipv4_nic_proto.value() == 1:
              self.ipv4_static_callback()
          else:
              self.ipv4_disabled_callback()
          # prepopulate current values only in case of missing values
          if self.__nic_config_failed == 1:
              try:
                  self.ipv4_netdevip.set(self.ipv4_current_netdevip)
                  self.ipv4_netdevmask.set(self.ipv4_current_netdevmask)
                  self.ipv4_netdevgateway.set(self.ipv4_current_netdevgateway)
                  self.static_ipv4_nic_proto.setValue("*")
                  self.ipv4_static_callback()
              except:
                  pass
          # ipv6 grids
          ipv6_main_grid = Grid(6,8)
          self.disabled_ipv6_nic_proto = Checkbox("Disabled ")
          self.disabled_ipv6_nic_proto.setCallback(self.ipv6_disabled_callback)
          self.dhcp_ipv6_nic_proto = Checkbox("DHCP ")
          self.dhcp_ipv6_nic_proto.setCallback(self.ipv6_dhcp_callback)
          self.static_ipv6_nic_proto = Checkbox("Static ")
          self.static_ipv6_nic_proto.setCallback(self.ipv6_static_callback)
          self.auto_ipv6_nic_proto = Checkbox("Auto")
          self.auto_ipv6_nic_proto.setCallback(self.ipv6_auto_callback)
          ipv6_autoconf_lookup_cmd = "/files/etc/sysconfig/network-scripts/ifcfg-%s/IPV6_AUTOCONF" % self.nic_lb.current()
          ipv6_autoconf = augtool_get(ipv6_autoconf_lookup_cmd)
          if ipv6_autoconf is None:
              ipv6_autoconf_lookup_cmd = "/files/etc/sysconfig/network-scripts/ifcfg-br%s/IPV6_AUTOCONF" % self.nic_lb.current()
              ipv6_autoconf = augtool_get(ipv6_autoconf_lookup_cmd)
          ipv6_dhcp_lookup_cmd = "/files/etc/sysconfig/network-scripts/ifcfg-%s/DHCPV6C" % self.nic_lb.current()
          ipv6_dhcp = augtool_get(ipv6_dhcp_lookup_cmd)
          if ipv6_dhcp is None:
              ipv6_dhcp_lookup_cmd = "/files/etc/sysconfig/network-scripts/ifcfg-br%s/DHCPV6C" % self.nic_lb.current()
              ipv6_dhcp = augtool_get(ipv6_dhcp_lookup_cmd)
          ipv6_bootproto = ""
          if ipv6_autoconf == "yes":
              ipv6_bootproto = "auto"
          if ipv6_dhcp == "yes":
              ipv6_bootproto = "dhcp"
          if ipv6_bootproto == "dhcp":
              self.dhcp_ipv6_nic_proto.setValue("*")
          elif ipv6_bootproto == "auto":
              self.auto_ipv6_nic_proto.setValue("*")
          else:
              self.disabled_ipv6_nic_proto.setValue("*")
          ipv6_proto_grid = Grid(6,1)
          ipv6_proto_grid.setField(self.disabled_ipv6_nic_proto, 0, 0, anchorLeft = 1)
          ipv6_proto_grid.setField(self.dhcp_ipv6_nic_proto, 1, 0, anchorLeft = 1)
          ipv6_proto_grid.setField(self.static_ipv6_nic_proto, 2, 0, anchorLeft = 1)
          ipv6_proto_grid.setField(self.auto_ipv6_nic_proto, 3, 0, anchorLeft = 1)
          ipv6_main_grid.setField(Label("IPv6 Settings"), 0, 0, anchorLeft = 1)
          ipv6_main_grid.setField(ipv6_proto_grid, 0, 2, anchorLeft = 1)
          self.ipv6_netdevip = Entry(39, "", scroll = 0)
          self.ipv6_netdevip.setCallback(self.ipv6_ip_callback)
          self.ipv6_netdevmask = Entry(39, "", scroll = 0)
          self.ipv6_netdevmask.setCallback(self.ipv6_netmask_callback)
          self.ipv6_netdevgateway = Entry(39, "", scroll = 0)
          self.ipv6_netdevgateway.setCallback(self.ipv6_gateway_callback)
          if "OVIRT_IPV6_ADDRESS" in OVIRT_VARS:
              self.ipv6_netdevip.set(OVIRT_VARS["OVIRT_IPV6_ADDRESS"])
          else:
              try:
                  current_ip, current_netmask = get_ipv6_address(self.nic_lb.current())
              except:
                  current_ip = ""
                  current_netmask = ""
              if current_ip == "":
                  try:
                      current_ip, current_netmask = get_ipv6_address("br" + self.nic_lb.current())
                  except:
                      pass
              if current_ip != "":
                  self.ipv6_netdevip.set(current_ip)
          if "OVIRT_IPV6_NETMASK" in OVIRT_VARS:
              self.ipv6_netdevmask.set(OVIRT_VARS["OVIRT_IPV6_NETMASK"])
          else:
              if current_ip != "":
                  self.ipv6_netdevmask.set(current_netmask)
          if "OVIRT_IPV6_GATEWAY" in OVIRT_VARS:
              self.ipv6_netdevgateway.set(OVIRT_VARS["OVIRT_IPV6_GATEWAY"])
          else:
              current_gateway = get_ipv6_gateway(self.nic_lb.current())
              if current_gateway == "":
                  current_gateway = get_gateway("br" + self.nic_lb.current())
          ipv6_grid = Grid (5,4)
          ipv6_grid.setField(Label("IP Address: "), 0, 1, anchorLeft = 1)
          ipv6_grid.setField(Label("Netmask: "), 0, 2, anchorLeft = 1)
          ipv6_grid.setField(Label("Gateway:"), 0, 3, anchorLeft = 1)
          ipv6_grid.setField(self.ipv6_netdevip, 2, 1)
          ipv6_grid.setField(self.ipv6_netdevmask, 2, 2)
          ipv6_grid.setField(self.ipv6_netdevgateway, 2, 3)
          ipv6_main_grid.setField(ipv6_grid, 0,3)
          if self.dhcp_ipv6_nic_proto.value() == 1:
              self.ipv6_dhcp_callback()
          elif self.static_ipv6_nic_proto.value() == 1:
              self.ipv6_static_callback()
          else:
              self.ipv6_disabled_callback()
          grid.setField(Label(" "), 0, 4, anchorLeft = 1)
          grid.setField(ipv4_main_grid, 0, 5, anchorLeft = 1)
          grid.setField(Label(" "), 0, 6, anchorLeft = 1)
          # only display ipv6 settings if OVIRT_IPV6 key is in defaults file
          if OVIRT_VARS.has_key("OVIRT_IPV6"):
              grid.setField(ipv6_main_grid, 0, 7, anchorLeft = 1)
          else:
              grid.setField(Label(" "), 0, 7, anchorLeft = 1, padding=(0,4,0,0))
          grid.setField(Label(" "), 0, 8, anchorLeft = 1)
          vlan_grid = Grid(2,2)
          self.netvlanid = Entry(4, "", scroll = 0)
          self.netvlanid.setCallback(self.netvlanid_callback)
          for vlan in os.listdir("/proc/net/vlan/"):
            # XXX wrong match e.g. eth10.1 with eth1
            if self.nic_lb.current() in vlan:
              vlan_id = vlan.replace(self.nic_lb.current()+".","")
              self.netvlanid.set(vlan_id)
          vlan_grid.setField(Label("VLAN ID: "), 0, 0, anchorLeft = 1)
          vlan_grid.setField(self.netvlanid, 1, 0)
          grid.setField(vlan_grid, 0, 9, anchorLeft = 1)
          # disable all items if registered to rhevm server
          if os.path.exists("/etc/sysconfig/network-scripts/ifcfg-rhevm"):
              for item in self.disabled_ipv4_nic_proto, self.dhcp_ipv4_nic_proto, self.static_ipv4_nic_proto, \
                  self.ipv4_netdevip, self.ipv4_netdevmask, self.ipv4_netdevgateway, self.disabled_ipv6_nic_proto, \
                  self.dhcp_ipv6_nic_proto, self.static_ipv6_nic_proto, self.auto_ipv6_nic_proto, \
                  self.ipv6_netdevip, self.ipv6_netdevmask, self.ipv6_netdevgateway, self.netvlanid:
                  item.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
          try:
              current_ip = get_ipv6_address("br" + self.nic_lb.current()).split("\n")
              if current_ip == "":
                  current_ip = get_ipv6_address(self.nic_lb.current()).split("\n")
              if current_ip != "":
                  if len(current_ip) > 1:
                      current_ip = current_ip[0]
                      current_ip, netmask = current_ip.split("/")
                  else:
                      current_ip, netmask = current_ip.split("/")
                  self.ipv6_netdevip.set(current_ip)
                  self.ipv6_netdevmask.set(netmask)
          except:
              pass
          return [Label(""),
                  grid]

      def snmp_configuration_page(self, screen):
          elements = Grid(2, 9)
          heading = Label("SNMP")
          if is_console():
              heading.setColors(customColorset(1))
          elements.setField(heading, 0, 0, anchorLeft = 1)
          pw_elements = Grid (3,3)
          self.current_snmp_status = 0
          if os.path.exists("/etc/snmp/snmpd.conf"):
              f = open("/etc/snmp/snmpd.conf")
              for line in f:
                  if "createUser" in line:
                      self.current_snmp_status = 1
              f.close()
          self.snmp_status = Checkbox("Enable SNMP", isOn=self.current_snmp_status)
          elements.setField(self.snmp_status, 0, 1, anchorLeft = 1)
          local_heading = Label("SNMP Password")
          if is_console():
              local_heading.setColors(customColorset(1))
          elements.setField(local_heading, 0, 3, anchorLeft = 1, padding = (0,2,0,0))
          elements.setField(Label(" "), 0, 6)
          pw_elements.setField(Label("Password: "), 0, 1, anchorLeft = 1)
          pw_elements.setField(Label("Confirm Password: "), 0, 2, anchorLeft = 1)
          self.root_password_1 = Entry(15,password = 1)
          self.root_password_1.setCallback(self.password_check_callback)
          self.root_password_2 = Entry(15,password = 1)
          self.root_password_2.setCallback(self.password_check_callback)
          pw_elements.setField(self.root_password_1, 1,1)
          pw_elements.setField(self.root_password_2, 1,2)
          self.pw_msg = Textbox(60, 6, "", wrap=1)
          elements.setField(pw_elements, 0, 7, anchorLeft=1)
          elements.setField(self.pw_msg, 0, 8, padding = (0,1,0,0))
          return [Label(""), elements]


      def keyboard_configuration_page(self, screen):
          # placeholder for system-config-keyboard-base, will remove move later
          try:
              import system_config_keyboard.keyboard as keyboard
          except:
              return [Label(""), elements]

          elements = Grid(2, 9)
          heading = Label("Keyboard Layout Selection")
          if is_console():
              heading.setColors(customColorset(1))
          self.kbd = keyboard.Keyboard()
          self.kbd.read()
          self.kbdDict = self.kbd.modelDict
          self.kbdKeys = self.kbdDict.keys()
          self.kbdKeys.sort()
          self.kb_list = Listbox(10, scroll = 1, returnExit = 0)
          default = ""
          for kbd in self.kbdKeys:
              if kbd == self.kbd.get():
                  default = kbd
              plainName = self.kbdDict[kbd][0]
              self.kb_list.append(plainName, kbd)
          try:
              self.kb_list.setCurrent(default)
          except:
              pass
          elements.setField(heading, 0, 0, anchorLeft = 1)
          elements.setField(self.kb_list, 0, 1, anchorLeft = 1, padding=(1,1,0,3))
          return [Label(""), elements]

      def kdump_configuration_page(self, screen):
          elements = Grid(2, 12)
          heading = Label("Kernel Dump")
          if is_console():
              heading.setColors(customColorset(1))
          elements.setField(heading, 0, 0, anchorLeft = 1)
          if not network_up():
              elements.setField(Label(" * Network Down, Configuration Disabled * "), 0, 1, anchorLeft = 1)
          else:
              elements.setField(Label(" "), 0, 1, anchorLeft = 1)
          kdump_type_grid = Grid(5, 2)
          self.kdump_nfs_type = Checkbox("NFS ")
          self.kdump_nfs_type.setCallback(self.kdump_nfs_callback)
          self.kdump_ssh_type = Checkbox("SSH ")
          self.kdump_ssh_type.setCallback(self.kdump_ssh_callback)
          self.kdump_restore_type = Checkbox("Restore (Local)")
          self.kdump_restore_type.setCallback(self.kdump_restore_callback)
          kdump_type_grid.setField(self.kdump_nfs_type, 0, 0, anchorLeft = 1)
          kdump_type_grid.setField(self.kdump_ssh_type, 1, 0, anchorLeft = 1)
          kdump_type_grid.setField(self.kdump_restore_type, 2, 0, anchorLeft = 1)
          elements.setField(kdump_type_grid, 0, 2, anchorLeft = 1)
          elements.setField(Label(" "), 0, 3, anchorLeft = 1)
          elements.setField(Label("NFS Location (example.redhat.com:/var/crash):"), 0, 4, anchorLeft = 1)
          self.kdump_nfs_config = Entry(30, "")
          self.kdump_nfs_config.setCallback(self.kdump_valid_nfs_callback)
          elements.setField(self.kdump_nfs_config, 0, 5, anchorLeft = 1)
          elements.setField(Label(" "), 0, 6, anchorLeft = 1)
          elements.setField(Label("SSH Location (root@example.redhat.com)"), 0, 7, anchorLeft = 1)
          self.kdump_ssh_config = Entry(30, "")
          self.kdump_ssh_config.setCallback(self.kdump_valid_ssh_callback)
          elements.setField(self.kdump_ssh_config, 0, 8, anchorLeft = 1, padding =(0,0,0,6))
          try:
              kdump_config_file = open("/etc/kdump.conf")
              for line in kdump_config_file:
                  if not line.startswith("#"):
                      if line.startswith("net"):
                          line = line.replace("net ", "")
                          if "@" in line:
                              self.kdump_ssh_type.setValue("*")
                              self.kdump_ssh_config.set(line.strip())
                              self.kdump_nfs_config.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
                          elif ":" in line:
                              self.kdump_nfs_type.setValue("*")
                              self.kdump_nfs_config.set(line.strip())
                              self.kdump_ssh_config.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
                      elif "/dev/HostVG/Data" in line:
                          self.kdump_restore_type.setValue("*")
              kdump_config_file.close()
          except:
              pass
          if not network_up():
              self.kdump_nfs_type.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
              self.kdump_ssh_type.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
              self.kdump_nfs_config.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
              self.kdump_ssh_config.setFlags(_snack.FLAG_DISABLED, _snack.FLAGS_SET)
          return [Label(""), elements]

      def support_page(self, screen):
          logger.info("Loading Support Page")
          elements = Grid(2, 8)
          elements.setField(Label(" View Log Files "), 0, 1, anchorLeft = 1, padding = (0,1,0,1))
          self.log_menu_list = Listbox(5, width = 40, returnExit = 1, border = 0, showCursor = 0, scroll = 0)
          self.log_menu_list.append(" oVirt Log (ovirt.log)", "/var/log/ovirt.log")
          self.log_menu_list.append(" System Messages (messages)", "/var/log/messages")
          self.log_menu_list.append(" Security Log (secure)", "/var/log/secure")
          if os.path.exists("/var/log/vdsm/vdsm.log"):
              self.log_menu_list.append(" VDSM Log (vdsm.log)", "/var/log/vdsm/vdsm.log")
          if os.path.exists("/var/log/vdsm-reg/vdsm-reg.log"):
              self.log_menu_list.append(" VDSM Registration Log (vdsm-reg.log)", "/var/log/vdsm-reg/vdsm-reg.log")
          elements.setField(self.log_menu_list, 0, 2, anchorLeft = 1, padding = (0,0,0,6))
          elements.setField(Label(" After viewing press \"q\" to quit "), 0, 3, anchorLeft = 1, padding = (0,1,0,0))

          return [Label(""), elements]

      def remote_storage_configuration_page(self, screen):
          elements = Grid(2, 8)
          heading = Label("Remote Storage")
          if is_console():
              heading.setColors(customColorset(1))
          elements.setField(heading, 0, 0, anchorLeft = 1)
          elements.setField(Label(" "), 0, 1, anchorLeft = 1)
          elements.setField(Label("iSCSI Initiator Name:"), 0, 2, anchorLeft = 1)
          self.iscsi_initiator_config = Entry(50, "")
          self.iscsi_initiator_config.setCallback(self.valid_iqn_callback)
          elements.setField(self.iscsi_initiator_config, 0, 3, anchorLeft = 1, padding =(0,0,0,11))
          current_iscsi_initiator_name = get_current_iscsi_initiator_name()
          if current_iscsi_initiator_name is not None:
              self.iscsi_initiator_config.set(current_iscsi_initiator_name)
          return [Label(""), elements]

      def menuSpacing(self):
          if not self.__current_page == NETWORK_DETAILS_PAGE: # pages that dont use main listbox
              if self.menu_list.current() != self.__current_page:
                  self.__current_page = self.menu_list.current()
                  screen.start()

      def get_tui_field_network_config(self):
          return [ f.value() for f in self.network_config_fields ]

      def is_same_network_config(self, a, b):
          return all (x == y for x, y in zip(a, b))

      def process_network_config(self):
          network = Network()
          if self.net_hostname.value() == "":
              network.remove_non_localhost()
              augtool("set", "/files/etc/sysconfig/network/HOSTNAME", "")
              os.system("hostname \"" + self.net_hostname.value()+"\"")
          elif self.net_hostname.value() != self.current_hostname and is_valid_hostname(self.net_hostname.value()):
              network.remove_non_localhost()
              network.add_localhost_alias(self.net_hostname.value())
              augtool("set", "/files/etc/sysconfig/network/HOSTNAME", self.net_hostname.value())
              os.system("hostname " + self.net_hostname.value())
          ovirt_store_config("/etc/sysconfig/network")
          ovirt_store_config("/etc/hosts")
          dns_servers = ""
          ntp_servers = ""
          if not self.dns_host1.value() == "":
              dns_servers += self.dns_host1.value()
          if not self.dns_host2.value() == "":
              dns_servers += "," + self.dns_host2.value()
          if not self.ntp_host1.value() == "":
              ntp_servers += self.ntp_host1.value()
          if not self.ntp_host2.value() == "":
              ntp_servers += "," + self.ntp_host2.value()
          if not dns_servers == "":
              augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_DNS", '"' + dns_servers + '"')
          if not ntp_servers == "":
              augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_NTP", '"' + ntp_servers + '"')
          if len(dns_servers) > 0:
              network.configure_dns()
          if len(ntp_servers) > 0:
              network.configure_ntp()
              network.save_ntp_configuration()
          self.net_apply_config = 1
          return

      def process_nic_config(self):
          self._create_warn_screen()
          warn = ButtonChoiceWindow(self.screen, "Confirm Network Settings", "Network Configuration may take a few moments, proceed?")
          self.reset_screen_colors()
          if warn == "ok":
              self._create_blank_screen()
              gridform = GridForm(self.screen, "", 2, 2)
              gridform.add(Label("Verifying Networking Configuration"), 0, 0)
              progress_bar = Scale(50,100)
              gridform.add(progress_bar, 0, 1)
              progress_bar.set(25)
              gridform.draw()
              self.screen.refresh()
              msg = ""
              if self.static_ipv4_nic_proto.value() == 1:
                  if self.ipv4_netdevip.value() == "":
                      msg = "  - IPv4 Address\n"
                  if self.ipv4_netdevmask.value() == "":
                      msg += "  - IPv4 Netmask Address\n"
                  if self.ipv4_netdevgateway.value() == "":
                      msg = "  - IPv4 Gateway Address\n"
                  augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IP_ADDRESS", '"' + self.ipv4_netdevip.value() + '"')
                  augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IP_NETMASK", '"' + self.ipv4_netdevmask.value() + '"')
                  augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IP_GATEWAY", '"' + self.ipv4_netdevgateway.value() + '"')

              if self.static_ipv6_nic_proto.value() == 1:
                  if self.ipv6_netdevmask.value() == "":
                      msg += "  - IPv6 Netmask Address\n"
                  if self.ipv6_netdevgateway.value() == "":
                      msg += "  - IPv6 Gateway Address\n"
                  # left out gateway check to prevent multiple ones
              if msg != "":
                  msg = "Please Input:\n" + msg
                  self._create_warn_screen()
                  warn = ButtonChoiceWindow(self.screen, "Network Settings", msg, buttons = ['Ok'])
                  self.__nic_config_failed = 1
                  self.ipv4_current_netdevip = self.ipv4_netdevip.value()
                  self.ipv4_current_netdevmask = self.ipv4_netdevmask.value()
                  self.ipv4_current_netdevgateway = self.ipv4_netdevgateway.value()
                  self.reset_screen_colors()
                  return
              else:
                  # if exists remove static keys from dictionary
                  if OVIRT_VARS.has_key("OVIRT_IP_ADDRESS"):
                      del OVIRT_VARS["OVIRT_IP_ADDRESS"]
                  if OVIRT_VARS.has_key("OVIRT_IP_NETMASK"):
                      del OVIRT_VARS["OVIRT_IP_NETMASK"]
                  if OVIRT_VARS.has_key("OVIRT_IP_GATEWAY"):
                      del OVIRT_VARS["OVIRT_IP_GATEWAY"]
                  if OVIRT_VARS.has_key("OVIRT_IPV6"):
                      del OVIRT_VARS["OVIRT_IPV6"]
                  if OVIRT_VARS.has_key("OVIRT_ADDRESS"):
                      del OVIRT_VARS["OVIRT_IPV6_ADDRESS"]
                  if OVIRT_VARS.has_key("OVIRT_IPV6_NETMASK"):
                      del OVIRT_VARS["OVIRT_IPV6_NETMASK"]
                  if OVIRT_VARS.has_key("OVIRT_IPV6_GATEWAY"):
                      del OVIRT_VARS["OVIRT_IPV6_GATEWAY"]
                  if OVIRT_VARS.has_key("OVIRT_VLAN"):
                      del OVIRT_VARS["OVIRT_VLAN"]

              gridform = GridForm(self.screen, "", 2, 2)
              gridform.add(Label("Configuring Networking"), 0, 0)
              progress_bar = Scale(50,100)
              gridform.add(progress_bar, 0, 1)
              progress_bar.set(50)
              gridform.draw()
              self.screen.refresh()

              augtool("rm", "/files/" + OVIRT_DEFAULTS + "/OVIRT_BOOTIF", "")
              if self.netvlanid.value() == "":
                  augtool("rm", "/files/" + OVIRT_DEFAULTS + "/OVIRT_VLAN", "")
              if self.disabled_ipv4_nic_proto.value() == 1:
                  augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_BOOTIF", '"' + self.nic_lb.current() + '-DISABLED"')
              else:
                  augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_BOOTIF", '"' + self.nic_lb.current() + '"')
              augtool("rm", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IP_ADDRESS", "")
              augtool("rm", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IP_NETMASK", "")
              augtool("rm", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IP_GATEWAY", "")
              augtool("rm", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IPV6" ,"")
              augtool("rm", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IPV6_ADDRESS", "")
              augtool("rm", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IPV6_NETMASK", "")
              augtool("rm", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IPV6_GATEWAY", "")

              msg = ""
              if self.static_ipv4_nic_proto.value() == 1:
                  if self.ipv4_netdevip.value() == "":
                      msg = "  - IPv4 Address\n"
                  if self.ipv4_netdevmask.value() == "":
                      msg += "  - IPv4 Netmask Address\n"
                  if self.ipv4_netdevgateway.value() == "":
                      msg = "  - IPv4 Gateway Address\n"
                  augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IP_ADDRESS", '"' + self.ipv4_netdevip.value() + '"')
                  augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IP_NETMASK", '"' + self.ipv4_netdevmask.value() + '"')
                  augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IP_GATEWAY", '"' + self.ipv4_netdevgateway.value() + '"')

              if self.static_ipv6_nic_proto.value() == 1:
                  if self.ipv6_netdevmask.value() == "":
                      msg += "  - IPv6 Netmask Address\n"
                  if self.ipv6_netdevgateway.value() == "":
                      msg += "  - IPv6 Gateway Address\n"
                  # left out gateway check to prevent multiple ones
              if msg != "":
                  msg = "Please Input:\n" + msg
                  self._create_warn_screen()
                  warn = ButtonChoiceWindow(self.screen, "Network Settings", msg, buttons = ['Ok'])
                  self.__nic_config_failed = 1
                  self.ipv4_current_netdevip = self.ipv4_netdevip.value()
                  self.ipv4_current_netdevmask = self.ipv4_netdevmask.value()
                  self.ipv4_current_netdevgateway = self.ipv4_netdevgateway.value()
                  self.reset_screen_colors()
                  return
              else:
                  # if exists remove static keys from dictionary
                  if OVIRT_VARS.has_key("OVIRT_IP_ADDRESS"):
                      del OVIRT_VARS["OVIRT_IP_ADDRESS"]
                  if OVIRT_VARS.has_key("OVIRT_IP_NETMASK"):
                      del OVIRT_VARS["OVIRT_IP_NETMASK"]
                  if OVIRT_VARS.has_key("OVIRT_IP_GATEWAY"):
                      del OVIRT_VARS["OVIRT_IP_GATEWAY"]
                  if OVIRT_VARS.has_key("OVIRT_IPV6"):
                      del OVIRT_VARS["OVIRT_IPV6"]
                  if OVIRT_VARS.has_key("OVIRT_ADDRESS"):
                      del OVIRT_VARS["OVIRT_IPV6_ADDRESS"]
                  if OVIRT_VARS.has_key("OVIRT_IPV6_NETMASK"):
                      del OVIRT_VARS["OVIRT_IPV6_NETMASK"]
                  if OVIRT_VARS.has_key("OVIRT_IPV6_GATEWAY"):
                      del OVIRT_VARS["OVIRT_IPV6_GATEWAY"]

              if self.netvlanid.value() != "":
                  augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_VLAN", '"' + self.netvlanid.value() + '"')
              if self.dhcp_ipv6_nic_proto.value() == 1:
                  augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IPV6", '"' + "dhcp" + '"')
              if self.auto_ipv6_nic_proto.value() == 1:
                  augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IPV6", '"' + "auto" + '"')
              if self.static_ipv6_nic_proto.value() == 1:
                  augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IPV6", '"' + "static" + '"')
                  if self.ipv6_netdevip.value():
                      augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IPV6_ADDRESS", '"' + self.ipv6_netdevip.value() + '"')
                  if self.ipv6_netdevmask.value():
                      augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IPV6_NETMASK", '"' + self.ipv6_netdevmask.value() + '"')
                  if self.ipv6_netdevgateway.value():
                      augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_IPV6_GATEWAY", '"' + self.ipv6_netdevgateway.value() + '"')

              network = Network()
              network.configure_interface()
              gridform = GridForm(self.screen, "", 2, 2)
              gridform.add(Label("Enabling Network Configuration"), 0, 0)
              progress_bar = Scale(50,100)
              gridform.add(progress_bar, 0, 1)
              progress_bar.set(75)
              gridform.draw()
              self.screen.refresh()
              network.save_network_configuration()
              self.screen.popWindow()
              self.net_apply_config = 1
              return
          else:
              self.__nic_config_failed = 1
              return

      def process_authentication_config(self):
          self._create_warn_screen()
          ssh_restart = False
          if self.root_password_1.value() != "" or self.root_password_2.value() != "":
              if self.root_password_1.value() != self.root_password_2.value():
                  ButtonChoiceWindow(self.screen, "Remote Access", "Passwords Do Not Match", buttons = ['Ok'])
              else:
                  set_password(self.root_password_1.value(), "admin")
                  ButtonChoiceWindow(self.screen, "Remote Access", "Password Successfully Changed", buttons = ['Ok'])
                  logger.info("Admin Password Changed")
          if self.ssh_passwd_status.value() == 1 and self.current_ssh_pwd_status == 0:
              self.current_ssh_pwd_status = augtool("set","/files/etc/ssh/sshd_config/PasswordAuthentication", "yes")
              ssh_restart = True
          elif self.ssh_passwd_status.value() == 0 and self.current_ssh_pwd_status == 1:
              self.current_ssh_pwd_status = augtool("set","/files/etc/ssh/sshd_config/PasswordAuthentication", "no")
              ssh_restart = True
          if ssh_restart:
              os.system("service sshd restart &>/dev/null")
              ButtonChoiceWindow(self.screen, "Remote Access", "SSH Restarted", buttons = ['Ok'])
              logger.info("SSH service restarted")
              ovirt_store_config("/etc/ssh/sshd_config")
          self.reset_screen_colors()
          return True

      def process_logging_config(self):
          ovirt_rsyslog(self.syslog_server.value(), self.syslog_port.value(), "udp")
          ovirt_netconsole(self.netconsole_server.value(), self.netconsole_server_port.value())
          set_logrotate_size(self.logrotate_max_size.value())
          return True

      def process_keyboard_config(self):
          self.kbd.set(self.kb_list.current())
          self.kbd.write()
          self.kbd.activate()
          # store keyboard config
          ovirt_store_config("/etc/sysconfig/keyboard")

      def process_locked_screen(self):
          auth = PAM.pam()
          auth.start("passwd")
          auth.set_item(PAM.PAM_USER, self.login_username)
          global login_password
          login_password = self.login_password.value()
          auth.set_item(PAM.PAM_CONV, pam_conv)
          try:
              auth.authenticate()
          except PAM.error, (resp, code):
              logger.debug(resp)
              return False
          except:
              logger.debug("Internal error")
              return False
          else:
              self.screen_locked = False
              self.__current_page = STATUS_PAGE
              return True

      def process_config(self):
          self._create_blank_screen()
          self._set_title()
          self.gridform.add(Label("Applying Configuration"), 0, 0)
          self.gridform.draw()
          self.screen.refresh()
          if self.__current_page == NETWORK_PAGE:
              ret = self.process_network_config()
          if self.__current_page == AUTHENTICATION_PAGE:
              ret = self.process_authentication_config()
          if self.__current_page == LOGGING_PAGE:
              ret = self.process_logging_config()
          if self.__current_page == NETWORK_DETAILS_PAGE:
              ret = self.process_nic_config()
          if self.__current_page == KEYBOARD_PAGE:
              ret = self.process_keyboard_config()
          if self.__current_page == SNMP_PAGE:
              ret = self.process_snmp_config()
          if self.__current_page == KDUMP_PAGE:
              ret = self.process_kdump_config()
          if self.__current_page == REMOTE_STORAGE_PAGE:
              ret = self.process_remote_storage_config()
          if self.__current_page == LOCKED_PAGE:
              ret = self.process_locked_screen()
          # plugin pages
          plugin_page=FIRST_PLUGIN_PAGE
          for p in self.plugins :
              if self.__current_page == plugin_page:
                  ret = p.action()
                  break
              plugin_page+=1
              if plugin_page > LAST_PLUGIN_PAGE :
                  # should not happen
                  break
          return

      def process_snmp_config(self):
          if self.snmp_status.value() == 1:
              enable_snmpd(self.root_password_1.value())
          elif self.snmp_status.value() == 0:
              disable_snmpd()

      def process_kdump_config(self):
          if self.kdump_nfs_type.value() == 1:
              write_kdump_config(self.kdump_nfs_config.value())
          if self.kdump_ssh_type.value() == 1:
              write_kdump_config(self.kdump_ssh_config.value())
              self.screen.popWindow()
              self.screen.finish()
              # systemctl change
              if os.path.exists("/usr/bin/kdumpctl"):
                  kdump_prop_cmd = "kdumpctl propagate"
              else:
                  kdump_prop_cmd = "service kdump propagate"
              ret = os.system("clear; %s" % kdump_prop_cmd)
              if ret == 0:
                  ovirt_store_config("/root/.ssh/kdump_id_rsa.pub")
                  ovirt_store_config("/root/.ssh/kdump_id_rsa")
                  ovirt_store_config("/root/.ssh/known_hosts")
                  ovirt_store_config("/root/.ssh/config")
          if self.kdump_restore_type.value() == 1:
              restore_kdump_config()
          if not system("service kdump restart"):
              self._create_warn_screen()
              ButtonChoiceWindow(self.screen, "KDump Status", "KDump configuration failed, location unreachable", buttons = ['Ok'])
              self.reset_screen_colors()
              unmount_config("/etc/kdump.conf")
              if os.path.exists("/etc/kdump.conf"):
                  os.remove("/etc/kdump.conf")
          else:
              ovirt_store_config("/etc/kdump.conf")

      def process_remote_storage_config(self):
          set_iscsi_initiator(self.iscsi_initiator_config.value())

      def ssh_hostkey_btn_cb(self):
            self._create_warn_screen()
            ssh_hostkey_msg = "RSA Host Key Fingerprint:\n%s\n\nRSA Host Key:\n%s" % get_ssh_hostkey()
            ButtonChoiceWindow(self.screen, "Host Key", ssh_hostkey_msg, buttons = ['Ok'])
            self.reset_screen_colors()

      def quit(self):
            manual_teardown()
            sys.exit(2)

      def start(self):
            self.plugins = []
            self.last_option = LAST_OPTION
            for imp,mod,ispkg in pkgutil.iter_modules(ovirt_config_setup.__path__, "ovirt_config_setup."):
                module = __import__(mod, fromlist="dummy")
                self.plugins.append(module.get_plugin(self))
                self.last_option+=1

            active = True
            # check for screenlock status
            self.screen_locked = False
            while active and (self.__finished == False):
                logger.debug("Current Page: " + str(self.__current_page))
                self._create_blank_screen()
                screen = self.screen
                # apply any colorsets that were provided.
                if is_console():
                    self.set_console_colors()
                    screen.setColor(customColorset(1), "black", "magenta")
                if self.__current_page == STATUS_PAGE:
                    screen.pushHelpLine(" Use arrow keys to choose option, then press Enter to select it ")
                else:
                    screen.pushHelpLine(" ")
                elements = self.get_elements_for_page(screen, self.__current_page)
                gridform = GridForm(screen, "", 2, 1)
                self._set_title()
                content = Grid(1, len(elements) + 3)
                self.menuo = 1
                self.menu_list = Listbox(18, width = 20, returnExit = 0, border = 0, showCursor = 0)
                self.menu_list.append(" Status", 1)
                self.menu_list.append(" Network", 2)
                self.menu_list.append(" Security", 3)
                self.menu_list.append(" Keyboard",4)
                self.menu_list.append(" SNMP", 5)
                self.menu_list.append(" Logging", 6)
                self.menu_list.append(" Kernel Dump", 7)
                self.menu_list.append(" Remote Storage", 8)
                # plugin menu options
                plugin_page=FIRST_PLUGIN_PAGE
                for p in self.plugins :
                    self.menu_list.append(" " + p.label(), plugin_page)
                    plugin_page+=1
                    if plugin_page > LAST_PLUGIN_PAGE :
                        # should not happen
                        raise "Too many plugins installed: max. %d are allowed." % ((LAST_PLUGIN_PAGE-FIRST_PLUGIN_PAGE)/2+1)
                if self.__current_page != LOCKED_PAGE and self.__current_page != NETWORK_DETAILS_PAGE and self.__current_page != SUPPORT_PAGE:
                    self.menu_list.setCurrent(self.__current_page)
                if not self.screen_locked:
                    if not self.__current_page == NETWORK_DETAILS_PAGE and not self.__current_page == SUPPORT_PAGE:
                        self.menu_list.setCallback(self.menuSpacing)
                        gridform.add(self.menu_list, 0, 0,
                                     anchorTop = 1, anchorLeft = 1,
                                     growx = 0)
                current_element = 0
                for element in elements:
                    content.setField(element, 0, current_element, anchorLeft = 1)
                    current_element += 1
                (fullwidth, fullheight) = _snack.size()
                screen.height = fullheight
                current_element += 1
                buttons = []
                if self.__current_page == NETWORK_PAGE:
                    buttons.append (["Flash Lights to Identify", IDENTIFY_BUTTON])
                if self.__current_page != STATUS_PAGE and self.__current_page < 20 :
                    buttons.append (["Apply", APPLY_BUTTON])
                if self.__current_page == NETWORK_DETAILS_PAGE:
                    buttons.append(["Back", BACK_BUTTON])
                if self.__current_page == STATUS_PAGE:
                    if not pwd_lock_check("admin"):
                        buttons.append(["Lock", LOCK_BUTTON])
                    buttons.append(["Log Off", LOG_OFF_BUTTON])
                    buttons.append(["Restart", RESTART_BUTTON])
                    buttons.append(["Power Off", POWER_OFF_BUTTON])
                if self.__current_page == LOCKED_PAGE:
                    buttons.append(["Unlock", UNLOCK_BUTTON])
                if self.__current_page != STATUS_PAGE and self.__current_page < 20:
                    buttons.append(["Reset", RESET_BUTTON])
                if self.__current_page == SUPPORT_PAGE:
                    buttons.append(["Back to Menu", MENU_BUTTON])
                buttonbar = ButtonBar(screen, buttons, compact = 1)
                if self.__current_page == LOCKED_PAGE:
                    pad = 28
                else:
                    pad = 0
                content.setField(buttonbar, 0, current_element, anchorLeft = 1, padding = (pad,0,0,0))
                gridform.add(content, 1, 0, anchorTop = 1, padding = (2,0,0,0))
                gridform.addHotKey("F2")
                gridform.addHotKey("F8")
                try:
                    (top, left) = (1, 4)
                    result = gridform.runOnce(top, left)
                    menu_choice = self.menu_list.current()
                    pressed = buttonbar.buttonPressed(result)
                    self.menu_list.setCurrent(menu_choice)
                    warn_message = ""
                    try:
                        conn = libvirt.openReadOnly(None)
                        self.dom_count = conn.numOfDomains()
                        conn.close()
                    except:
                        self.dom_count = "Failed to connect"
                    if str(self.dom_count).isdigit():
                        warn_message= "There are %s Virtual Machines running\n\n" % str(self.dom_count)
                    else:
                        warn_message= "Unable to verify any running vms\n\n"
                    self._create_warn_screen()
                    if pressed == IDENTIFY_BUTTON:
                        os.system("ethtool -p " + self.nic_lb.current() + " 10")
                    elif pressed == APPLY_BUTTON or pressed == UNLOCK_BUTTON:
                        errors = []
                        self.process_config()
                    elif pressed == LOCK_BUTTON:
                        self.__current_page = LOCKED_PAGE
                    elif pressed == RESTART_BUTTON:
                        self._create_warn_screen()
                        warn = ButtonChoiceWindow(self.screen, "Confirm System Restart", warn_message + "This will restart the system, proceed?")
                        if warn == "ok":
                            screen.popWindow()
                            screen.finish()
                            os.system("reboot")
                    elif pressed == POWER_OFF_BUTTON:
                        self._create_warn_screen()
                        warn = ButtonChoiceWindow(self.screen, "Confirm System Shutdown", warn_message + "This will shutdown the system, proceed?")
                        if warn == "ok":
                            screen.popWindow()
                            screen.finish()
                            os.system("/usr/bin/clear;shutdown -h now")
                    elif pressed == LOG_OFF_BUTTON:
                        # will exit and ovirt-admin-shell cleans up tty lockfile and drops to login
                        self.quit()
                    elif (result is self.ssh_hostkey_btn):
                        self.ssh_hostkey_btn_cb()

                    if self.__current_page == LOCKED_PAGE:
                        self.screen_locked = True
                    elif result == "F8" and self.__current_page != LOCKED_PAGE:
                        self.__current_page = SUPPORT_PAGE
                    elif result == "F2" and self.__current_page != LOCKED_PAGE:
                        self._create_warn_screen()
                        title = "Shell Access"
                        message = "This is a non persistent filesystem.  Any changes will be lost on reboot.  RPM installations may succeed, but changes will be lost when rebooted."
                        warn = ButtonChoiceWindow(self.screen, title, message)
                        if warn == "ok":
                            screen.popWindow()
                            screen.finish()
                            os.system("/usr/bin/clear;SHELL=/bin/bash /bin/bash")
                    else:
                        if self.__current_page == NETWORK_PAGE:
                            if menu_choice == NETWORK_PAGE:
                                if pressed == RESET_BUTTON:
                                    self.__current_page = NETWORK_PAGE
                                elif pressed == APPLY_BUTTON:
                                    self.__current_page == NETWORK_PAGE
                                else:
                                    # We want to enter the NIC details ...
                                    warn = "ok"
                                    current_network_config = self.get_tui_field_network_config()
                                    if not self.is_same_network_config (self.original_system_network_config, current_network_config):
                                        self._create_warn_screen()
                                        title = "Confirm NIC Configuration"
                                        message = "Unsaved network changes detected, save and continue to NIC configuration?"
                                        warn = ButtonChoiceWindow(self.screen, title, message)
                                    if warn == "ok":
                                        # apply and continue
                                        self.process_network_config()
                                        self.__current_page = NETWORK_DETAILS_PAGE
                                        self.preset_network_config = None
                                    else:
                                        # Do not apply, return
                                        self.preset_network_config = current_network_config
                            else:
                                self.__current_page = menu_choice
                            if self.net_apply_config == 1:
                                self.net_apply_config = 0
                        elif self.__current_page == NETWORK_DETAILS_PAGE:
                            if pressed == BACK_BUTTON:
                                self.__current_page = NETWORK_PAGE
                            elif self.net_apply_config == 1:
                                self.__current_page = NETWORK_PAGE
                            elif self.__nic_config_failed == 1:
                                self.__current_page = NETWORK_DETAILS_PAGE
                            elif is_managed():
                                self.__current_page = NETWORK_PAGE
                            else:
                               self.__current_page = menu_choice
                        elif self.__current_page == SUPPORT_PAGE:
                           logger.debug("Pressed: " + str(pressed))
                           if pressed == MENU_BUTTON:
                               self.__current_page = STATUS_PAGE
                           else:
                               f = self.log_menu_list.current()
                               screen.popWindow()
                               screen.finish()
                               os.system("/usr/bin/clear;SHELL=/bin/false /usr/bin/less -R " + f)
                        else:
                            self.__current_page = menu_choice
                except Exception, error:
                    self._create_warn_screen()
                    os.remove(lockfile)
                    ButtonChoiceWindow(screen,
                                       "An Exception Has Occurred",
                                       str(error) + "\n" + traceback.format_exc(),
                                       buttons = ["OK"])
                screen.popWindow()
                screen.finish()
                self.restore_console_colors()

if __name__ == "__main__":
    if is_rescue_mode():
        print "Unable to run setup in rescue mode"
        sys.exit(1)
    elif is_booted_from_local_disk() or is_stateless() or "--force" in sys.argv:
        if manual_setup() and "--force" not in sys.argv:
            print "Unable to run setup manually, Run \"exit\" to return to setup"
        else:
            tty = get_ttyname()
            lockfile = "/tmp/ovirt-setup.%s" % tty
            f = open(lockfile, "w").close()
            screen = NodeConfigScreen()
            screen.start()
    else:
        print "Setup must be run after installation and reboot"
        sys.exit(1)
