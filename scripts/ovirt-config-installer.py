#!/usr/bin/python
# ovirt-config-installer - Copyright (C) 2010 Red Hat, Inc.
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
import ovirtnode.password as password
import ovirtnode.install as install
import ovirtnode.storage as storage
from ovirtnode.ovirtfunctions import *
import _snack
import traceback
import os
import dbus
import fcntl
import cracklib
import gudev
import PAM

ABORT_BUTTON = "Abort"
BACK_BUTTON = "Back"
NEXT_BUTTON = "Next"
FINISH_BUTTON = "Finish"
INSTALL_BUTTON = "Install"
REBOOT_BUTTON = "Reboot"
CONTINUE_BUTTON = "Continue"
SHELL_BUTTON = "Drop To Shell"

WELCOME_PAGE = 1
ROOT_STORAGE_PAGE = 3
OTHER_DEVICE_ROOT_PAGE = 4
HOSTVG_STORAGE_PAGE = 5
OTHER_DEVICE_HOSTVG_PAGE = 6
PASSWORD_PAGE = 7
UPGRADE_PAGE = 9
FAILED_PAGE = 11
FINISHED_PAGE = 13
current_password = ""

def pam_conv(auth, query_list):
    global current_password
    resp = []
    for i in range(len(query_list)):
        resp.append((current_password, 0))
    return resp

