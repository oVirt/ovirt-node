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

from ovirtnode.ovirtfunctions import *
import os
import time
import re
import subprocess
from subprocess import PIPE, STDOUT
import gudev
import logging

class Storage:
    def __init__(self):
        logger = logging.getLogger(PRODUCT_SHORT)
        logger.propagate = False
        OVIRT_VARS = parse_defaults()
        self.overcommit=0.5
        self.BOOT_SIZE=50
        self.ROOT_SIZE=256
        self.CONFIG_SIZE=5
        self.LOGGING_SIZE=2048
        self.EFI_SIZE=256
        self.SWAP_SIZE=0
        self.SWAP2_SIZE=0
        self.DATA2_SIZE=0
        self.BOOTDRIVE = ""
        self.HOSTVGDRIVE = ""
        self.APPVGDRIVE = []
        self.ISCSIDRIVE = ""
        # -1 indicates data partition should use remaining disk
        self.DATA_SIZE = -1
        # gpt or msdos partition table type
        self.LABEL_TYPE="gpt"
        if OVIRT_VARS.has_key("OVIRT_INIT"):
            OVIRT_VARS["OVIRT_INIT"] = OVIRT_VARS["OVIRT_INIT"].strip(",")
            if "," in OVIRT_VARS["OVIRT_INIT"]:
                disk_count = 0
                for disk in OVIRT_VARS["OVIRT_INIT"].split(","):
                    if disk_count < 1:
                        self.ROOTDRIVE = disk
                        disk_count = disk_count + 1
                    else:
                        self.HOSTVGDRIVE = self.HOSTVGDRIVE + disk + ","
            else:
                self.ROOTDRIVE = translate_multipath_device(OVIRT_VARS["OVIRT_INIT"])
                self.HOSTVGDRIVE = translate_multipath_device(OVIRT_VARS["OVIRT_INIT"])
            if is_iscsi_install():
                logger.info(self.BOOTDRIVE)
                logger.info(self.ROOTDRIVE)
                self.BOOTDRIVE = translate_multipath_device(self.ROOTDRIVE)
        mem_size_cmd = "awk '/MemTotal:/ { print $2 }' /proc/meminfo"
        mem_size_mb = subprocess.Popen(mem_size_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        MEM_SIZE_MB = mem_size_mb.stdout.read()
        MEM_SIZE_MB= int(MEM_SIZE_MB) / 1024
        # we multiply the overcommit coefficient by 10 then divide the
        # product by 10 to avoid decimals in the result
        OVERCOMMIT_SWAP_SIZE = int(MEM_SIZE_MB) * self.overcommit * 10 / 10
        # add to the swap the amounts from http://kbase.redhat.com/faq/docs/DOC-15252
        MEM_SIZE_GB= int(MEM_SIZE_MB)/1024
        if MEM_SIZE_GB < 4:
            BASE_SWAP_SIZE=2048
        elif MEM_SIZE_GB < 16:
            BASE_SWAP_SIZE=4096
        elif MEM_SIZE_GB < 64:
            BASE_SWAP_SIZE=8192
        else:
            BASE_SWAP_SIZE=16384
        self.SWAP_SIZE = int(BASE_SWAP_SIZE) + int(OVERCOMMIT_SWAP_SIZE)

        for i in ['OVIRT_VOL_BOOT_SIZE','OVIRT_VOL_SWAP_SIZE','OVIRT_VOL_ROOT_SIZE','OVIRT_VOL_CONFIG_SIZE','OVIRT_VOL_LOGGING_SIZE', \
                  'OVIRT_VOL_DATA_SIZE','OVIRT_VOL_SWAP2_SIZE','OVIRT_VOL_DATA2_SIZE']:
            i_short = i.replace("OVIRT_VOL_","")
            if OVIRT_VARS.has_key(i):
                logging.info("Setting value for %s to %s " % (self.__dict__[i_short], OVIRT_VARS[i]))
                self.__dict__[i_short] = int(OVIRT_VARS[i])
            else:
                logging.info("Using default value for: %s" % i_short)

        self.RootBackup_end = self.ROOT_SIZE * 2 + self.EFI_SIZE
        self.Root_end = self.EFI_SIZE + self.ROOT_SIZE

        if OVIRT_VARS.has_key("OVIRT_INIT_APP"):
            if self.SWAP2_SIZE != 0 or self.DATA2_SIZE != 0:
                for drv in OVIRT_VARS["OVIRT_INIT_APP"].split(","):
                    DRIVE = translate_multipath_device(drv)
                    self.APPVGDRIVE.append(DRIVE)
            if not self.cross_check_host_app:
                logger.error("Skip disk partitioning, AppVG overlaps with HostVG")
                sys.exit(1)
        else:
            if self.SWAP2_SIZE != 0 or self.DATA2_SIZE != 0:
                logger.error("Missing device parameter for AppVG: unable to partition any disk")
                sys.exit(2)


    def cross_check_host_app(self):
        for hdrv in self.HOSTVGDRIVE:
            if hdrv in self.APPDRIVE:
                # Skip disk partitioning, AppVG overlaps with HostVG
                return False
            else:
                return True

    def get_drive_size(self, drive):
        size_cmd = "sfdisk -s " + drive + " 2>null"
        size = subprocess.Popen(size_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        size = size.stdout.read()
        size = int(int(size) / 1024)
        return size


    def wipe_lvm_on_disk(self, dev):
        part_delim="p"
        if "/dev/sd" in dev:
            part_delim=""
        vg_cmd = "pvs -o vg_uuid --noheadings \"%s\" \"%s%s\"[0-9]* 2>/dev/null|sort -u" % (dev, dev, part_delim)
        vg_proc = subprocess.Popen(vg_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        for vg in vg_proc.stdout.read().split():
            pvs_cmd="pvs -o pv_name,vg_uuid --noheadings | grep \"%s\" | egrep -v -q \"%s%s[0-9]+|%s \"" % (vg, dev, part_delim, dev)
            if system(pvs_cmd):
                logger.error("The volume group \"%s\" spans multiple disks." % vg)
                logger.error("This operation cannot complete.  Please manually cleanup the storage using standard disk tools.")
                sys.exit(1)
            wipe_volume_group(vg)
        return


    def reread_partitions(self, drive):
        if "dev/mapper" in drive:
            # kpartx -a -p p "$drive"
            # XXX fails with spaces in device names (TBI)
            # ioctl(3, DM_TABLE_LOAD, 0x966980) = -1 EINVAL (Invalid argument)
            # create/reload failed on 0QEMU    QEMU HARDDISK   drive-scsi0-0-0p1
            system("partprobe")
            # partprobe fails on cdrom:
            # Error: Invalid partition table - recursive partition on /dev/sr0.
            system("service multipathd reload")

        else:
            system("blockdev --rereadpt " + drive + " &>>/dev/null")


    def get_sd_name(self, id):
        device_sys_cmd = "grep -H \"^%s$\" /sys/block/*/dev | cut -d: -f1" % id
        device_sys = subprocess.Popen(device_sys_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        device_sys_output = device_sys.stdout.read().strip()
        if not device_sys_output is "":
            device = os.path.basename(os.path.dirname(device_sys_output))
            return device


    # gets the dependent block devices for multipath devices
    def get_multipath_deps(self, mpath_device):
        deplist=""
        #get dependencies for multipath device
        deps_cmd = "dmsetup deps -u mpath-%s | sed 's/^.*: //' \
        | sed 's/, /:/g' | sed 's/[\(\)]//g'" % mpath_device
        deps = subprocess.Popen(deps_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        deps_output = deps.stdout.read()
        for dep in deps_output.split():
            device=self.get_sd_name(dep)
            if device is not None:
                deplist = "%s %s" % (device, deplist)
        return deplist

        return (dev_names.sort(), self.disk_dict)

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
            byid_list_cmd = "find /dev/disk/by-id -mindepth 1 -not -name '*-part*' 2>/dev/null"
            byid_list = subprocess.Popen(byid_list_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
            byid_list_output = byid_list.stdout.read()
        for d in byid_list_output.split():
            d = os.readlink(d)
            d_basename = os.path.basename(d)
            udev_cmd = "udevadm info --name=/dev/" + d_basename + " --query=property | grep -q ^ID_BUS: &>>/dev/null"
            if os.system(udev_cmd):
                devices.append("/dev/%s" % d_basename)
        # FIXME: workaround for detecting cciss devices
        if os.path.exists("/dev/cciss"):
            for d in os.listdir("/dev/cciss"):
                if not re.match("p[0-9]+\$", d):
                     devices.append("/dev/cciss/%s" % d)

        # include multipath devices
        devs_to_remove=""
        multipath_list_cmd = "dmsetup ls --target=multipath | cut -f1"
        multipath_list = subprocess.Popen(multipath_list_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        multipath_list_output = multipath_list.stdout.read()

        for d in multipath_list_output.split():
            devices.append("/dev/mapper/%s" % d)
            sd_devs=""
            sd_devs = self.get_multipath_deps(d)

            dm_dev_cmd = "multipath -ll \"%s\" | grep \"%s\" | sed -r 's/^.*(dm-[0-9]+ ).*$/\\1/'" % (d, d)
            dm_dev = subprocess.Popen(dm_dev_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
            dm_dev_output = dm_dev.stdout.read()
            devs_to_remove="%s %s %s" % (devs_to_remove, sd_devs, dm_dev_output)
        # Remove /dev/sd* devices that are part of a multipath device
        dev_list=[]
        for d in devices:
            if os.path.basename(d) not in devs_to_remove and not "/dev/dm-" in d:
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
            dev_size = subprocess.Popen(dev_size_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
            dev_size = dev_size.stdout.read()
            size_failed = 0
            if not device.get_property("ID_CDROM"):
                try:
                    dev_size = int(dev_size) / 1024 /1024
                except:
                   size_failed = 1
            if not dev_desc:
                if "/dev/vd" in dev_name:
                    dev_desc = "virtio disk"
                else:
                    dev_desc = "unknown"
            if not device.get_property("ID_CDROM") and not "/dev/dm-" in dev_name and not "/dev/loop" in dev_name and size_failed == 0:
                dev_name = translate_multipath_device(dev_name)
                if dev_bus == "usb":
                    dev_bus = "USB Device          "
                elif dev_bus == "ata" or dev_bus == "scsi" or dev_bus == "cciss" or "/dev/vd" in dev_name:
                    dev_bus = "Local / FibreChannel"
                else:
                    dev_bus = "                    "

                self.disk_dict[dev_name] = "%s,%s,%s,%s,%s,%s" % (dev_bus,dev_name,dev_size,dev_desc,dev_serial,dev_model)
        devs = self.get_dev_name()
        return (sorted(devs), self.disk_dict)

    def check_partition_sizes(self):
        drive_list = []
        drive_space_dict = {}
        min_data_size = self.DATA_SIZE
        if self.DATA_SIZE == -1 :
            min_data_size=5
        if is_iscsi_install():
            BOOTDRIVESPACE = get_drive_size(self.BOOTDRIVE)
            drive_list.append("BOOT")
            drive_space_dict["BOOTDRIVESPACE"] = BOOTDRIVESPACE
            drive_space_dict["BOOT_NEED_SIZE"] = self.BOOT_SIZE
        else:
            ROOTDRIVESPACE = get_drive_size(self.ROOTDRIVE)
            HOSTVGDRIVESPACE = get_drive_size(self.HOSTVGDRIVE)
            ROOT_NEED_SIZE=self.ROOT_SIZE * 2
            HOSTVG_NEED_SIZE=self.SWAP_SIZE + self.CONFIG_SIZE + self.LOGGING_SIZE + min_data_size
            drive_space_dict["ROOTDRIVESPACE"] = ROOTDRIVESPACE
            drive_space_dict["ROOT_NEED_SIZE"] = ROOT_NEED_SIZE
            drive_space_dict["HOSTVGDRIVESPACE"] = HOSTVGDRIVESPACE
            drive_space_dict["HOSTVG_NEED_SIZE"] = HOSTVG_NEED_SIZE
            if self.ROOTDRIVE == self.HOSTVGDRIVE:
                drive_list.append("ROOT")
                ROOT_NEED_SIZE=self.ROOT_SIZE * 2 + HOSTVG_NEED_SIZE
                drive_space_dict["ROOT_NEED_SIZE"] = ROOT_NEED_SIZE
            else:
                drive_list.append("ROOT")
                drive_list.append("HOSTVG")

            for drive in drive_list:
                drive_need_size = drive_space_dict[drive + "NEED_SIZE"]
                drive_disk_size= drive_space_dict[drive + "DRIVESPACE"]
    
            if drive_need_size > drive_disk_size:
                gap_size = drive_need_size - drive_disk_size
                logger.error("The target storage device is too small for the desired sizes:")
                logger.error(" Disk Target: " + drive)
                logger.error(" Size of target storage device: " + drive_disk_size + "MB")
                logger.error(" Total storage size to be used: " + drive_need_size + "MB")
                logger.error("You need an additional " + gap_size + "MB of storage.")
                sys.exit(1)
            else:
                logger.info("Required Space : " + drive_need_size + "MB")
                return True

    def create_hostvg(self):
        logger.info("Creating LVM partition")
        self.physical_vols = []
        for drv in self.HOSTVGDRIVE.strip(",").split(","):
            drv = translate_multipath_device(drv)
            if drv != "":
                if self.ROOTDRIVE == drv:
                    self.reread_partitions(self.ROOTDRIVE)
                    parted_cmd = "parted \"" + drv + "\" -s \"mkpart primary ext2 "+ str(self.RootBackup_end) +"M -1\""
                    logger.debug(parted_cmd)
                    system(parted_cmd)
                    hostvgpart="4"
                elif self.BOOTDRIVE == drv:
                    parted_cmd = "parted \"" + drv + "\" -s \"mkpart primary ext2 " + str(self.boot_size_si) + " -1\""
                    logger.debug(parted_cmd)
                    system(parted_cmd)
                    hostvgpart="2"
                    self.ROOTDRIVE = self.BOOTDRIVE
                elif self.ISCSIDRIVE == drv:
                    parted_cmd = "parted \"" + drv + "\" -s \"mkpart primary ext2 512M -1\""
                    logger.debug(parted_cmd)
                    system(parted_cmd)
                    hostvgpart="3"
                else:
                    system("parted \""+ drv +"\" -s \"mklabel "+self.LABEL_TYPE+"\"")
                    parted_cmd = "parted \""+ drv + "\" -s \"mkpart primary ext2 1M -1 \""
                    logger.debug(parted_cmd)
                    system(parted_cmd)
                    hostvgpart = "1"
                logger.info("Toggling LVM on")
                parted_cmd = "parted \"" + drv +  "\" -s \"set " + str(hostvgpart) + " lvm on\""
                logger.debug(parted_cmd)
                system(parted_cmd)
                system("parted \"" + self.ROOTDRIVE + "\" -s \"print\"")
                system("udevadm settle 2> /dev/null || udevsettle &>/dev/null")
                self.reread_partitions(drv)
                # sync GPT to the legacy MBR partitions
                if OVIRT_VARS.has_key("OVIRT_INSTALL_ROOT") and OVIRT_VARS["OVIRT_INSTALL_ROOT"] == "y" :
                    if self.LABEL_TYPE == "gpt":
                        logger.info("Running gptsync to create legacy mbr")
                        system("gptsync \"" + self.ROOTDRIVE + "\"")

                partpv = drv + hostvgpart
                if not os.path.exists(partpv):
                    # e.g. /dev/cciss/c0d0p2
                    partpv = drv + "p" + hostvgpart
                self.physical_vols.append(partpv)
        drv_count = 0
        logger.debug(self.physical_vols)
        for partpv in self.physical_vols:
            logger.info("Creating physical volume on " + partpv)
            for drv in self.HOSTVGDRIVE.strip(",").split(","):
                self.reread_partitions(drv)
            i = 0
            while not os.path.exists(partpv):
                logger.error(partpv + "is not available!")
                i = i + i
                time.sleep(1)
                if i == 15:
                    return False
            if not system("dd if=/dev/zero of=\"" + partpv + "\" bs=1024k count=1"):
                logger.error("Failed to wipe lvm partition")
                return False
            if not system("pvcreate -ff -y \"" + partpv + "\""):
                logger.error("Failed to pvcreate on " + partpv)
                return False
            if drv_count < 1:
                logger.info("Creating volume group on " + partpv)
                if not system("vgcreate /dev/HostVG \"" + partpv + "\""):
                    logger.error("Failed to vgcreate /dev/HostVG on " + partpv)
                    return False
            else:
                logger.info("Extending volume group on " + partpv)
                if not system("vgextend /dev/HostVG \"" + partpv + "\""):
                    logger.error("Failed to vgextend /dev/HostVG on " + partpv)
                    return False
            drv_count = drv_count + 1
        if self.SWAP_SIZE > 0:
            logger.info("Creating swap partition")
            system("lvcreate --name Swap --size "+str(self.SWAP_SIZE) + "M /dev/HostVG")
            system("mkswap -L \"SWAP\" /dev/HostVG/Swap")
            os.system("echo \"/dev/HostVG/Swap swap swap defaults 0 0\" >> /etc/fstab")
            if OVIRT_VARS.has_key("OVIRT_CRYPT_SWAP"):
                os.system("echo \"SWAP /dev/HostVG/Swap /dev/mapper/ovirt-crypt-swap " + OVIRT_VARS["OVIRT_CRYPT_SWAP"] + "\" >> /etc/ovirt-crypttab")
        if self.CONFIG_SIZE > 0:
            logger.info("Creating config partition")
            system("lvcreate --name Config --size "+str(self.CONFIG_SIZE)+"M /dev/HostVG")
            system("mke2fs -j -t ext4 /dev/HostVG/Config -L \"CONFIG\"")
            system("tune2fs -c 0 -i 0 /dev/HostVG/Config")
        if self.LOGGING_SIZE > 0:
            logger.info("Creating log partition")
            system("lvcreate --name Logging --size "+str(self.LOGGING_SIZE)+"M /dev/HostVG")
            system("mke2fs -j -t ext4 /dev/HostVG/Logging -L \"LOGGING\"")
            system("tune2fs -c 0 -i 0 /dev/HostVG/Logging")
            os.system("echo \"/dev/HostVG/Logging /var/log ext4 defaults,noatime 0 0\" >> /etc/fstab")
        use_data=1
        if self.DATA_SIZE == -1:
            logger.info("Creating data partition with remaining free space")
            system("lvcreate --name Data -l 100%FREE /dev/HostVG")
            use_data=0
        elif self.DATA_SIZE > 0:
            logger.info("Creating data partition")
            system("lvcreate --name Data --size "+str(self.DATA_SIZE)+"M /dev/HostVG")
            use_data=0
        if use_data == 0:
            system("mke2fs -j -t ext4 /dev/HostVG/Data -L \"DATA\"")
            system("tune2fs -c 0 -i 0 /dev/HostVG/Data")
            os.system("echo \"/dev/HostVG/Data /data ext4 defaults,noatime 0 0\" >> /etc/fstab")
            os.system("echo \"/data/images /var/lib/libvirt/images bind bind 0 0\" >> /etc/fstab")
            os.system("echo \"/data/core /var/log/core bind bind 0 0\" >> /etc/fstab")

        logger.info("Mounting config partition")
        mount_config()
        if os.path.ismount("/config"):
            ovirt_store_config("/etc/fstab")
        # remount /var/log from tmpfs to HostVG/Logging
        unmount_logging()
        mount_logging()
        if use_data == 0:
            logger.info("Mounting data partition")
            mount_data()
        logger.info("Completed HostVG Setup!")
        return True

    def create_iscsiroot(self):
        logger.info("Partitioning iscsi root drive: " + self.ISCSIDRIVE)
        wipe_partitions(self.ISCSIDRIVE)
        self.reread_partitions(self.ISCSIDRIVE)
        logger.info("Labeling Drive: " + self.ISCSIDRIVE)
        parted_cmd = "parted \""+ self.ISCSIDRIVE +"\" -s \"mklabel "+ self.LABEL_TYPE+"\""
        logger.debug(parted_cmd)
        system(parted_cmd)
        logger.debug("Creating Root and RootBackup Partitions")
        parted_cmd = "parted \"" + self.ISCSIDRIVE + "\" -s \"mkpart primary ext2 1M 256M\""
        logger.debug(parted_cmd)
        system(parted_cmd)
        parted_cmd = "parted \"" + self.ISCSIDRIVE + "\" -s \"mkpart primary ext2 256M 512M\""
        logger.debug(parted_cmd)
        system(parted_cmd)
        # sleep to ensure filesystems are created before continuing
        time.sleep(5)
        # force reload some cciss devices will fail to mkfs
        system("multipath -r")
        self.reread_partitions(self.ISCSIDRIVE)
        partroot = self.ISCSIDRIVE + "1"
        partrootbackup = self.ISCSIDRIVE + "2"
        if not os.path.exists(partroot):
            partroot = self.ISCSIDRIVE + "p1"
            partrootbackup= self.ISCSIDRIVE + "p2"
        system("ln -snf \""+partroot+"\" /dev/disk/by-label/Root")
        system("mke2fs \""+partroot+"\" -L Root")
        system("tune2fs -c 0 -i 0 \""+partroot+"\"")
        system("ln -snf \""+partrootbackup+"\" /dev/disk/by-label/RootBackup")
        system("mke2fs \""+partrootbackup+"\" -L RootBackup")
        system("tune2fs -c 0 -i 0 \""+partrootbackup+"\"")
        return True

    def create_appvg(self):
        logger.info("Creating LVM partition(s) for AppVG")
        physical_vols = []
        logger.debug("APPVGDRIVE: " + ' '.join(self.APPVGDRIVE))
        logger.debug("SWAP2_SIZE: " + str(self.SWAP2_SIZE))
        logger.debug("DATA2_SIZE: " + str(self.DATA2_SIZE))
        for drv in self.APPVGDRIVE:
            wipe_partitions(drv)
            self.reread_partitions(drv)
            logger.info("Labeling Drive: " + drv)
            appvgpart = "1"
            while True:
                parted_cmd = "parted -s \"" + drv + "\" \"mklabel " + self.LABEL_TYPE + " mkpart primary ext2 2048s -1 set " + appvgpart + " lvm on print\""
                system(parted_cmd)
                self.reread_partitions(drv)
                if os.path.exists(drv + appvgpart) or os.path.exists(drv + "p" + appvgpart):
                    break

            partpv = drv + appvgpart
            if not os.path.exists(partpv):
                # e.g. /dev/cciss/c0d0p2
                partpv=drv + "p" + appvgpart
            logger.info("Creating physical volume")
            if not os.path.exists(partpv):
                logger.error(partpv + " is not available!")
                sys.exit(1)
            dd_cmd = "dd if=/dev/zero of=\""+ partpv + "\" bs=1024k count=1"
            logger.info(dd_cmd)
            system(dd_cmd)
            system("pvcreate -ff -y \"" + partpv + "\"")
            physical_vols.append(partpv)

        logger.info("Creating volume group AppVG")
        is_first = True
        for drv in physical_vols:
            if is_first:
                system("vgcreate AppVG \"" + drv + "\"")
                is_first = False
            else:
                system("vgextend AppVG \"" + drv +"\"")

        if self.SWAP2_SIZE > 0:
            logger.info("Creating swap2 partition")
            lv_cmd = "lvcreate --name Swap2 --size \"" + str(self.SWAP2_SIZE) + "M\" /dev/AppVG"
            logger.debug(lv_cmd)
            system(lv_cmd)
            if OVIRT_VARS.has_key("OVIRT_CRYPT_SWAP2"):
                os.system("echo \"SWAP2 /dev/AppVG/Swap2 /dev/mapper/ovirt-crypt-swap2 " + OVIRT_VARS["OVIRT_CRYPT_SWAP2"] + "\" >> /etc/ovirt-crypttab")
            else:
                system("mkswap -L \"SWAP2\" /dev/AppVG/Swap2")
                os.system("echo \"/dev/AppVG/Swap2 swap swap defaults 0 0\" >> /etc/fstab")

        use_data = "1"
        if self.DATA2_SIZE == -1:
            logger.info("Creating data2 partition with remaining free space")
            system("lvcreate --name Data2 -l 100%FREE /dev/AppVG")
            use_data = 0
        elif self.DATA2_SIZE > 0:
            logger.info("Creating data2 partition")
            system("lvcreate --name Data2 --size " + str(self.DATA2_SIZE) + "M /dev/AppVG")
            use_data = 0

        if use_data == 0:
            system("mke2fs -j -t ext4 /dev/AppVG/Data2 -L \"DATA2\"")
            system("tune2fs -c 0 -i 0 /dev/AppVG/Data2")
            os.system("echo \"/dev/AppVG/Data2 /data2 ext4 defaults,noatime 0 0\" >> /etc/fstab")
            logger.info("Mounting data2 partition")
            mount_data2()
            logger.info("Completed AppVG!")
            return True

    def perform_partitioning(self):
        if self.HOSTVGDRIVE is None and not is_iscsi_install():
            logger.error("\nNo storage device selected.")
            return False

        if self.BOOTDRIVE is None and is_iscsi_install():
            logger.error("No storage device selected.")
            return False

        if has_fakeraid(self.HOSTVGDRIVE):
            if not handle_fakeraid(self.HOSTVGDRIVE):
                return False
        if has_fakeraid(self.ROOTDRIVE):
            if not handle_fakeraid(self.ROOTDRIVE):
                return False

        logger.info("Saving parameters")
        unmount_config("/etc/default/ovirt")

        logger.info("Removing old LVM partitions")
        # HostVG must not exist at this point
        # we wipe only foreign LVM here
        logger.info("Wiping LVM on HOSTVGDRIVE %s" % self.HOSTVGDRIVE)
        self.wipe_lvm_on_disk(self.HOSTVGDRIVE)
        logger.info("Wiping LVM on ROOTDRIVE %s" % self.ROOTDRIVE)
        self.wipe_lvm_on_disk(self.ROOTDRIVE)
        logger.info("Wiping LVM on BOOTDRIVE %s" % self.BOOTDRIVE)
        self.wipe_lvm_on_disk(self.BOOTDRIVE)
        self.boot_size_si = self.BOOT_SIZE * (1024 * 1024) / (1000 * 1000)
        if is_iscsi_install():
            # login to target and setup disk"
            get_targets = "iscsiadm -m discovery -p %s:%s -t sendtargets" % (OVIRT_VARS["OVIRT_ISCSI_TARGET_HOST"],OVIRT_VARS["OVIRT_ISCSI_TARGET_PORT"])
            system(get_targets)
            before_login_drvs = self.get_dev_name()
            logger.debug(before_login_drvs)
            login_cmd = "iscsiadm -m node -T %s -p %s:%s -l" % (OVIRT_VARS["OVIRT_ISCSI_TARGET_NAME"], OVIRT_VARS["OVIRT_ISCSI_TARGET_HOST"], OVIRT_VARS["OVIRT_ISCSI_TARGET_PORT"])
            system(login_cmd)
            system("multipath -r")
            after_login_drvs = self.get_dev_name()
            logger.debug(after_login_drvs)
            logger.info("iSCSI enabled, partitioning boot drive: %s" % self.BOOTDRIVE)
            wipe_partitions(self.BOOTDRIVE)
            self.reread_partitions(self.BOOTDRIVE)
            logger.info("Creating boot partition")
            parted_cmd="parted %s -s \"mklabel %s\"" % (self.BOOTDRIVE, self.LABEL_TYPE)
            system(parted_cmd)
            parted_cmd="parted \"%s\" -s \"mkpart primary ext2 1M 256M\"" % self.BOOTDRIVE
            system(parted_cmd)
            parted_cmd="parted \"%s\" -s \"mkpart primary ext2 256M 512M\"" % self.BOOTDRIVE
            system(parted_cmd)
            parted_cmd = "parted \""+self.BOOTDRIVE+"\" -s \"set 1 boot on\""
            system(parted_cmd)
            self.reread_partitions(self.BOOTDRIVE)
            partboot= self.BOOTDRIVE + "1"
            if not os.path.exists(partboot):
                logger.debug("%s does not exist" % partboot)
                partboot = self.BOOTDRIVE + "p1"
            partbootbackup= self.BOOTDRIVE + "2"
            if not os.path.exists(partbootbackup):
                logger.debug("%s does not exist" % partbootbackup)
                partbootbackup = self.BOOTDRIVE + "p2"
            # sleep to ensure filesystems are created before continuing
            system("udevadm settle")
            time.sleep(10)
            system("mke2fs \""+str(partboot)+"\" -L Boot")
            system("tune2fs -c 0 -i 0 \""+str(partboot)+"\"")
            system("ln -snf \""+partboot+"\" /dev/disk/by-label/Boot")
            system("mke2fs \""+str(partbootbackup)+"\" -L BootBackup")
            system("tune2fs -c 0 -i 0 \""+str(partbootbackup)+"\"")
            system("ln -snf \""+partbootbackup+"\" /dev/disk/by-label/BootBackup")
            self.ISCSIDRIVE =  translate_multipath_device(OVIRT_VARS["OVIRT_ISCSI_INIT"])
            logger.debug(self.ISCSIDRIVE)
            if self.create_iscsiroot():
                logger.info("iSCSI Root Partitions Created")
                if self.create_hostvg():
                    logger.info("Completed!")
                    return True

        if OVIRT_VARS.has_key("OVIRT_ROOT_INSTALL") and OVIRT_VARS["OVIRT_ROOT_INSTALL"] == "y":
            logger.info("Partitioning root drive: " + self.ROOTDRIVE)
            wipe_partitions(self.ROOTDRIVE)
            self.reread_partitions(self.ROOTDRIVE)
            logger.info("Labeling Drive: " + self.ROOTDRIVE)
            parted_cmd = "parted \""+ self.ROOTDRIVE +"\" -s \"mklabel "+ self.LABEL_TYPE+"\""
            logger.debug(parted_cmd)
            system(parted_cmd)
            logger.debug("Creating Root and RootBackup Partitions")
            # efi partition should at 0M
            if is_efi_boot():
                efi_start = 0
                parted_cmd = "parted \"" + self.ROOTDRIVE + "\" -s \"mkpart EFI " + str(efi_start) + "M " + str(self.EFI_SIZE)+"M\""
                logger.debug(parted_cmd)
                system(parted_cmd)
            else:
                efi_start = 1
                # create partition labeled bios_grub
                parted_cmd = "parted \"" + self.ROOTDRIVE + "\" -s \"mkpart primary " + str(efi_start) + "M " + str(self.EFI_SIZE)+"M\""
                logger.debug(parted_cmd)
                system(parted_cmd)
                parted_cmd = "parted \"" + self.ROOTDRIVE + "\" -s \"set 1 bios_grub on\""
                logger.debug(parted_cmd)
                system(parted_cmd)
            parted_cmd = "parted \"" + self.ROOTDRIVE + "\" -s \"mkpart primary ext2 "+str(self.EFI_SIZE)+"M "+ str(self.Root_end)+"M\""
            logger.debug(parted_cmd)
            system(parted_cmd)
            parted_cmd = "parted \""+self.ROOTDRIVE+"\" -s \"mkpart primary ext2 "+str(self.Root_end)+"M "+str(self.RootBackup_end)+"M\""
            logger.debug(parted_cmd)
            system(parted_cmd)
            parted_cmd = "parted \""+self.ROOTDRIVE+"\" -s \"set 2 boot on\""
            logger.debug(parted_cmd)
            system(parted_cmd)
            # sleep to ensure filesystems are created before continuing
            time.sleep(5)
            # force reload some cciss devices will fail to mkfs
            system("multipath -r")
            self.reread_partitions(self.ROOTDRIVE)
            partefi = self.ROOTDRIVE + "1"
            partroot = self.ROOTDRIVE + "2"
            partrootbackup = self.ROOTDRIVE + "3"
            if not os.path.exists(partroot):
                partefi = self.ROOTDRIVE + "p1"
                partroot = self.ROOTDRIVE + "p2"
                partrootbackup= self.ROOTDRIVE + "p3"
            if is_efi_boot():
                system("ln -snf \""+partefi+"\" /dev/disk/by-label/EFI")
                system("mkfs.vfat \""+partefi+"\" -n EFI -F32")
            system("ln -snf \""+partroot+"\" /dev/disk/by-label/Root")
            system("mke2fs \""+partroot+"\" -L Root")
            system("tune2fs -c 0 -i 0 \""+partroot+"\"")
            system("ln -snf \""+partrootbackup+"\" /dev/disk/by-label/RootBackup")
            system("mke2fs \""+partrootbackup+"\" -L RootBackup")
            system("tune2fs -c 0 -i 0 \""+partrootbackup+"\"")
        hostvg1=self.HOSTVGDRIVE.split(",")[0]
        self.reread_partitions(self.ROOTDRIVE)
        if self.ROOTDRIVE != hostvg1 :
            system("parted \"" + hostvg1 +"\" -s \"mklabel " + self.LABEL_TYPE + "\"")
        if self.create_hostvg():
            if len(self.APPVGDRIVE) > 0:
                self.create_appvg()
        else:
            return False
        if OVIRT_VARS.has_key("OVIRT_CRYPT_SWAP2") or OVIRT_VARS.has_key("OVIRT_CRYPT_SWAP"):
            ovirt_store_config("/etc/ovirt-crypttab")
        return True

    def check_partition_sizes(self):
        drive_list = []
        drive_space_dict = {}
        min_data_size = self.DATA_SIZE
        if self.DATA_SIZE == -1 :
            min_data_size=5

        if is_iscsi_install():
            BOOTDRIVESPACE = self.get_drive_size(self.BOOTDRIVE)
            drive_list.append("BOOT")
            drive_space_dict["BOOTDRIVESPACE"] = BOOTDRIVESPACE
            drive_space_dict["BOOT_NEED_SIZE"] = self.BOOT_SIZE
        else:
            ROOTDRIVESPACE = self.get_drive_size(self.ROOTDRIVE)
            for drive in self.HOSTVGDRIVE.split(","):
                space = self.get_drive_size(drive)
                HOSTVGDRIVESPACE = HOSTVGDRIVESPACE + space
            ROOT_NEED_SIZE=self.ROOT_SIZE * 2
            HOSTVG_NEED_SIZE= int(self.SWAP_SIZE) + int(self.CONFIG_SIZE) + int(self.LOGGING_SIZE) + int(min_data_size)
            drive_space_dict["ROOTDRIVESPACE"] = ROOTDRIVESPACE
            drive_space_dict["ROOT_NEED_SIZE"] = ROOT_NEED_SIZE
            drive_space_dict["HOSTVGDRIVESPACE"] = HOSTVGDRIVESPACE
            drive_space_dict["HOSTVG_NEED_SIZE"] = HOSTVG_NEED_SIZE
            hostvg1=self.HOSTVGDRIVE.split(",")[0]
            if self.ROOTDRIVE == hostvg1:
                drive_list.append("ROOT")
                ROOT_NEED_SIZE=self.ROOT_SIZE * 2 + HOSTVG_NEED_SIZE
                drive_space_dict["ROOT_NEED_SIZE"] = ROOT_NEED_SIZE
            else:
                drive_list.append("ROOT")
                drive_list.append("HOSTVG")

            for drive in drive_list:
                drive_need_size = drive_space_dict[drive + "_NEED_SIZE"]
                drive_disk_size= drive_space_dict[drive + "DRIVESPACE"]

            if drive_need_size > drive_disk_size:
                gap_size = drive_need_size - drive_disk_size
                logger.error("The target storage device is too small for the desired sizes:")
                logger.error(" Disk Target: " + drive)
                logger.error(" Size of target storage device: " + str(drive_disk_size) + "MB")
                logger.error(" Total storage size to be used: " + str(drive_need_size) + "MB")
                logger.error("You need an additional " + str(gap_size) + "MB of storage.")
                sys.exit(1)
            else:
                logger.info("Required Space : " + str(drive_need_size) + "MB")

def wipe_fakeraid(device):
    dmraid_cmd = "echo y | dmraid -rE $(readlink -f \"%s\")" % device
    dmraid=subprocess.Popen(dmraid_cmd, stdout=PIPE, stderr=STDOUT, shell=True)
    dmraid.communicate()
    dmraid.poll()
    if dmraid.returncode == 0:
        return True
    else:
        return False

def handle_fakeraid(device):
    if is_wipe_fakeraid():
        return wipe_fakeraid(device)
    #don't wipe fakeraid
    logger.error("Fakeraid metadata detected on %s, Aborting install." % device)
    logger.error("If you want auto-install to wipe the fakeraid metadata automatically,")
    logger.error("then boot with the wipe-fakeraid option on the kernel commandline.")
    return False

def storage_auto():
    storage = Storage()
    if not OVIRT_VARS["OVIRT_INIT"] == "":
        #force root install variable for autoinstalls
        OVIRT_VARS["OVIRT_ROOT_INSTALL"] = "y"
        if storage.perform_partitioning():
            return True
        else:
            return False
    else:
        logger.error("Storage Device Is Required for Auto Installation")
