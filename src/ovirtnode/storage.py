#!/usr/bin/python
# storage.py - Copyright (C) 2010 Red Hat, Inc.
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
import os
import sys
import time
import re
import gudev
import logging
import subprocess
import shlex
from ovirtnode.iscsi import set_iscsi_initiator

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self):
        logger = logging.getLogger(_functions.PRODUCT_SHORT)
        logger.propagate = False
        OVIRT_VARS = _functions.parse_defaults()
        self.overcommit = 0.5
        self.BOOT_SIZE = 512
        self.ROOT_SIZE = 512
        self.CONFIG_SIZE = 5
        self.LOGGING_SIZE = 2048
        self.EFI_SIZE = 256
        self.SWAP_SIZE = 0
        self.MIN_SWAP_SIZE = 5
        self.MIN_LOGGING_SIZE = 5
        self.SWAP2_SIZE = 0
        self.DATA2_SIZE = 0
        self.BOOTDRIVE = ""
        self.HOSTVGDRIVE = ""
        self.APPVGDRIVE = []
        self.ISCSIDRIVE = ""
        # -1 indicates data partition should use remaining disk
        self.DATA_SIZE = -1
        # gpt or msdos partition table type
        self.LABEL_TYPE = "gpt"
        if "OVIRT_INIT" in OVIRT_VARS:
            _functions.OVIRT_VARS["OVIRT_INIT"] = \
                                _functions.OVIRT_VARS["OVIRT_INIT"].strip(",")
            if "," in _functions.OVIRT_VARS["OVIRT_INIT"]:
                disk_count = 0
                init = _functions.OVIRT_VARS["OVIRT_INIT"].strip(",").split(",")
                for disk in init:
                    skip = False
                    translated_disk = _functions.translate_multipath_device(disk)
                    if disk_count < 1:
                        self.ROOTDRIVE = translated_disk
                        if len(init) == 1:
                            self.HOSTVGDRIVE = translated_disk
                        disk_count = disk_count + 1
                    else:
                        for hostvg in self.HOSTVGDRIVE.split(","):
                            if hostvg == translated_disk:
                                skip = True
                                break
                        if not skip:
                            self.HOSTVGDRIVE += ("%s," % translated_disk) \
                                if translated_disk else ""
            else:
                self.ROOTDRIVE = _functions.translate_multipath_device(
                                    _functions.OVIRT_VARS["OVIRT_INIT"])
                self.HOSTVGDRIVE = _functions.translate_multipath_device(
                                    _functions.OVIRT_VARS["OVIRT_INIT"])
            if _functions.is_iscsi_install():
                logger.info(self.BOOTDRIVE)
                logger.info(self.ROOTDRIVE)
                self.BOOTDRIVE = _functions.translate_multipath_device( \
                                                                self.ROOTDRIVE)
        if "OVIRT_OVERCOMMIT" in OVIRT_VARS:
            self.overcommit = OVIRT_VARS["OVIRT_OVERCOMMIT"]
        if "OVIRT_VOL_SWAP_SIZE" in OVIRT_VARS:
            if int(OVIRT_VARS["OVIRT_VOL_SWAP_SIZE"]) < self.MIN_SWAP_SIZE:
                logger.error("Swap size is smaller than minimum required + "
                             "size of: %s" % self.MIN_SWAP_SIZE)
                print ("\n\nSwap size is smaller than minimum required " +
                      "size of: %s" % self.MIN_SWAP_SIZE)
                #return False
                sys.exit(1)
            else:
                self.SWAP_SIZE = _functions.OVIRT_VARS["OVIRT_VOL_SWAP_SIZE"]
        else:
            self.SWAP_SIZE = _functions.calculate_swap_size( \
                                 float(self.overcommit))
        for i in ['OVIRT_VOL_BOOT_SIZE', 'OVIRT_VOL_ROOT_SIZE',
                  'OVIRT_VOL_CONFIG_SIZE', 'OVIRT_VOL_LOGGING_SIZE',
                  'OVIRT_VOL_DATA_SIZE', 'OVIRT_VOL_SWAP2_SIZE',
                  'OVIRT_VOL_DATA2_SIZE', 'OVIRT_VOL_EFI_SIZE']:
            i_short = i.replace("OVIRT_VOL_", "MIN_")
            if not i_short in self.__dict__:
                i_short = i_short.replace("MIN_", "")
            if i in OVIRT_VARS:
                if int(OVIRT_VARS[i]) < int(self.__dict__[i_short]):
                    logger.error(("%s is smaller than minimum required size " +
                                 "of: %s") % (i, self.__dict__[i_short]))
                    print (("\n%s is smaller than minimum required size of: " +
                          "%s") % (i, self.__dict__[i_short]))
                    #return False
                logger.info(("Setting value for %s to %s " %
                           (self.__dict__[i_short], _functions.OVIRT_VARS[i])))
                i_short = i_short.replace("MIN_", "")
                self.__dict__[i_short] = int(OVIRT_VARS[i])
            else:
                logger.info("Using default value for: %s" % i_short)
        self.RootBackup_end = self.ROOT_SIZE * 2 + self.EFI_SIZE
        self.Root_end = self.EFI_SIZE + self.ROOT_SIZE

        if "OVIRT_INIT_APP" in OVIRT_VARS:
            if self.SWAP2_SIZE != 0 or self.DATA2_SIZE != 0:
                for drv in _functions.OVIRT_VARS["OVIRT_INIT_APP"].split(","):
                    DRIVE = _functions.translate_multipath_device(drv)
                    self.APPVGDRIVE.append(DRIVE)
        else:
            if self.SWAP2_SIZE != 0 or self.DATA2_SIZE != 0:
                logger.error("Missing device parameter for AppVG: " +
                             "unable to partition any disk")
                #return False

    def cross_check_host_app(self):
        logger.debug("Doing cross-check (if a device is a member of appvg " +
                     "and hostvg)")
        hostvg_drives = self.HOSTVGDRIVE.strip(",").split(",")
        if self.ROOTDRIVE:
            hostvg_drives.append(self.ROOTDRIVE)
        # Translate to DM name as APPVG is using it
        hostvg_drives = [_functions.translate_multipath_device(drv)
                         for drv in hostvg_drives]
        return Storage._xcheck_vgs(hostvg_drives, self.APPVGDRIVE)

    @staticmethod
    def _xcheck_vgs(hostvg_drives, appvg_drives):
        """Semi-internal method to allow a better testing

        APPVG and HOSTVG do not overlap:
        >>> Storage._xcheck_vgs(["/dev/sda"], ["/dev/sdb"])
        True

        APPVG and HOSTVG do overlap (sda):
        >>> Storage._xcheck_vgs(["sda"], ["sda", "sdb"])
        False

        APPVG and HOSTVG do not overlap:
        >>> Storage._xcheck_vgs([], [])
        True
        """
        assert type(hostvg_drives) is list
        assert type(appvg_drives) is list
        drives_in_both = set.intersection(set(hostvg_drives),
                                          set(appvg_drives))
        if drives_in_both:
            logger.warning("The following drives are members of " +
                           "APPVG and HOSTVG: %s" % drives_in_both)
            return False
        return True

    def get_drive_size(self, drive):
        logger.debug("Getting Drive Size For: %s" % drive)
        size_cmd = "sfdisk -s " + drive + " 2>/dev/null"
        size_popen = _functions.subprocess_closefds(size_cmd, shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        size, size_err = size_popen.communicate()
        size = size.strip()
        size = int(int(size) / 1024)
        logger.debug(size)
        return size

    def _lvm_name_for_disk(self, disk):
        name = None
        cmd = "lvm pvs --noheadings --nameprefixes --unquoted -o pv_name,vg_name '%s' 2> /dev/null" % disk
        lines = str(_functions.passthrough(cmd)).strip().split("\n")
        if len(lines) > 1:
            logger.warning("More than one PV for disk '%s' found: %s" % (disk,
                                                                         lines))
        for line in lines:
            lvm2_vars = dict([tuple(e.split("=", 1)) for e \
                              in shlex.split(line)])
            if "LVM2_PV_NAME" in lvm2_vars:
                name = lvm2_vars["LVM2_PV_NAME"]
            else:
                logger.debug("Found line '%s' but no LVM2_PV_NAME" % line)
        return name

    def wipe_lvm_on_disk(self, _devs):
        devs = set(_devs.split(","))
        logger.debug("Considering to wipe LVM on: %s / %s" % (_devs, devs))
        for dev in devs:
            logger.debug("Considering device '%s'" % dev)
            if not os.path.exists(dev):
                logger.info("'%s' is no device, let's try the next one." % dev)
                continue
            part_delim = "p"
            # FIXME this should be more intelligent
            if "/dev/sd" in dev or "dev/vd" in dev:
                part_delim = ""
            vg_cmd = ("pvs -o vg_uuid --noheadings \"%s\" \"%s%s\"[0-9]* " +
                      "2>/dev/null | sort -u") % (dev, dev, part_delim)
            vg_proc = _functions.passthrough(vg_cmd, log_func=logger.debug)
            vgs_on_dev = vg_proc.stdout.split()
            for vg in vgs_on_dev:
                name = self._lvm_name_for_disk(dev)
                pvs_cmd = ("pvs -o pv_name,vg_uuid --noheadings | " +
                           "grep \"%s\" | egrep -v -q \"%s" % (vg, name))
                for fdev in devs:
                    pvs_cmd += "|%s%s[0-9]+|%s" % (fdev, part_delim, fdev)
                    name = self._lvm_name_for_disk(fdev)
                    pvs_cmd += "|%s%s[0-9]+|%s" % (name, part_delim, name)
                pvs_cmd += "\""
                remaining_pvs = _functions.system(pvs_cmd)
                if remaining_pvs:
                    logger.error("The volume group \"%s\" spans multiple " +
                                 "disks.") % vg
                    logger.error("This operation cannot complete.  " +
                                 "Please manually cleanup the storage using " +
                                 "standard disk tools.")
                    return False
                _functions.wipe_volume_group(vg)
        return True

    def reread_partitions(self, drive):
        logger.debug("Rereading pt")
        _functions.system("sync")
        if "dev/mapper" in drive:
            # kpartx -a -p p "$drive"
            # XXX fails with spaces in device names (TBI)
            # ioctl(3, DM_TABLE_LOAD, 0x966980) = -1 EINVAL (Invalid argument)
            # create/reload failed on 0QEMU   QEMU HARDDISK  drive-scsi0-0-0p1
            _functions.system("kpartx -a '%s'" % drive)
            _functions.system("partprobe")
            # partprobe fails on cdrom:
            # Error: Invalid partition table - recursive partition on /dev/sr0.
            _functions.system("service multipathd reload")
            _functions.system("multipath -r &>/dev/null")
            # wait for device to exit
            i = 0
            timeout = 15
            while not os.path.exists(drive):
                logger.error(drive + " is not available, waiting %s more " +
                             "secs") % (timeout - i)
                i = i + i
                time.sleep(1)
                if i == timeout:
                    logger.error("Timed out waiting for: %s" % drive)
                    return False
        else:
            _functions.passthrough("blockdev --rereadpt \"%s\"" % drive, \
                                   logger.debug)

    def get_sd_name(self, id):
        device_sys_cmd = "grep -H \"^%s$\" /sys/block/*/dev | cut -d: -f1" % id
        device_sys = _functions.subprocess_closefds(device_sys_cmd, shell=True,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
        device_sys_output, device_sys_err = device_sys.communicate()
        device_sys_output = device_sys_output.strip()
        if not device_sys_output is "":
            device = os.path.basename(os.path.dirname(device_sys_output))
            return device

    # gets the dependent block devices for multipath devices
    def get_multipath_deps(self, mpath_device):
        deplist = ""
        #get dependencies for multipath device
        deps_cmd = "dmsetup deps -u mpath-%s | sed 's/^.*: //' \
        | sed 's/, /:/g' | sed 's/[\(\)]//g'" % mpath_device
        deps = _functions.subprocess_closefds(deps_cmd, shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        deps_output, deps_err = deps.communicate()
        for dep in deps_output.split():
            device = self.get_sd_name(dep)
            if device is not None:
                deplist = "%s %s" % (device, deplist)
        return deplist

    # Find a usable/selected storage device.
    # If there are none, give a diagnostic and return nonzero.
    # If there is just one, e.g., /dev/sda, treat it as selected (see below).
    # and return 0.  If there are two or more, make the user select one
    # or decline.  Upon decline, return nonzero. Otherwise, print the
    # selected name, then return 0.
    # Sample output: /dev/sda
    def get_dev_name(self):
        devices = []
        # list separator
        for d in os.listdir("/sys/block/"):
            if re.match("^[hsv]+d", d):
                devices.append("/dev/%s" % d)
            byid_list_cmd = ("find /dev/disk/by-id -mindepth 1 -not -name " +
                            "'*-part*' 2>/dev/null")
            byid_list = _functions.subprocess_closefds(byid_list_cmd,
                                            shell=True,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
            byid_list_output, byid_list_err = byid_list.communicate()
        for d in byid_list_output.split():
            d = os.readlink(d)
            d_basename = os.path.basename(d)
            udev_cmd = ("udevadm info --name=/dev/" + d_basename +
                        " --query=property | grep -q ^ID_BUS: &>>/dev/null")
            if _functions.system_closefds(udev_cmd):
                devices.append("/dev/%s" % d_basename)
        # FIXME: workaround for detecting cciss devices
        if os.path.exists("/dev/cciss"):
            for d in os.listdir("/dev/cciss"):
                if not re.match("p[0-9]+\$", d):
                    devices.append("/dev/cciss/%s" % d)

        # include multipath devices
        devs_to_remove = ""
        multipath_list_cmd = "dmsetup ls --target=multipath | cut -f1"
        multipath_list = _functions.subprocess_closefds(multipath_list_cmd,
                                             shell=True,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT)
        multipath_list_output, multipath_list_err = multipath_list.communicate()

        for d in multipath_list_output.split():
            devices.append("/dev/mapper/%s" % d)
            sd_devs = ""
            sd_devs = self.get_multipath_deps(d)

            dm_dev_cmd = ("multipath -ll \"%s\" | grep \"%s\" | " +
                          "sed -r 's/^.*(dm-[0-9]+ ).*$/\\1/'") % (d, d)
            dm_dev = _functions.subprocess_closefds(dm_dev_cmd, shell=True,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
            dm_dev_output, dm_dev_err = dm_dev.communicate()
            devs_to_remove = ("%s %s %s" % (devs_to_remove, sd_devs,
                                          dm_dev_output))
        # Remove /dev/sd* devices that are part of a multipath device
        dev_list = []
        for d in devices:
            if (os.path.basename(d) not in devs_to_remove and
                    not "/dev/dm-" in d):
                dev_list.append(d)

        for dev in dev_list:
            if dev_list.count(dev) > 1:
                count = dev_list.count(dev)
                while (count > 1):
                    dev_list.remove(dev)
                    count = count - 1
        return dev_list

    def get_udev_devices(self):
        self.disk_dict = {}
        client = gudev.Client(['block'])
        for device in client.query_by_subsystem("block"):
            dev_name = device.get_property("DEVNAME")
            dev_bus = device.get_property("ID_BUS")
            dev_model = device.get_property("ID_MODEL")
            dev_serial = device.get_property("ID_SERIAL")
            dev_desc = device.get_property("ID_SCSI_COMPAT")
            dev_size_cmd = "sfdisk -s %s 2>/dev/null" % dev_name
            dev_size_popen = _functions.subprocess_closefds(dev_size_cmd, shell=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            dev_size, dev_size_err = dev_size_popen.communicate()
            size_failed = 0
            if not device.get_property("ID_CDROM"):
                try:
                    dev_size = int(dev_size) / 1024 / 1024
                except:
                    size_failed = 1
            if not dev_desc:
                if "/dev/vd" in dev_name:
                    dev_desc = "virtio disk"
                elif dev_serial is not None:
                    dev_desc = dev_serial
                else:
                    dev_desc = "unknown"
            if (not device.get_property("ID_CDROM") and
                    not "/dev/dm-" in dev_name and
                    not "/dev/loop" in dev_name and size_failed == 0):
                dev_name = _functions.translate_multipath_device(dev_name)
                busmap = { \
                    "usb": "USB Device          ", \
                    "ata": "Local / FibreChannel", \
                    "scsi": "Local / FibreChannel", \
                    "cciss": "CCISS               " \
                }
                if dev_bus in busmap:
                    dev_bus = busmap[dev_bus]
                elif "/dev/vd" in dev_name:
                    dev_bus = "Local (Virtio)      "
                else:
                    dev_bus = "                    "

                self.disk_dict[dev_name] = "%s,%s,%s,%s,%s,%s" % (dev_bus,
                                            dev_name, dev_size, dev_desc,
                                            dev_serial, dev_model)
        devs = self.get_dev_name()
        return (sorted(devs), self.disk_dict)

    def create_hostvg(self):
        logger.info("Creating LVM partition")
        self.physical_vols = []
        for drv in self.HOSTVGDRIVE.strip(",").split(","):
            drv = _functions.translate_multipath_device(drv)
            if drv != "":
                if self.ROOTDRIVE == drv and not _functions.is_iscsi_install():
                    self.reread_partitions(self.ROOTDRIVE)
                    parted_cmd = ("parted \"" + drv + "\" -s \"mkpart " +
                                  "primary ext2 " + str(self.RootBackup_end) +
                                  "M -1\"")
                    logger.debug(parted_cmd)
                    _functions.system(parted_cmd)
                    hostvgpart = "4"
                elif self.BOOTDRIVE == drv:
                    parted_cmd = ("parted \"" + drv + "\" -s \"mkpart " +
                                  "primary ext2 " + str(self.boot_size_si * 2) +
                                  " -1\"")
                    logger.debug(parted_cmd)
                    _functions.system(parted_cmd)
                    hostvgpart = "3"
                    self.ROOTDRIVE = self.BOOTDRIVE
                elif self.ISCSIDRIVE == drv:
                    parted_cmd = ("parted \"" + drv + "\" -s \"mkpart " +
                                  "primary ext2 " + str(self.ROOT_SIZE * 2) +
                                  " -1\"")
                    logger.debug(parted_cmd)
                    _functions.system(parted_cmd)
                    hostvgpart = "3"
                else:
                    _functions.system("parted \"" + drv + "\" -s \"mklabel " +
                            self.LABEL_TYPE + "\"")
                    parted_cmd = ("parted \"" + drv + "\" -s \"mkpart " +
                                  "primary ext2 1M -1 \"")
                    logger.debug(parted_cmd)
                    _functions.system(parted_cmd)
                    hostvgpart = "1"
                logger.info("Toggling LVM on")
                parted_cmd = ("parted \"" + drv + "\" -s \"set " +
                              str(hostvgpart) + " lvm on\"")
                logger.debug(parted_cmd)
                _functions.system(parted_cmd)
                _functions.system("parted \"" + self.ROOTDRIVE + \
                                  "\" -s \"print\"")
                _functions.system("udevadm settle 2> /dev/null || " + \
                                  "udevsettle &>/dev/null")
                # sync GPT to the legacy MBR partitions
                if ("OVIRT_INSTALL_ROOT" in _functions.OVIRT_VARS and
                     _functions.OVIRT_VARS["OVIRT_INSTALL_ROOT"] == "y"):
                    if self.LABEL_TYPE == "gpt":
                        logger.info("Running gptsync to create legacy mbr")
                        _functions.system("gptsync \"" + \
                                          self.ROOTDRIVE + "\"")

                self.physical_vols.append((drv, hostvgpart))
        drv_count = 0
        logger.debug(self.physical_vols)
        for drv, hostvgpart in self.physical_vols:
            partpv = None
            logger.info("Creating physical volume on (%s, %s)" % (drv,
                        hostvgpart))
            for _drv in self.HOSTVGDRIVE.strip(",").split(","):
                self.reread_partitions(_drv)
            i = 15
            while i > 0 and partpv is None:
                # e.g. /dev/cciss/c0d0p2
                for _partpv in [drv + hostvgpart, drv + "p" + hostvgpart]:
                    if os.path.exists(_partpv):
                        partpv = _partpv
                        break
                    logger.info(_partpv + " is not available!")
                i -= 1
                time.sleep(1)
            if i is 0:
                return False
            assert(partpv is not None)

            if not _functions.system("dd if=/dev/zero of=\"" + partpv +
                          "\" bs=1024k count=1"):
                logger.error("Failed to wipe lvm partition")
                return False
            if not _functions.system("pvcreate -ff -y \"" + partpv + "\""):
                logger.error("Failed to pvcreate on " + partpv)
                return False
            if drv_count < 1:
                logger.info("Creating volume group on " + partpv)
                if not _functions.system("vgcreate /dev/HostVG \"" + \
                                         partpv + "\""):
                    logger.error("Failed to vgcreate /dev/HostVG on " + partpv)
                    return False
            else:
                logger.info("Extending volume group on " + partpv)
                if not _functions.system("vgextend /dev/HostVG \"" + \
                                         partpv + "\""):
                    logger.error("Failed to vgextend /dev/HostVG on " + partpv)
                    return False
            drv_count = drv_count + 1
        if self.SWAP_SIZE > 0:
            logger.info("Creating swap partition")
            _functions.system("lvcreate --name Swap --size " + \
                              str(self.SWAP_SIZE) + "M /dev/HostVG")
            _functions.system("mkswap -L \"SWAP\" /dev/HostVG/Swap")
            _functions.system_closefds("echo \"/dev/HostVG/Swap swap swap " +
                            "defaults 0 0\" >> /etc/fstab")
            if "OVIRT_CRYPT_SWAP" in _functions.OVIRT_VARS:
                _functions.system_closefds("echo \"SWAP /dev/HostVG/Swap " +
                                "/dev/mapper/ovirt-crypt-swap " +
                                _functions.OVIRT_VARS["OVIRT_CRYPT_SWAP"] +
                                "\" >> /etc/ovirt-crypttab")
        if self.CONFIG_SIZE > 0:
            logger.info("Creating config partition")
            _functions.system("lvcreate --name Config --size " +
                    str(self.CONFIG_SIZE) + "M /dev/HostVG")
            _functions.system("mke2fs -j -t ext4 /dev/HostVG/Config " + \
                              "-L \"CONFIG\"")
            _functions.system("tune2fs -c 0 -i 0 /dev/HostVG/Config")
        if self.LOGGING_SIZE > 0:
            logger.info("Creating log partition")
            _functions.system("lvcreate --name Logging --size " +
                    str(self.LOGGING_SIZE) + "M /dev/HostVG")
            _functions.system("mke2fs -j -t ext4 /dev/HostVG/Logging " + \
                              "-L \"LOGGING\"")
            _functions.system("tune2fs -c 0 -i 0 /dev/HostVG/Logging")
            _functions.system_closefds("echo \"/dev/HostVG/Logging " + \
                            "/var/log ext4 defaults,noatime 0 0\" >> " + \
                            "/etc/fstab")
        use_data = 1
        if self.DATA_SIZE == -1:
            logger.info("Creating data partition with remaining free space")
            _functions.system("lvcreate --name Data -l 100%FREE /dev/HostVG")
            use_data = 0
        elif self.DATA_SIZE > 0:
            logger.info("Creating data partition")
            _functions.system("lvcreate --name Data --size " + \
                              str(self.DATA_SIZE) + "M /dev/HostVG")
            use_data = 0
        if use_data == 0:
            _functions.system("mke2fs -j -t ext4 /dev/HostVG/Data -L \"DATA\"")
            _functions.system("tune2fs -c 0 -i 0 /dev/HostVG/Data")
            _functions.system_closefds("echo \"/dev/HostVG/Data /data ext4 " +
                            "defaults,noatime 0 0\" >> /etc/fstab")
            _functions.system_closefds("echo \"/data/images " + \
                            "/var/lib/libvirt/images bind bind 0 0\" >> " + \
                            "/etc/fstab")
            _functions.system_closefds("echo \"/data/core " + \
                            "/var/log/core bind bind 0 0\" >> /etc/fstab")

        logger.info("Mounting config partition")
        _functions.mount_config()
        if os.path.ismount("/config"):
            _functions.ovirt_store_config("/etc/fstab")
        # remount /var/log from tmpfs to HostVG/Logging
        _functions.unmount_logging()
        _functions.mount_logging()
        if use_data == 0:
            logger.info("Mounting data partition")
            _functions.mount_data()
        logger.info("Completed HostVG Setup!")
        return True

    def create_efi_partition(self):
        if _functions.is_iscsi_install():
            disk = self.BOOTDRIVE
        else:
            disk = self.ROOTDRIVE
        parted_cmd = ("parted \"" + disk +
                     "\" -s \"mkpart EFI 1M " +
                     str(self.EFI_SIZE) + "M\"")
        _functions.system(parted_cmd)
        time.sleep(1)
        partefi = disk + "1"
        if not os.path.exists(partefi):
            partefi = disk + "p1"
        _functions.system("ln -snf \"" + partefi + \
                          "\" /dev/disk/by-label/EFI")
        _functions.system("mkfs.vfat \"" + partefi + "\"")

    def create_iscsiroot(self):
        logger.info("Partitioning iscsi root drive: " + self.ISCSIDRIVE)
        _functions.wipe_partitions(self.ISCSIDRIVE)
        self.reread_partitions(self.ISCSIDRIVE)
        logger.info("Labeling Drive: " + self.ISCSIDRIVE)
        parted_cmd = ("parted \"" + self.ISCSIDRIVE +
                     "\" -s \"mklabel " + self.LABEL_TYPE + "\"")
        logger.debug(parted_cmd)
        _functions.system(parted_cmd)
        logger.debug("Creating Root and RootBackup Partitions")
        parted_cmd = ("parted \"" + self.ISCSIDRIVE +
                      "\" -s \"mkpart primary 1M " +
                      str(self.ROOT_SIZE) + "M\"")
        logger.debug(parted_cmd)
        _functions.system(parted_cmd)
        parted_cmd = ("parted \"" + self.ISCSIDRIVE +
                     "\" -s \"mkpart primary ext2 " + str(self.ROOT_SIZE) +
                     "M " + str(self.ROOT_SIZE * 2) + "M\"")
        logger.debug(parted_cmd)
        _functions.system(parted_cmd)
        # sleep to ensure filesystems are created before continuing
        time.sleep(5)
        # force reload some cciss devices will fail to mkfs
        _functions.system("multipath -r")
        self.reread_partitions(self.ISCSIDRIVE)
        partroot = self.ISCSIDRIVE + "1"
        partrootbackup = self.ISCSIDRIVE + "2"
        if not os.path.exists(partroot):
            partroot = self.ISCSIDRIVE + "p1"
            partrootbackup = self.ISCSIDRIVE + "p2"
        _functions.system("ln -snf \"" + partroot + \
                          "\" /dev/disk/by-label/Root")
        _functions.system("mke2fs \"" + partroot + "\" -L Root")
        _functions.system("tune2fs -c 0 -i 0 \"" + partroot + "\"")
        _functions.system("ln -snf \"" + partrootbackup +
               "\" /dev/disk/by-label/RootBackup")
        _functions.system("mke2fs \"" + partrootbackup + "\" -L RootBackup")
        _functions.system("tune2fs -c 0 -i 0 \"" + partrootbackup + "\"")
        return True

    def create_appvg(self):
        logger.info("Creating LVM partition(s) for AppVG")
        physical_vols = []
        logger.debug("APPVGDRIVE: " + ' '.join(self.APPVGDRIVE))
        logger.debug("SWAP2_SIZE: " + str(self.SWAP2_SIZE))
        logger.debug("DATA2_SIZE: " + str(self.DATA2_SIZE))
        for drv in self.APPVGDRIVE:
            _functions.wipe_partitions(drv)
            self.reread_partitions(drv)
            logger.info("Labeling Drive: " + drv)
            appvgpart = "1"
            while True:
                parted_cmd = ("parted -s \"" + drv + "\" \"mklabel " +
                              self.LABEL_TYPE +
                              " mkpart primary ext2 2048s -1 set " +
                              appvgpart + " lvm on print\"")
                _functions.system(parted_cmd)
                self.reread_partitions(drv)
                if (os.path.exists(drv + appvgpart) or
                    os.path.exists(drv + "p" + appvgpart)):
                    break

            partpv = drv + appvgpart
            if not os.path.exists(partpv):
                # e.g. /dev/cciss/c0d0p2
                partpv = drv + "p" + appvgpart
            logger.info("Creating physical volume")
            if not os.path.exists(partpv):
                logger.error(partpv + " is not available!")
                return False
            dd_cmd = "dd if=/dev/zero of=\"" + partpv + "\" bs=1024k count=1"
            logger.info(dd_cmd)
            _functions.system(dd_cmd)
            _functions.system("pvcreate -ff -y \"" + partpv + "\"")
            physical_vols.append(partpv)

        logger.info("Creating volume group AppVG")
        is_first = True
        for drv in physical_vols:
            if is_first:
                _functions.system("vgcreate AppVG \"" + drv + "\"")
                is_first = False
            else:
                _functions.system("vgextend AppVG \"" + drv + "\"")

        if self.SWAP2_SIZE > 0:
            logger.info("Creating swap2 partition")
            lv_cmd = ("lvcreate --name Swap2 --size \"" +
                      str(self.SWAP2_SIZE) + "M\" /dev/AppVG")
            logger.debug(lv_cmd)
            _functions.system(lv_cmd)
            if "OVIRT_CRYPT_SWAP2" in _functions.OVIRT_VARS:
                _functions.system_closefds("echo \"SWAP2 /dev/AppVG/Swap2 " +
                                "/dev/mapper/ovirt-crypt-swap2 " +
                                _functions.OVIRT_VARS["OVIRT_CRYPT_SWAP2"] +
                                "\" >> /etc/ovirt-crypttab")
            else:
                _functions.system("mkswap -L \"SWAP2\" /dev/AppVG/Swap2")
                _functions.system_closefds("echo \"/dev/AppVG/Swap2 " + \
                                "swap swap defaults 0 0\" >> /etc/fstab")

        use_data = "1"
        if self.DATA2_SIZE == -1:
            logger.info("Creating data2 partition with remaining free space")
            _functions.system("lvcreate --name Data2 -l 100%FREE /dev/AppVG")
            use_data = 0
        elif self.DATA2_SIZE > 0:
            logger.info("Creating data2 partition")
            _functions.system("lvcreate --name Data2 --size " + \
                              str(self.DATA2_SIZE) +
                   "M /dev/AppVG")
            use_data = 0

        if use_data == 0:
            _functions.system("mke2fs -j -t ext4 /dev/AppVG/Data2 " + \
                              "-L \"DATA2\"")
            _functions.system("tune2fs -c 0 -i 0 /dev/AppVG/Data2")
            _functions.system_closefds("echo \"/dev/AppVG/Data2 /data2 ext4 " +
                            "defaults,noatime 0 0\" >> /etc/fstab")
            logger.info("Mounting data2 partition")
            _functions.mount_data2()
            logger.info("Completed AppVG!")
            return True

    def perform_partitioning(self):
        if self.HOSTVGDRIVE is None and not _functions.is_iscsi_install():
            logger.error("\nNo storage device selected.")
            return False

        if self.BOOTDRIVE is None and _functions.is_iscsi_install():
            logger.error("No storage device selected.")
            return False

        if not self.cross_check_host_app():
            logger.error("Skip disk partitioning, AppVG overlaps with HostVG")
            return False

        if _functions.has_fakeraid(self.HOSTVGDRIVE):
            if not handle_fakeraid(self.HOSTVGDRIVE):
                return False
        if _functions.has_fakeraid(self.ROOTDRIVE):
            if not handle_fakeraid(self.ROOTDRIVE):
                return False

        logger.info("Saving parameters")
        _functions.unmount_config("/etc/default/ovirt")
        if not self.check_partition_sizes():
            return False

        # Check for still remaining HostVGs this can be the case when
        # Node was installed on a disk not given in storage_init
        # rhbz#872114
        existing_vgs = str(_functions.passthrough("vgs"))
        for vg in existing_vgs.split("\n"):
            vg = vg.strip()
            if "HostVG" in str(vg):
                logger.error("An existing installation was found or not " +
                     "all VGs could be removed.  " +
                     "Please manually cleanup the storage using " +
                     "standard disk tools.")
                return False

        logger.info("Removing old LVM partitions")
        # HostVG must not exist at this point
        # we wipe only foreign LVM here
        logger.info("Wiping LVM on HOSTVGDRIVE %s" % self.HOSTVGDRIVE)
        if not self.wipe_lvm_on_disk(self.HOSTVGDRIVE):
            logger.error("Wiping LVM on %s Failed" % self.HOSTVGDRIVE)
            return False
        logger.info("Wiping LVM on ROOTDRIVE %s" % self.ROOTDRIVE)
        if not self.wipe_lvm_on_disk(self.ROOTDRIVE):
            logger.error("Wiping LVM on %s Failed" % self.ROOTDRIVE)
            return False
        logger.info("Wiping LVM on BOOTDRIVE %s" % self.BOOTDRIVE)
        if not self.wipe_lvm_on_disk(self.BOOTDRIVE):
            logger.error("Wiping LVM on %s Failed" % self.BOOTDRIVE)
            return False
        logger.debug("Old LVM partitions should be gone.")
        logger.debug(_functions.passthrough("vgdisplay -v"))

        self.boot_size_si = self.BOOT_SIZE * (1024 * 1024) / (1000 * 1000)
        if _functions.is_iscsi_install():
            if "OVIRT_ISCSI_NAME" in _functions.OVIRT_VARS:
                iscsi_name = _functions.OVIRT_VARS["OVIRT_ISCSI_NAME"]
                set_iscsi_initiator(iscsi_name)
            # login to target and setup disk
            get_targets = ("iscsiadm -m discovery -p %s:%s -t sendtargets" %
                           (_functions.OVIRT_VARS["OVIRT_ISCSI_TARGET_HOST"],
                           _functions.OVIRT_VARS["OVIRT_ISCSI_TARGET_PORT"]))
            _functions.system(get_targets)
            before_login_drvs = self.get_dev_name()
            logger.debug(before_login_drvs)
            login_cmd = ("iscsiadm -m node -T %s -p %s:%s -l" %
                        (_functions.OVIRT_VARS["OVIRT_ISCSI_TARGET_NAME"],
                        _functions.OVIRT_VARS["OVIRT_ISCSI_TARGET_HOST"],
                        _functions.OVIRT_VARS["OVIRT_ISCSI_TARGET_PORT"]))
            _functions.system(login_cmd)
            _functions.system("multipath -r")
            after_login_drvs = self.get_dev_name()
            logger.debug(after_login_drvs)
            logger.info("iSCSI enabled, partitioning boot drive: %s" %
                        self.BOOTDRIVE)
            _functions.wipe_partitions(self.BOOTDRIVE)
            self.reread_partitions(self.BOOTDRIVE)
            logger.info("Creating boot partition")
            parted_cmd = "parted %s -s \"mklabel %s\"" % (self.BOOTDRIVE,
                                                          self.LABEL_TYPE)
            _functions.system(parted_cmd)
            self.create_efi_partition()
            boot_end_mb = self.EFI_SIZE + self.BOOT_SIZE
            parted_cmd = ("parted \"%s\" -s \"mkpart primary ext2 %sM %sM\"" %
                         (self.BOOTDRIVE, self.EFI_SIZE, boot_end_mb))
            _functions.system(parted_cmd)
            parted_cmd = ("parted \"%s\" -s \"mkpart primary ext2 %sM %sM\"" %
                         (self.BOOTDRIVE , boot_end_mb, boot_end_mb + self.BOOT_SIZE))
            _functions.system(parted_cmd)
            parted_cmd = ("parted \"" + self.BOOTDRIVE + "\" -s \"set 1 " +
                         "boot on\"")
            _functions.system(parted_cmd)
            self.reread_partitions(self.BOOTDRIVE)
            partboot = self.BOOTDRIVE + "2"
            partbootbackup = self.BOOTDRIVE + "3"

            if not os.path.exists(partboot):
                logger.debug("%s does not exist" % partboot)
                partboot = self.BOOTDRIVE + "p2"
                partbootbackup = self.BOOTDRIVE + "p3"

            # sleep to ensure filesystems are created before continuing
            _functions.system("udevadm settle")
            _functions.system("mke2fs \"" + str(partboot) + "\" -L Boot")
            _functions.system("tune2fs -c 0 -i 0 \"" + str(partboot) + "\"")
            _functions.system("ln -snf \"" + partboot + \
                              "\" /dev/disk/by-label/Boot")
            _functions.system("mke2fs \"" + str(partbootbackup) + \
                              "\" -L BootBackup")
            _functions.system("tune2fs -c 0 -i 0 \"" + \
                              str(partbootbackup) + "\"")
            _functions.system("ln -snf \"" + partbootbackup +
                   "\" /dev/disk/by-label/BootBackup")
            self.ISCSIDRIVE = _functions.translate_multipath_device(
                               _functions.OVIRT_VARS["OVIRT_ISCSI_INIT"])
            logger.debug(self.ISCSIDRIVE)
            if self.create_iscsiroot():
                logger.info("iSCSI Root Partitions Created")
                if self.create_hostvg():
                    if len(self.APPVGDRIVE) > 0:
                        self.create_appvg()
                    logger.info("Completed!")
                    return True

        if ("OVIRT_ROOT_INSTALL" in _functions.OVIRT_VARS and
                  _functions.OVIRT_VARS["OVIRT_ROOT_INSTALL"] == "y" and not \
                      _functions.is_iscsi_install()):
            logger.info("Partitioning root drive: " + self.ROOTDRIVE)
            _functions.wipe_partitions(self.ROOTDRIVE)
            self.reread_partitions(self.ROOTDRIVE)
            logger.info("Labeling Drive: " + self.ROOTDRIVE)
            parted_cmd = ("parted \"" + self.ROOTDRIVE + "\" -s \"mklabel " +
                         self.LABEL_TYPE + "\"")
            _functions.passthrough(parted_cmd, logger.debug)
            logger.debug("Creating Root and RootBackup Partitions")
            if _functions.is_efi_boot():
                self.create_efi_partition()
            else:
                # create partition labeled bios_grub
                parted_cmd = ("parted \"" + self.ROOTDRIVE +
                             "\" -s \"mkpart primary 1M " +
                             str(self.EFI_SIZE) + "M\"")
                _functions.passthrough(parted_cmd, logger.debug)
                parted_cmd = ("parted \"" + self.ROOTDRIVE +
                             "\" -s \"set 1 bios_grub on\"")
                _functions.passthrough(parted_cmd, logger.debug)
            parted_cmd = ("parted \"" + self.ROOTDRIVE +
                         "\" -s \"mkpart primary ext2 " + str(self.EFI_SIZE) +
                         "M " + str(self.Root_end) + "M\"")
            _functions.passthrough(parted_cmd, logger.debug)
            parted_cmd = ("parted \"" + self.ROOTDRIVE +
                         "\" -s \"mkpart primary ext2 " +
                         str(self.Root_end) + "M " +
                         str(self.RootBackup_end) + "M\"")
            logger.debug(parted_cmd)
            _functions.system(parted_cmd)
            _functions.system("sync ; udevadm settle ; partprobe")
            parted_cmd = ("parted \"" + self.ROOTDRIVE +
                         "\" -s \"set 2 boot on\"")
            logger.debug(parted_cmd)
            _functions.system(parted_cmd)
            # force reload some cciss devices will fail to mkfs
            _functions.system("multipath -r &>/dev/null")
            self.reread_partitions(self.ROOTDRIVE)
            partroot = self.ROOTDRIVE + "2"
            partrootbackup = self.ROOTDRIVE + "3"
            if not os.path.exists(partroot):
                partroot = self.ROOTDRIVE + "p2"
                partrootbackup = self.ROOTDRIVE + "p3"
            _functions.system("mke2fs \"" + partroot + "\" -L Root")
            _functions.system("tune2fs -c 0 -i 0 \"" + partroot + "\"")
            _functions.system("ln -snf \"" + partrootbackup +
                   "\" /dev/disk/by-label/RootBackup")
            _functions.system("mke2fs \"" + partrootbackup + \
                              "\" -L RootBackup")
            _functions.system("tune2fs -c 0 -i 0 \"" + partrootbackup + "\"")
        hostvg1 = self.HOSTVGDRIVE.split(",")[0]
        self.reread_partitions(self.ROOTDRIVE)
        if self.ROOTDRIVE != hostvg1:
            _functions.system("parted \"" + hostvg1 + "\" -s \"mklabel " +
                   self.LABEL_TYPE + "\"")
        if self.create_hostvg():
            if len(self.APPVGDRIVE) > 0:
                self.create_appvg()
        else:
            return False
        if ("OVIRT_CRYPT_SWAP2" in _functions.OVIRT_VARS or
            "OVIRT_CRYPT_SWAP" in _functions.OVIRT_VARS):
            _functions.ovirt_store_config("/etc/ovirt-crypttab")
        return True

    def check_partition_sizes(self):
        drive_list = []
        drive_space_dict = {}
        min_data_size = self.DATA_SIZE
        if self.DATA_SIZE == -1:
            min_data_size = 5

        if _functions.is_iscsi_install():
            BOOTDRIVESPACE = self.get_drive_size(self.BOOTDRIVE)
            drive_list.append("BOOT")
            drive_space_dict["BOOTDRIVESPACE"] = BOOTDRIVESPACE
            drive_space_dict["BOOT_NEED_SIZE"] = self.BOOT_SIZE
            if BOOTDRIVESPACE > self.BOOT_SIZE:
                return True

        else:
            ROOTDRIVESPACE = self.get_drive_size(self.ROOTDRIVE)
            HOSTVGDRIVESPACE = 0
            for drive in self.HOSTVGDRIVE.strip(",").split(","):
                space = self.get_drive_size(drive)
                HOSTVGDRIVESPACE = HOSTVGDRIVESPACE + space
            ROOT_NEED_SIZE = self.ROOT_SIZE * 2 + self.EFI_SIZE
            HOSTVG_NEED_SIZE = (int(self.SWAP_SIZE) + int(self.CONFIG_SIZE) +
                                int(self.LOGGING_SIZE) + int(min_data_size))
            drive_space_dict["ROOTDRIVESPACE"] = ROOTDRIVESPACE
            drive_space_dict["ROOT_NEED_SIZE"] = ROOT_NEED_SIZE
            drive_space_dict["HOSTVGDRIVESPACE"] = HOSTVGDRIVESPACE
            drive_space_dict["HOSTVG_NEED_SIZE"] = HOSTVG_NEED_SIZE
            hostvg1 = self.HOSTVGDRIVE.split(",")[0]
            if self.ROOTDRIVE == hostvg1:
                drive_list.append("HOSTVG")
                HOSTVG_NEED_SIZE = ROOT_NEED_SIZE + HOSTVG_NEED_SIZE
                drive_space_dict["HOSTVG_NEED_SIZE"] = HOSTVG_NEED_SIZE
            else:
                drive_list.append("ROOT")
                drive_list.append("HOSTVG")

            for drive in drive_list:
                drive_need_size = drive_space_dict[drive + "_NEED_SIZE"]
                drive_disk_size = drive_space_dict[drive + "DRIVESPACE"]

            self.drive_disk_size = drive_disk_size
            self.drive_need_size = drive_need_size

            if ROOT_NEED_SIZE > ROOTDRIVESPACE:
                gap_size = ROOT_NEED_SIZE - ROOTDRIVESPACE
                logger.error("The target storage device is too small for " +
                             "the desired sizes:")
                logger.error(" Disk Target: Root")
                logger.error(" Size of target storage device: " +
                             str(ROOTDRIVESPACE) + "MB")
                logger.error(" Total storage size to be used: " +
                             str(ROOT_NEED_SIZE) + "MB")
                logger.error("You need an additional " + str(gap_size) +
                             "MB of storage.")
                return False

            if drive_need_size > drive_disk_size:
                gap_size = drive_need_size - drive_disk_size
                logger.error("The target storage device is too small for " +
                             "the desired sizes:")
                logger.error(" Disk Target: " + drive)
                logger.error(" Size of target storage device: " +
                             str(drive_disk_size) + "MB")
                logger.error(" Total storage size to be used: " +
                             str(drive_need_size) + "MB")
                logger.error("You need an additional " + str(gap_size) +
                             "MB of storage.")
                return False
            else:
                logger.info("Required Space : " + str(drive_need_size) + "MB")
                return True


def wipe_fakeraid(device):
    dmraid_cmd = "echo y | dmraid -rE $(readlink -f \"%s\")" % device
    dmraid = _functions.subprocess_closefds(dmraid_cmd,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT,
                                 shell=True)
    dmraid.communicate()
    dmraid.poll()
    if dmraid.returncode == 0:
        return True
    else:
        return False


def handle_fakeraid(device):
    if _functions.is_wipe_fakeraid():
        return wipe_fakeraid(device)
    #don't wipe fakeraid
    logger.error(("Fakeraid metadata detected on %s, Aborting install."
                 % device))
    logger.error(("If you want auto-install to wipe the fakeraid metadata " +
                 "automatically,"))
    logger.error(("then boot with the wipe-fakeraid option on the kernel " +
                 "commandline."))
    return False


def storage_auto():
    storage = Storage()
    if not _functions.OVIRT_VARS["OVIRT_INIT"] == "":
        #force root install variable for autoinstalls
        _functions.OVIRT_VARS["OVIRT_ROOT_INSTALL"] = "y"
        if _functions.check_existing_hostvg("") or \
           _functions.check_existing_hostvg("","AppVG"):
            logger.error("HostVG/AppVG exists on a separate disk")
            logger.error("Manual Intervention required")
            return False
        if storage.perform_partitioning():
            return True
    else:
        logger.error("Storage Device Is Required for Auto Installation")
    return False