class NodeInstallScreen:
    def __init__(self, colorset = None):
        self.__current_page = 1
        self.__finished = False
        self.ovirt_defaults_file = "/etc/default/ovirt"
        OVIRT_VARS = parse_defaults()
        _colorset = {
                        "ROOT"          : ("gray",  "magenta"),
                        "BORDER"        : ("magenta", "magenta"),
                        "WINDOW"        : ("magenta", "magenta"),
                        "ACTBUTTON"     : ("blue",  "white"),
                        "BUTTON"        : ("blue",  "white"),
                        "COMPACTBUTTON" : ("black", "magenta"),
                        "LISTBOX"       : ("green",  "red"),
                        "ACTLISTBOX"    : ("blue", "white"),
                        "ACTSELLISTBOX" : ("blue",  "white"),
                        "TEXTBOX"       : ("cyan",  "magenta"),
                        "ENTRY"         : ("cyan", "magenta"),
                        "SHADOW"        : ("magenta",  "magenta"),
                        "LABEL"         : ("brown",  "magenta"),
                        "TITLE"         : ("white",  "blue"),
                        "HELPLINE"      : ("cyan",  "magenta"),
                        "EMPTYSCALE"    : ("white",  "cyan"),
                        "FULLSCALE"     : ("cyan",  "white"),
                        "CHECKBOX"      : ("black",  "red"),
                        "ROOTTEXT"      : ("white",  "blue"),
                         }
        self.__colorset = _colorset
        self.dev_name = ""
        self.dev_model = ""
        self.dev_bus = ""
        self.dev_serial = ""
        self.dev_size = ""
        self.dev_desc = ""
        self.current_password_fail = 0
        self.failed_block_dev = 0
        self.live_disk = "/dev/" + get_live_disk().rstrip('0123456789')
        log("::::live::::\n" + self.live_disk)
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
        color_array[12] = 0x38
        color_array[13] = 0x8f
        color_array[14] = 0xcd
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

    def password_check_callback(self):
        self.valid_password = 0
        if self.root_password_1.value() != "" and self.root_password_2.value() != "":
            if self.root_password_1.value() != self.root_password_2.value():
                self.screen.setColor("BUTTON", "black", "red")
                self.screen.setColor("ACTBUTTON", "blue", "white")
                ButtonChoiceWindow(self.screen, "Password Check", "Passwords Do Not Match", buttons = ['Ok'])
                return
            try:
                cracklib.FascistCheck(self.root_password_1.value())
            except ValueError, e:
                self.screen.setColor("BUTTON", "black", "red")
                self.screen.setColor("ACTBUTTON", "blue", "white")
                ButtonChoiceWindow(self.screen, "Password Check", "You have provided a weak password!\n\nStrong passwords contain a mix of uppercase, lowercase, numeric and \
                punctuation characters. They are six or more characters long and do not\ncontain dictionary words.\n", buttons = ['Ok'])
            finally:
                self.valid_password = 1
        elif self.root_password_1.value() != "" and self.root_password_2.value() == "":
            self.screen.setColor("BUTTON", "black", "red")
            self.screen.setColor("ACTBUTTON", "blue", "white")
            ButtonChoiceWindow(self.screen, "Password Check", "Please Confirm Password", buttons = ['Ok'])
        return

    def current_password_callback(self):
        auth = PAM.pam()
        auth.start("passwd")
        auth.set_item(PAM.PAM_USER, "root")
        global current_password
        current_password = self.current_password.value()
        auth.set_item(PAM.PAM_CONV, pam_conv)
        try:
            auth.authenticate()
        except PAM.error, (resp, code):
            log(resp)
            self.current_password_fail == 1
            return False
        except:
            log("Internal error")
            return False
        else:
            self.current_password_fail == 0
            return True

    def other_device_root_callback(self):
        ret = os.system("test -b " + self.root_device.value())
        if ret != 0:
            self.screen.setColor("BUTTON", "black", "red")
            self.screen.setColor("ACTBUTTON", "blue", "white")
            ButtonChoiceWindow(self.screen, "Storage Check", "Invalid Block Device", buttons = ['Ok'])
            self.reset_screen_colors()
            self.failed_block_dev = 1
        else:
            self.failed_block_dev = 0
        return

    def other_device_hostvg_callback(self):
        for dev in self.hostvg_device.value().split(","):
            ret = os.system("test -b " + dev)
            if ret != 0:
                self.screen.setColor("BUTTON", "black", "red")
                self.screen.setColor("ACTBUTTON", "blue", "white")
                ButtonChoiceWindow(self.screen, "Storage Check", "Invalid Block Device: " + dev, buttons = ['Ok'])
            self.reset_screen_colors()
            self.failed_block_dev = 1
        else:
            self.failed_block_dev = 0
        return

    def menuSpacing(self):
        menu_option = self.menu_list.current()
        if self.menuo < self.menu_list.current():
            if menu_option == 2:
                try:
                    self.menu_list.setCurrent(3)
                    self.menuo = 3
                except:
                    self.menu_list.setCurrent(5)
                    self.menuo = 5
            if menu_option == 4:
                self.menu_list.setCurrent(5)
                self.menuo = 5
            if menu_option == 6:
                self.menu_list.setCurrent(7)
                self.menuo = 7
            if menu_option == 8:
                self.menu_list.setCurrent(9)
                self.menuo = 9
            if menu_option == 10:
                self.menu_list.setCurrent(11)
                self.menuo = 11
            if menu_option == 10:
                self.menu_list.setCurrent(11)
                self.menuo = 11
            # prevent going further down list
            if menu_option == 12:
                self.menu_list.setCurrent(11)
                self.menuo = 11
        elif self.menuo > self.menu_list.current():
            if menu_option == 10:
                self.menu_list.setCurrent(9)
                self.menuo = 9
            if menu_option == 8:
                self.menu_list.setCurrent(7)
                self.menuo = 7
            if menu_option == 6:
                self.menu_list.setCurrent(5)
                self.menuo = 5
            if menu_option == 4:
                self.menu_list.setCurrent(3)
                self.menuo = 3
            if menu_option == 2:
                self.menu_list.setCurrent(1)
                self.menuo = 1

    def get_back_page(self):
        if self.__current_page == ROOT_STORAGE_PAGE:
            self.__current_page = WELCOME_PAGE
        elif self.__current_page == OTHER_DEVICE_ROOT_PAGE:
            self.__current_page = ROOT_STORAGE_PAGE
        elif self.__current_page == OTHER_DEVICE_HOSTVG_PAGE:
            self.__current_page = HOSTVG_STORAGE_PAGE
        elif self.__current_page == HOSTVG_STORAGE_PAGE:
            self.__current_page = ROOT_STORAGE_PAGE
        elif self.__current_page == PASSWORD_PAGE:
            self.__current_page = HOSTVG_STORAGE_PAGE
        elif self.__current_page == UPGRADE_PAGE:
            self.__current_page = WELCOME_PAGE
        return

    def install_page(self):
        elements = Grid(2, 5)
        self.menuo = 1
        self.menu_list = Listbox(16, width = 60, returnExit = 1, border = 0, showCursor = 0, scroll = 0)
        try:
            m_version,m_release = get_media_version_number()
            m_full_ver = m_version + "-" + m_release
        finally:
            if os.path.exists("/dev/HostVG"):
                try:
                    e_version, e_release = get_installed_version_number()
                    e_full_ver = e_version + "-" + e_release
                    if e_version <= m_version:
                        if e_release < m_release:
                            self.menu_list.append(" Upgrade " + e_full_ver + " Version to " + m_full_ver, 3)
                            self.menu_list.append(" ", 4)
                        else:
                            self.menu_list.append(" Install " + PRODUCT_SHORT + " " +  m_full_ver, 1)
                            self.menu_list.append(" ", 2)
                except:
                    log("unable to get_version_numbers for upgrade")
                    pass
            else:
                self.menu_list.append(" Install Hypervisor " + m_full_ver, 1)
            self.menu_list.setCallback(self.menuSpacing)
        elements.setField(self.menu_list, 1,1, anchorLeft = 1)
        return [Label(""), elements]

    def finish_install_page(self):
        elements = Grid(2, 5)
        elements.setField(Label("%s Installation Finished Successfully" %
            PRODUCT_SHORT), 0, 0,padding=(20,5,0,1))
        elements.setField(Label(" "), 0, 1)
        return [Label(""), elements]

    def failed_install_page(self):
        os.system("cat " + OVIRT_TMP_LOGFILE + ">> " + OVIRT_LOGFILE)
        elements = Grid(2, 5)
        elements.setField(Label("%s Installation Failed " %
            PRODUCT_SHORT), 0, 0)
        elements.setField(Label("Check /var/log/ovirt.log for more details"), 0, 1)
        return [Label(""), elements]

    def disk_details_callback(self):
        if self.__current_page == ROOT_STORAGE_PAGE:
            dev = self.root_disk_menu_list.current()
        elif self.__current_page == HOSTVG_STORAGE_PAGE:
            dev = self.hostvg_checkbox.getCurrent()
        if dev == "      Location          Device Name   Size (GB)      Description":
            blank_entry = ",,,,,"
            dev_bus,dev_name,dev_size,dev_desc,dev_serial,dev_model = blank_entry.split(",",5)
        else:
            dev = translate_multipath_device(dev)
            dev_bus,dev_name,dev_size,dev_desc,dev_serial,dev_model = self.disk_dict[dev].split(",",5)
        self.dev_bus_label.setText(dev_bus)
        self.dev_name_label.setText(dev_name)
        self.dev_size_label.setText(dev_size + "GB")
        self.dev_desc_label.setText(dev_desc)
        self.dev_serial_label.setText(dev_serial)
        self.dev_model_label.setText(dev_model)
        return
    def root_disk_page(self):
        elements = Grid(2, 9)
        self.disk_dict = {}
        self.root_disk_menu_list = Listbox(5, width = 70, returnExit = 0, border = 0, scroll = 1)
        self.root_disk_menu_list.setCallback(self.disk_details_callback)
        client = gudev.Client(['block'])
        for device in client.query_by_subsystem("block"):
            dev_name = device.get_property("DEVNAME")
            dev_bus = device.get_property("ID_BUS")
            dev_model = device.get_property("ID_MODEL")
            dev_serial = device.get_property("ID_SERIAL_SHORT")
            dev_desc = device.get_property("ID_SCSI_COMPAT")
            dev_size_cmd = "sfdisk -s %s 2>/dev/null" % dev_name
            dev_size = subprocess.Popen(dev_size_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
            dev_size = dev_size.stdout.read()
            if not device.get_property("ID_CDROM"):
                dev_size = int(dev_size) / 1024 /1024
            if not dev_desc:
                if "/dev/vd" in dev_name:
                    dev_desc = "virtio disk"
                else:
                    dev_desc = "unknown"
            if not device.get_property("ID_CDROM") and not "/dev/dm-" in dev_name:
                dev_name = translate_multipath_device(dev_name)
                self.disk_dict[dev_name] = "%s,%s,%s,%s,%s,%s" % (dev_bus,dev_name,dev_size,dev_desc,dev_serial,dev_model)
        Storage = storage.Storage()
        devs = Storage.get_dev_name()
        dev_names = []
        for dev in devs:
            dev_names.append(dev)
        dev_names.sort()
        self.displayed_disks = {}
        self.valid_disks = []
        for dev in dev_names:
            dev = translate_multipath_device(dev)
            if not self.displayed_disks.has_key(dev):
                if self.disk_dict.has_key(dev) and dev != self.live_disk:
                    dev_bus,dev_name,dev_size,dev_desc,dev_serial,dev_model = self.disk_dict[dev].split(",",5)
                    if dev_bus == "usb":
                        dev_bus = dev_bus.upper()
                    elif dev_bus == "ata" or dev_bus == "scsi" or dev_bus == "cciss":
                        dev_bus = "Local / FibreChannel"
                    else:
                        if "/dev/vd" in dev_name:
                            dev_bus = "      Local        "
                        else:
                            dev_bus = "     "
                    to_rem = len(dev_desc) - 26
                    # if negative pad name space
                    if to_rem < 1:
                        while abs(to_rem) != 0:
                            dev_desc += " "
                            to_rem = to_rem + 1
                    else:
                        dev_desc = dev_desc.rstrip(dev_desc[-to_rem:])
                    self.valid_disks.append(dev_name)
                    dev_name = dev_name.replace("/dev/mapper/","")
                    dev_name = dev_name.replace("  ","_").replace("__","_").replace(" ","")
                    to_rem = len(dev_name) - 25
                    # if negative pad name space
                    if to_rem < 1:
                        while abs(to_rem) != 0:
                            dev_name += " "
                            to_rem = to_rem + 1
                    dev_name = dev_name[:+25]
                    dev_entry = " %6s  %11s  %8sGB" % (dev_bus,dev_name, dev_size)
                    dev_name = translate_multipath_device(dev_name)
                    self.root_disk_menu_list.append(dev_entry, dev)
                    self.valid_disks.append(dev_name)
                    self.displayed_disks[dev] = ""
        self.root_disk_menu_list.append(" Other Device", "OtherDevice")
        self.disk_dict["OtherDevice"] = ",,,,,"
        elements.setField(Label("Please select the disk to use for booting %s"
            % PRODUCT_SHORT), 0,1, anchorLeft = 1)
        elements.setField(Label(" "), 0,2, anchorLeft = 1)
        elements.setField(Label("      Location              Device Name                  Size (GB)"),0,3,anchorLeft =1)
        elements.setField(self.root_disk_menu_list, 0,4)
        disk_grid = Grid(5,8)
        elements.setField(Label("Disk Details"), 0,5, anchorLeft = 1)
        elements.setField(Label(" "), 0,6)
        disk_grid.setField(Label("Device       "),0, 0, anchorLeft = 1)
        disk_grid.setField(Label("Model        "),0, 1, anchorLeft = 1)
        disk_grid.setField(Label("Bus Type     "),0, 2, anchorLeft = 1)
        disk_grid.setField(Label("Serial       "),0, 3, anchorLeft = 1)
        disk_grid.setField(Label("Size         "),0, 4, anchorLeft = 1)
        disk_grid.setField(Label("Description  "),0, 5, anchorLeft = 1)
        # get first disk's info to prepopulate
        i = 0
        for d in self.valid_disks:
            while i < 1:
                dev_bus,dev_name,dev_size,dev_desc,dev_serial,dev_model = self.disk_dict[d].split(",",5)
                i = i + 1
        self.dev_name_label = Label(dev_name)
        self.dev_model_label = Label(dev_model)
        self.dev_bus_label = Label(dev_bus)
        self.dev_serial_label = Label(dev_serial)
        self.dev_size_label = Label(dev_size + "GB")
        self.dev_desc_label = Label(dev_desc)
        disk_grid.setField(self.dev_name_label,1, 0, anchorLeft = 1)
        disk_grid.setField(self.dev_model_label,1, 1, anchorLeft = 1)
        disk_grid.setField(self.dev_bus_label,1, 2, anchorLeft = 1)
        disk_grid.setField(self.dev_serial_label,1, 3, anchorLeft = 1)
        disk_grid.setField(self.dev_size_label,1, 4, anchorLeft = 1)
        disk_grid.setField(self.dev_desc_label,1, 5, anchorLeft = 1)
        elements.setField(disk_grid, 0,7, anchorLeft = 1)
        elements.setField(Label(" "), 0, 8, anchorLeft = 1)
        return [Label(""), elements]

    def hostvg_disk_page(self):
        self.hostvg_checkbox = CheckboxTree(6, width = 70, scroll = 1)
        self.hostvg_checkbox.setCallback(self.disk_details_callback)
        self.hostvg_checkbox.append("      Location            Device Name                Size (GB)", selected = 1)
        elements = Grid(2, 9)
        Storage = storage.Storage()
        devs = Storage.get_dev_name()
        dev_names = []
        for dev in devs:
            dev_names.append(dev)
        dev_names.sort()
        self.displayed_disks = {}
        for dev in dev_names:
            dev = translate_multipath_device(dev)
            if not self.displayed_disks.has_key(dev) and dev != self.live_disk:
                if self.disk_dict.has_key(dev):
                    dev_bus,dev_name,dev_size,dev_desc,dev_serial,dev_model = self.disk_dict[dev].split(",",5)
                    if dev_bus == "usb":
                        dev_bus = dev_bus.upper()
                    elif dev_bus == "ata" or dev_bus == "scsi" or dev_bus == "cciss":
                        dev_bus = "Local / FibreChannel"
                    else:
                        if "/dev/vd" in dev_name:
                            dev_bus = "      Local        "

                        else:
                            dev_bus = "     "
                    to_rem = len(dev_desc) - 26
                    # if negative pad name space
                    if to_rem < 1:
                      while abs(to_rem) != 0:
                          dev_desc += " "
                          to_rem = to_rem + 1
                    else:
                        dev_desc = dev_desc.rstrip(dev_desc[-to_rem:])
                    if dev_name == self.root_disk_menu_list.current():
                        select_status = 1
                    else:
                        select_status = 0
                    # strip all "/dev/*/" references and leave just basename
                    dev_name = dev_name.replace("/dev/mapper/","")
                    dev_name = dev_name.replace("/dev/","")
                    dev_name = dev_name.replace("  ","_").replace("__","_").replace(" ","")
                    to_rem = len(dev_name) - 25
                    # if negative pad name space
                    if to_rem < 1:
                        while abs(to_rem) != 0:
                            dev_name += " "
                            to_rem = to_rem + 1
                    dev_name = dev_name[:+25]
                    dev_entry = " %6s %10s  %7sGB" % (dev_bus,dev_name, dev_size)
                    self.hostvg_checkbox.addItem(dev_entry, (0, snackArgs['append']), item = dev, selected = select_status)
                    self.displayed_disks[dev] = ""
        if self.root_disk_menu_list.current() == "OtherDevice":
            select_status = 1
        else:
            select_status = 0
        self.hostvg_checkbox.addItem(" Other Device", (0, snackArgs['append']), item = "OtherDevice", selected = select_status)
        elements.setField(Label("Please select the disk(s) to use for installation of %s" % PRODUCT_SHORT), 0,1, anchorLeft = 1)
        elements.setField(self.hostvg_checkbox, 0,3)
        elements.setField(Label("Disk Details"), 0,4, anchorLeft = 1)
        elements.setField(Label(" "), 0,5)
        disk_grid = Grid(2,8)
        disk_grid.setField(Label("Device       "),0, 0, anchorLeft = 1)
        disk_grid.setField(Label("Model        "),0, 1, anchorLeft = 1)
        disk_grid.setField(Label("Bus Type     "),0, 2, anchorLeft = 1)
        disk_grid.setField(Label("Serial       "),0, 3, anchorLeft = 1)
        disk_grid.setField(Label("Size         "),0, 4, anchorLeft = 1)
        disk_grid.setField(Label("Description  "),0, 5, anchorLeft = 1)
        # get first disk's info to prepopulate
        i = 0
        for d in self.valid_disks:
            while i < 1:
                dev_bus,dev_name,dev_size,dev_desc,dev_serial,dev_model = self.disk_dict[d].split(",",5)
                self.hostvg_checkbox.setCurrent(self.root_disk_menu_list.current())
                i = i + 1
        self.dev_name_label = Label(dev_name)
        self.dev_model_label = Label(dev_model)
        self.dev_bus_label = Label(dev_bus)
        self.dev_serial_label = Label(dev_serial)
        self.dev_size_label = Label(dev_size + "GB")
        self.dev_desc_label = Label(dev_desc)
        disk_grid.setField(self.dev_name_label,1, 0, anchorLeft = 1)
        disk_grid.setField(self.dev_model_label,1, 1, anchorLeft = 1)
        disk_grid.setField(self.dev_bus_label,1, 2, anchorLeft = 1)
        disk_grid.setField(self.dev_serial_label,1, 3, anchorLeft = 1)
        disk_grid.setField(self.dev_size_label,1, 4, anchorLeft = 1)
        disk_grid.setField(self.dev_desc_label,1, 5, anchorLeft = 1)
        elements.setField(disk_grid, 0,6, anchorLeft = 1)
        elements.setField(Label(" "), 0, 7, anchorLeft = 1)
        return [Label(""), elements]

    def other_device_root_page(self):
        elements = Grid(2, 8)
        elements.setField(Label("Please enter the disk to use for booting %s" % PRODUCT_SHORT), 0, 0, anchorLeft = 1)
        self.root_device = Entry(35)
        self.root_device.setCallback(self.other_device_root_callback)
        elements.setField(self.root_device, 0,1, anchorLeft = 1, padding = (0,1,0,1))
        return [Label(""), elements]

    def other_device_hostvg_page(self):
        elements = Grid(2, 8)
        elements.setField(Label("Please select the disk(s) to use for installation of %s" % PRODUCT_SHORT), 0, 0, anchorLeft = 1)
        elements.setField(Label("Enter multiple entries separated by commas"), 0, 1, anchorLeft = 1)
        self.hostvg_device = Entry(35)
        self.hostvg_device.setCallback(self.other_device_hostvg_callback)
        elements.setField(self.hostvg_device, 0, 2, anchorLeft = 1, padding = (0,1,0,1))
        return [Label(""), elements]

    def password_page(self):
        elements = Grid(2, 8)
        pw_elements = Grid (3,3)
        elements.setField(Label("Require a password for local console access?"), 0, 0, anchorLeft = 1)
        elements.setField(Label(" "), 0, 1, anchorLeft = 1)
        elements.setField(Label(" "), 0, 4)
        pw_elements.setField(Label("Password: "), 0, 1, anchorLeft = 1)
        pw_elements.setField(Label("Confirm Password: "), 0, 2, anchorLeft = 1)
        self.root_password_1 = Entry(15,password = 1)
        self.root_password_1.setCallback(self.password_check_callback)
        self.root_password_2 = Entry(15,password = 1)
        self.root_password_2.setCallback(self.password_check_callback)
        pw_elements.setField(self.root_password_1, 1,1)
        pw_elements.setField(self.root_password_2, 1,2)
        elements.setField(pw_elements, 0, 5, anchorLeft = 1)
        elements.setField(Label(" "), 0, 6)
        return [Label(""), elements]

    def upgrade_page(self):
        elements = Grid(2, 8)
        pw_elements = Grid (3,8)
        self.current_password = Entry(15,password = 1)
        self.root_password_1 = Entry(15,password = 1)
        self.root_password_2 = Entry(15,password = 1)

        if pwd_set_check("root"):
            elements.setField(Label(" "), 0, 1, anchorLeft = 1)
            elements.setField(Label("To reset password, please enter the current password "), 0, 2, anchorLeft = 1)
            pw_elements.setField(Label("Current Password: "), 0, 1, anchorLeft = 1)
            self.current_password.setCallback(self.current_password_callback)
            pw_elements.setField(self.current_password, 1,1)
        elements.setField(Label("Password for local console access"), 0, 3, anchorLeft = 1)
        elements.setField(Label(" "), 0, 4)
        pw_elements.setField(Label("Password: "), 0, 2, anchorLeft = 1)
        pw_elements.setField(Label("Confirm Password: "), 0, 3, anchorLeft = 1)
        self.root_password_1.setCallback(self.password_check_callback)
        self.root_password_2.setCallback(self.password_check_callback)
        pw_elements.setField(self.root_password_1, 1,2)
        pw_elements.setField(self.root_password_2, 1,3)
        elements.setField(pw_elements, 0, 5, anchorLeft = 1)
        elements.setField(Label(" "), 0, 6)
        return [Label(""), elements]

    def get_elements_for_page(self, screen, page):
        if page == WELCOME_PAGE:
            return self.install_page()
        if page == ROOT_STORAGE_PAGE:
            return self.root_disk_page()
        if page == OTHER_DEVICE_ROOT_PAGE:
            return self.other_device_root_page()
        if page == OTHER_DEVICE_HOSTVG_PAGE:
            return self.other_device_hostvg_page()
        if page == HOSTVG_STORAGE_PAGE:
            return self.hostvg_disk_page()
        if page == PASSWORD_PAGE:
            return self.password_page()
        if page == FAILED_PAGE:
            return self.failed_install_page()
        if page == UPGRADE_PAGE:
            return self.upgrade_page()
        if page == FINISHED_PAGE:
            return self.finish_install_page()
        return []

    def install_node(self):
        self.__current_page = FAILED_PAGE
        gridform = GridForm(self.screen, "", 2, 2)
        dev_name = self.storage_init.replace("/dev/mapper/","").replace("  ","_").replace("__","_").replace(" ","")
        gridform.add(Label("Partitioning and Creating File Systems on: " + dev_name ), 0, 0, anchorLeft = 1)
        progress_bar = Scale(50,100)
        progress_bar.set(25)
        gridform.add(progress_bar, 0, 1)
        gridform.draw()
        self.screen.refresh()
        config_storage = storage.Storage()
        storage_setup = config_storage.perform_partitioning()
        if storage_setup:
            progress_bar.set(50)
            gridform = GridForm(self.screen, "", 2, 2)
            gridform.add(Label("Setting Root Password"), 0, 0, anchorLeft = 1)
            gridform.add(progress_bar, 0, 1)
            gridform.draw()
            self.screen.refresh()
            root_pw_set = password.set_password(self.root_password_1.value(), "root")
            if root_pw_set:
                admin_pw_set = password.set_password(self.root_password_1.value(), "admin")
                if admin_pw_set:
                    gridform.add(progress_bar, 0, 1)
                    gridform.draw()
                    self.screen.refresh()
                    progress_bar.set(75)
                    gridform = GridForm(self.screen, "", 2, 2)
                    gridform.add(Label("Installing Bootloader Configuration on: " + self.storage_init ), 0, 0, anchorLeft = 1)
                    gridform.add(progress_bar, 0, 1)
                    gridform.draw()
                    self.screen.refresh()
                    boot_setup = install.ovirt_boot_setup()
                    if boot_setup:
                        progress_bar.set(100)
                        self.__current_page = FINISHED_PAGE

    def upgrade_node(self):
        gridform = GridForm(self.screen, "", 2, 2)
        gridform.add(Label("Upgrading Hypervisor"), 0, 0, anchorLeft = 1)
        progress_bar = Scale(50,100)
        progress_bar.set(75)
        gridform.add(progress_bar, 0, 1)
        gridform.draw()
        self.screen.refresh()
        boot_setup = install.ovirt_boot_setup()
        progress_bar.set(100)
        self.__current_page = FINISHED_PAGE
        return

    def start(self):
        self.set_console_colors()
        active = True
        while active and (self.__finished == False):
            # reread defaults every refresh
            OVIRT_VARS = parse_defaults()
            self.screen = SnackScreen()
            screen = self.screen
            for item in self.__colorset.keys():
                colors = self.__colorset.get(item)
                screen.setColor(item, colors[0], colors[1])
            screen.pushHelpLine(" ")
            screen.drawRootText(1,0, "".ljust(80))
            screen.drawRootText(1,1, "   %s" % PRODUCT_SHORT.ljust(77))
            screen.drawRootText(1,2, "".ljust(80))
            elements = self.get_elements_for_page(screen, self.__current_page)
            self.gridform = GridForm(screen, "", 8, 8)
            gridform = self.gridform
            content = Grid(1, len(elements) + 3) # extra = button bar + padding row
            current_element = 1
            for element in elements:
                # set the title of the page
                content.setField(element, 0, current_element, anchorLeft = 1)
                current_element += 1
            (fullwidth, fullheight) = _snack.size()
            current_element += 1
            buttons = []
            if self.__current_page == FINISHED_PAGE:
                buttons.append(["Reboot", REBOOT_BUTTON])
            if self.__current_page != FINISHED_PAGE:
                buttons.append(["Abort", ABORT_BUTTON])
            if self.__current_page != WELCOME_PAGE and self.__current_page != FAILED_PAGE and self.__current_page != FINISHED_PAGE:
                buttons.append(["Back", BACK_BUTTON])
            if self.__current_page == HOSTVG_STORAGE_PAGE or self.__current_page == ROOT_STORAGE_PAGE or self.__current_page == UPGRADE_PAGE:
                buttons.append(["Continue", CONTINUE_BUTTON])
            if self.__current_page == OTHER_DEVICE_ROOT_PAGE or self.__current_page == OTHER_DEVICE_HOSTVG_PAGE:
                buttons.append(["Continue", CONTINUE_BUTTON])
            if self.__current_page == PASSWORD_PAGE:
                buttons.append(["Install", INSTALL_BUTTON])
            if self.__current_page == FAILED_PAGE:
                buttons.append(["Drop To Shell", SHELL_BUTTON])
            buttonbar = ButtonBar(screen, buttons, compact = 1)
            buttongrid = Grid(1,1)
            if self.__current_page == FINISHED_PAGE:
                buttongrid.setField(buttonbar, 0, 0, padding = (14,0,0,0))
                buttongrid_anchor = 0
            else:
                buttongrid.setField(buttonbar, 0, 0, anchorLeft = 1)#, growx = 0)
                buttongrid_anchor = 1

            current_element += 1
            gridform.add(content, 2, 0, anchorTop = 1)
            if self.__current_page == FINISHED_PAGE:
                gridform.add(buttongrid, 2, 1, anchorLeft = buttongrid_anchor, padding = (6,0,0,0))
            else:
                gridform.add(buttongrid, 2, 1, anchorLeft = buttongrid_anchor)
            gridform.addHotKey("F2")
            gridform.addHotKey("F3")
            try:
                (top, left) = (1, 4)
                result = gridform.runOnce(top, left)
                pressed = buttonbar.buttonPressed(result)
                menu_choice = self.menu_list.current()
                self.screen.setColor("BUTTON", "black", "red")
                self.screen.setColor("ACTBUTTON", "blue", "white")
                if result == "F2" or pressed == SHELL_BUTTON:
                    screen.popWindow()
                    screen.finish()
                    os.system("/usr/bin/clear;/bin/bash")
                elif pressed == ABORT_BUTTON:
                    log("Exiting")
                    abort = ButtonChoiceWindow(self.screen, "Abort Installation", "", buttons = ['Back','Reboot','Shutdown'])
                    if abort == "reboot":
                        os.system("/usr/bin/clear;reboot")
                    elif abort == "shutdown":
                        os.system("/usr/bin/clear;halt")
                elif pressed == REBOOT_BUTTON:
                    screen.finish()
                    os.system("/usr/bin/clear;/sbin/reboot")
                elif pressed == BACK_BUTTON:
                    self.get_back_page()
                elif not result == "F2":
                    if self.__current_page == WELCOME_PAGE:
                        if menu_choice == 1:
                            self.__current_page = ROOT_STORAGE_PAGE
                        elif menu_choice == 3:
                            self.__current_page = UPGRADE_PAGE
                    elif self.__current_page == ROOT_STORAGE_PAGE:
                            self.storage_init = self.root_disk_menu_list.current()
                            if self.storage_init == "OtherDevice":
                                self.__current_page = OTHER_DEVICE_ROOT_PAGE
                            else:
                                augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_INIT", '"' + self.storage_init + '"')
                                augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_ROOT_INSTALL", '"y"')
                                self.__current_page =  HOSTVG_STORAGE_PAGE
                    elif self.__current_page == OTHER_DEVICE_ROOT_PAGE:
                        if self.failed_block_dev == 0:
                            self.storage_init = self.root_device.value()
                            augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_INIT", '"' + self.storage_init + '"')
                            augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_ROOT_INSTALL", '"y"')
                            self.__current_page = HOSTVG_STORAGE_PAGE
                        else:
                            self.__current_page = OTHER_DEVICE_ROOT_PAGE
                    elif self.__current_page == HOSTVG_STORAGE_PAGE:
                        self.hostvg_init = self.hostvg_checkbox.getSelection()
                        if not self.hostvg_checkbox.getSelection():
                            ButtonChoiceWindow(self.screen, "HostVG Storage Selection", "You must select a HostVG device", buttons = ['Ok'])
                            self.__current_page = HOSTVG_STORAGE_PAGE
                        else:
                            if "OtherDevice" in self.hostvg_init:
                                self.__current_page = OTHER_DEVICE_HOSTVG_PAGE
                            else:
                                hostvg_list = ""
                                for dev in self.hostvg_init:
                                    hostvg_list += dev + ","
                                augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_INIT", '"' + self.storage_init + "," + hostvg_list + '"')
                                self.__current_page = PASSWORD_PAGE
                                if check_existing_hostvg(""):
                                    self.screen.setColor("BUTTON", "black", "red")
                                    self.screen.setColor("ACTBUTTON", "blue", "white")
                                    msg = "Existing HostVG Detected on %s, Overwrite?" % check_existing_hostvg("")
                                    warn = ButtonChoiceWindow(self.screen, "HostVG Check", msg)
                                    self.reset_screen_colors()
                                    if warn != "ok":
                                        self.__current_page = HOSTVG_STORAGE_PAGE
                                        augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_INIT", '"' + self.storage_init + "," + hostvg_list + '"')
                    elif self.__current_page == OTHER_DEVICE_HOSTVG_PAGE:
                        self.hostvg_init = self.hostvg_device.value()
                        hostvg_list = ""
                        for dev in self.hostvg_init.split(","):
                            if dev != self.storage_init:
                                hostvg_list += dev + ","
                        augtool("set", "/files/" + OVIRT_DEFAULTS + "/OVIRT_INIT", '"' + self.storage_init + "," + hostvg_list + '"')
                        self.__current_page = PASSWORD_PAGE
                    elif self.__current_page == UPGRADE_PAGE:
                        if not self.current_password_fail == 1:
                            self.upgrade_node()
                    elif self.__current_page == PASSWORD_PAGE:
                        if self.valid_password == 1:
                            self.install_node()
                        else:
                            ButtonChoiceWindow(self.screen, "Password Check", "You must enter a valid password", buttons = ['Ok'])
                            self.__current_page = PASSWORD_PAGE
            except Exception, error:
                self.screen.setColor("BUTTON", "black", "red")
                self.screen.setColor("ACTBUTTON", "blue", "white")
                ButtonChoiceWindow(screen,
                                   "An Exception Has Occurred",
                                   str(error) + "\n" + traceback.format_exc(),
                                   buttons = ["OK"])
            screen.popWindow()
            screen.finish()
            self.restore_console_colors()

if __name__ == "__main__":
   screen = NodeInstallScreen()
   screen.start()

