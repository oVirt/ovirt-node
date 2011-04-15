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

class Storage:
    def __init__(self):
        OVIRT_VARS = parse_defaults()
        self.overcommit=0.5
        self.BOOT_SIZE=50
        self.ROOT_SIZE=256
        self.CONFIG_SIZE=5
        self.LOGGING_SIZE=2048
        self.SWAP_SIZE=""
        self.BOOTDRIVE = ""
        self.HOSTVGDRIVE = ""
        self.RootBackup_end = self.ROOT_SIZE * 2
        # -1 indicates data partition should use remaining disk
        self.DATA_SIZE = -1
        # if the node is Fedora then use GPT, otherwise use MBR
        if os.path.isfile("/etc/fedora-release"):
            self.LABEL_TYPE="gpt"
        else:
            self.LABEL_TYPE="msdos"
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
                self.ROOTDRIVE = OVIRT_VARS["OVIRT_INIT"]
                self.HOSTVGDRIVE = OVIRT_VARS["OVIRT_INIT"]

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

    def get_drive_size(self, drive):
        size_cmd = "sfdisk -s " + drive + " 2>null"
        size = subprocess.Popen(size_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        size = size.stdout.read()
        size = int(int(size) / 1024)
        return size


    def wipe_lvm_on_disk(self, dev):
        unmount_logging()
        part_delim="p"
        if "/dev/sd" in dev:
            part_delim=""
        vg_cmd = "pvs -o vg_uuid --noheadings %s \"%s%s[0-9]\"* 2>/dev/null|sort -u" % (dev, dev, part_delim) 
        vg = subprocess.Popen(vg_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        vg_output = vg.stdout.read()
        for vg in vg_output:
            pvs = system("pvscan -o pv_name,vg_uuid --noheadings | grep \"%s\" | egrep -v -q \"%s%s[0-9]+|%s \"") % (vg, dev, part_delim, dev)
            if pvs > 0:
                log("The volume group \"%s\" spans multiple disks.") % vg
                log("This operation cannot complete.  Please manually")
                log("cleanup the storage using standard disk tools.")
                sys.exit(1)
            wipe_volume_group(vg)
        return


    def reread_partitions(self, drive):
        if "dev/mapper" in drive:
            # kpartx -a -p p "$drive"
            # XXX fails with spaces in device names (TBI)
            # ioctl(3, DM_TABLE_LOAD, 0x966980) = -1 EINVAL (Invalid argument)
            # create/reload failed on 0QEMU    QEMU HARDDISK   drive-scsi0-0-0p1
            os.system("partprobe &>/dev/null")
            # partprobe fails on cdrom:
            # Error: Invalid partition table - recursive partition on /dev/sr0.
            system("service multipathd reload")

        else:
            os.system("blockdev --rereadpt " + drive + " &>>/dev/null")


    def get_sd_name(self, id):
        device_sys_cmd = "grep -H \"^%s$\" /sys/block/*/dev | cut -d: -f1" % id
        device_sys = subprocess.Popen(device_sys_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        device_sys_output = device_sys.stdout.read().strip()
        if not device_sys_output is "":
            device = os.path.basename(device_sys_output)
            return device
        return False


    # gets the dependent block devices for multipath devices
    def get_multipath_deps(self, mpath_device, deplist_var):
        return
        deplist=""
        #get dependencies for multipath device
        deps_cmd ="dmsetup deps -u \"mpath-%s\" \
        | sed -r 's/\(([0-9]+), ([0-9]+)\)/\1:\2/g' \
        | sed 's/ /\n/g' | grep [0-9]:[0-9] 2>/dev/null" % mpath_device
        deps = subprocess.Popen(deps_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        deps_output = deps.stdout.read()
        for dep in deps_output.split():
            device=get_sd_name(dep)
            dep_list=[]
            if device is None:
                if deplist is None:
                    deplist = device
                else:
                    deplist.append(device)
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
                devices ="%s /dev/%s " % (devices,d)
            byid_list_cmd = "find /dev/disk/by-id -mindepth 1 -not -name '*-part*' 2>/dev/null"
            byid_list = subprocess.Popen(byid_list_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
            byid_list_output = byid_list.stdout.read()
        for d in byid_list_output.split():
            d = os.readlink(d)
            d_basename = os.path.basename(d)
            udev_cmd = "udevadm info --name=/dev/" + d_basename + " --query=property | grep -q ^ID_BUS: &>>/dev/null"
            if os.system(udev_cmd):
                devices="%s /dev/%s " % (devices, d_basename)
        # FIXME: workaround for detecting cciss devices
        if os.path.exists("/dev/cciss"):
            for d in os.listdir("/dev/cciss"):
                if not re.match("p[0-9]+\$", d):
                     devices="%s /dev/cciss/%s" % (devices, d)

        # include multipath devices
        devs_to_remove=""
        multipath_list_cmd = "dmsetup ls --target=multipath | cut -f1"
        multipath_list = subprocess.Popen(multipath_list_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        multipath_list_output = multipath_list.stdout.read()

        for d in multipath_list_output:
            devices="/dev/mapper/%s %s" % (d, devices)
            sd_devs=""
            self.get_multipath_deps(d, sd_devs)

            dm_dev_cmd = "multipath -ll \"%s\" | grep \"%s\" | sed -r 's/^.*(dm-[0-9]+ ).*$/\1/' )" % (d, d)
            dm_dev = subprocess.Popen(dm_dev_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
            dm_dev_output = dm_dev.stdout.read()
            devs_to_remove="%s %s %s" % (devs_to_remove, sd_devs, dm_dev)
        # Remove /dev/sd* devices that are part of a multipath device
        dev_list=[]
        for d in devices.split():
            if os.path.basename(d) not in devs_to_remove:
                 dev_list.append(d)

        for dev in dev_list:
            if dev_list.count(dev) > 1:
                count = dev_list.count(dev)
                while (count > 1):
                    dev_list.remove(dev)
                    count = count - 1
        return dev_list

    def check_partition_sizes(self):
        drive_list = []
        drive_space_dict = {}
        min_data_size = self.DATA_SIZE
        if self.DATA_SIZE == -1 :
            min_data_size=5
        if OVIRT_VARS["OVIRT_ISCSI_ENABLED"] == "y":
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
                log("\n")
                log("=============================================================\n")
                log("The target storage device is too small for the desired sizes:\n")
                log(" Disk Target: " + drive + " \n")
                log(" Size of target storage device: " + drive_disk_size + "MB\n")
                log(" Total storage size to be used: " + drive_need_size + "MB\n")
                log("\n")
                log("You need an additional " + gap_size + "MB of storage.\n")
                log("\n")
                sys.exit(1)
            else:
                log("Required Space : " + drive_need_size + "MB\n\n")
                return True

    def create_hostvg(self):
        log("Creating LVM partition")
        log(self.HOSTVGDRIVE)
        self.physical_vols = []
        for drv in self.HOSTVGDRIVE.split(","):
            if drv != "":
                if self.ROOTDRIVE == drv:
                    parted_cmd = "parted \"" + drv + "\" -s \"mkpart primary ext2 "+ str(self.RootBackup_end) +"M -1\""
                    log(parted_cmd)
                    system(parted_cmd)
                    hostvgpart="3"
                elif self.BOOTDRIVE == drv:
                    parted_cmd = "parted \"" + drv + "\" -s \"mkpart primary ext2 " + str(self.boot_size_si) + " -1\""
                    log(parted_cmd)
                    system(parted_cmd)
                    hostvgpart="2"
                    self.ROOTDRIVE = self.BOOTDRIVE
                else:
                    system("parted \""+ drv +"\" -s \"mklabel "+self.LABEL_TYPE+"\"")
                    parted_cmd = "parted \""+ drv + "\" -s \"mkpart primary ext2 0M -1 \""
                    log(parted_cmd)
                    system(parted_cmd)
                    hostvgpart = "1"
                log("Toggling LVM on")
                parted_cmd = "parted " + self.HOSTVGDRIVE +  " -s \"set " + str(hostvgpart) + " lvm on\""
                system(parted_cmd)
                system("parted \"" + self.ROOTDRIVE + "\" -s \"print\"")
                os.system("udevadm settle 2> /dev/null || udevsettle &>/dev/null")
                self.reread_partitions(drv)

                # sync GPT to the legacy MBR partitions
                if OVIRT_VARS.has_key("OVIRT_INSTALL_ROOT") and OVIRT_VARS["OVIRT_INSTALL_ROOT"] == "y" :
                    if self.LABEL_TYPE == "gpt":
                        log("Running gptsync to create legacy mbr")
                        system("gptsync \"" + self.ROOTDRIVE + "\"")

                partpv = drv + hostvgpart
                if not os.path.exists(partpv):
                    # e.g. /dev/cciss/c0d0p2
                    partpv = drv + "p" + hostvgpart
                self.physical_vols.append(partpv)
        drv_count = 0
        log(self.physical_vols)
        for partpv in self.physical_vols:
            log("Creating physical volume on " + partpv)
            if not os.path.exists(partpv):
                log(partpv + "is not available!")
                return False
            if not system("dd if=/dev/zero of=\"" + partpv + "\" bs=1024k count=1"):
                log("Failed to wipe lvm partition")
            if not system("pvcreate -ff -y \"" + partpv + "\""):
                log("Failed to pvcreate on " + partpv)
                return False
            if drv_count < 1:
                log("Creating volume group on " + partpv)
                if not system("vgcreate /dev/HostVG \"" + partpv + "\""):
                    log("Failed to vgcreate /dev/HostVG on " + partpv)
                    return False
            else:
                log("Extending volume group on " + partpv)
                if not system("vgextend /dev/HostVG \"" + partpv + "\""):
                    log("Failed to vgextend /dev/HostVG on " + partpv)
                    return False
            drv_count = drv_count + 1
        if self.SWAP_SIZE > 0:
            log("Creating swap partition")
            system("lvcreate --name Swap --size "+str(self.SWAP_SIZE) + "M /dev/HostVG")
            system("mkswap -L \"SWAP\" /dev/HostVG/Swap")
            os.system("echo \"/dev/HostVG/Swap swap swap defaults 0 0\" >> /etc/fstab")
        if self.CONFIG_SIZE > 0:
            log("Creating config partition")
            system("lvcreate --name Config --size "+str(self.CONFIG_SIZE)+"M /dev/HostVG")
            system("mke2fs -j /dev/HostVG/Config -L \"CONFIG\"")
            system("tune2fs -c 0 -i 0 /dev/HostVG/Config")
        if self.LOGGING_SIZE > 0:
            log("Creating log partition")
            system("lvcreate --name Logging --size "+str(self.LOGGING_SIZE)+"M /dev/HostVG")
            system("mke2fs -j /dev/HostVG/Logging -L \"LOGGING\"")
            system("tune2fs -c 0 -i 0 /dev/HostVG/Logging")
            os.system("echo \"/dev/HostVG/Logging /var/log ext3 defaults,noatime 0 0\" >> /etc/fstab")
        use_data=1
        if self.DATA_SIZE == -1:
            log("Creating data partition with remaining free space")
            system("lvcreate --name Data -l 100%FREE /dev/HostVG")
            use_data=0
        elif self.DATA_SIZE > 0:
            log("Creating data partition")
            system("lvcreate --name Data --size "+str(self.DATA_SIZE)+"M /dev/HostVG")
            use_data=0
        if use_data == 0:
            system("mke2fs -j /dev/HostVG/Data -L \"DATA\"")
            system("tune2fs -c 0 -i 0 /dev/HostVG/Data")
            os.system("echo \"/dev/HostVG/Data /data ext3 defaults,noatime 0 0\" >> /etc/fstab")
            os.system("echo \"/data/images /var/lib/libvirt/images bind bind 0 0\" >> /etc/fstab")
            os.system("echo \"/data/core /var/log/core bind bind 0 0\" >> /etc/fstab")

        log("Mounting config partition")
        mount_config()
        if os.path.ismount("/config"):
            ovirt_store_config("/etc/fstab")

        mount_logging()
        if use_data == 0:
            log("Mounting data partition")
            mount_data()
        log("Completed!")
        return True

    def perform_partitioning(self):
        if self.HOSTVGDRIVE is None and OVIRT_VARS["OVIRT_ISCSI_ENABLED"] != "y":
            log("\nNo storage device selected.\n")
            return False

        if self.BOOTDRIVE is None and OVIRT_VARS["OVIRT_ISCSI_ENABLED"] == "y":
            log("\nNo storage device selected.\n")
            return False

        log("Saving parameters")
        unmount_config("/etc/default/ovirt")

        log("Removing old LVM partitions")
        wipe_volume_group("HostVG")
        self.wipe_lvm_on_disk(self.HOSTVGDRIVE)
        self.wipe_lvm_on_disk(self.ROOTDRIVE)
        self.boot_size_si = self.BOOT_SIZE * (1024 * 1024) / (1000 * 1000)
        if OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED") and OVIRT_VARS["OVIRT_ISCSI_ENABLED"] == "y":
            log("iSCSI enabled, partitioning boot drive: $BOOTDRIVE")
            wipe_partitions(self.BOOTDRIVE)
            reread_partitions(self.BOOTDRIVE)
            log("Creating boot partition")
            system("parted \""+ self.BOOTDRIVE+"\" -s \"mklabel "+self.LABEL_TYPE+"\"")
            system("parted \""+self.BOOTDRIVE+"\" -s \"mkpartfs primary ext2 0M "+ self.boot_size_si+"%sM\"")
            reread_partitions(self.BOOTDRIVE)
            partboot= self.BOOTDRIVE + "1"
            if not os.path.exists(partboot):
                partboot = self.BOOTDRIVE + "p1"
            # sleep to ensure filesystems are created before continuing
            time.sleep(10)
            system("mke2fs \"" + str(partboot) +"\" -L Boot")
            system("tune2fs -c 0 -i 0 " + str(partboot))
            if OVIRT_VARS["OVIRT_ISCSI_HOSTVG"] == "y":
                self.create_hostvg()
            log("Completed!")
            return
        if OVIRT_VARS.has_key("OVIRT_ROOT_INSTALL") and OVIRT_VARS["OVIRT_ROOT_INSTALL"] == "y":
            log("Partitioning root drive: " + self.ROOTDRIVE)
            wipe_partitions(self.ROOTDRIVE)
            self.reread_partitions(self.ROOTDRIVE)
            log("Labeling Drive: " + self.ROOTDRIVE)
            parted_cmd = "parted \""+ self.ROOTDRIVE +"\" -s \"mklabel "+ self.LABEL_TYPE+"\""
            log(parted_cmd)
            system(parted_cmd)
            log("Creating Root and RootBackup Partitions")
            parted_cmd = "parted \"" + self.ROOTDRIVE + "\" -s \"mkpart primary ext2 0M "+ str(self.ROOT_SIZE)+"M\""
            log(parted_cmd)
            system(parted_cmd)
            parted_cmd = "parted \""+self.ROOTDRIVE+"\" -s \"mkpart primary ext2 "+str(self.ROOT_SIZE)+"M "+str(self.RootBackup_end)+"M\""
            log(parted_cmd)
            system(parted_cmd)
            # sleep to ensure filesystems are created before continuing
            time.sleep(5)
            # force reload some cciss devices will fail to mkfs
            system("multipath -r")
            self.reread_partitions(self.ROOTDRIVE)
            partroot = self.ROOTDRIVE + "1"
            partrootbackup = self.ROOTDRIVE + "2"
            if not os.path.exists(partroot):
                partroot = self.ROOTDRIVE + "p1"
                partrootbackup= self.ROOTDRIVE + "p2"
            system("ln -snf " + partroot + " /dev/disk/by-label/Root")
            system("mke2fs \""+partroot+"\" -L Root")
            system("ln -snf " + partrootbackup + " /dev/disk/by-label/RootBackup")
            system("mke2fs \""+partrootbackup+"\" -L RootBackup")
            system("tune2fs -c 0 -i 0 \""+partroot+"\"")
            system("tune2fs -c 0 -i 0 \""+partrootbackup+"\"")

        if self.ROOTDRIVE != self.HOSTVGDRIVE:
            system("parted \"" + self.HOSTVGDRIVE +"\" -s \"mklabel " + self.LABEL_TYPE + "\"")
        if self.create_hostvg():
            return True
        else:
            return False

    def check_partition_sizes(self):
        drive_list = []
        drive_space_dict = {}
        min_data_size = self.DATA_SIZE
        if self.DATA_SIZE == -1 :
            min_data_size=5

        if OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED"):
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
            if self.ROOTDRIVE == self.HOSTVGDRIVE:
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
                log("\n")
                log("=============================================================\n")
                log("The target storage device is too small for the desired sizes:\n")
                log(" Disk Target: " + drive + " \n")
                log(" Size of target storage device: " + str(drive_disk_size) + "MB\n")
                log(" Total storage size to be used: " + str(drive_need_size) + "MB\n")
                log("\n")
                log("You need an additional " + str(gap_size) + "MB of storage.\n")
                log("\n")
                sys.exit(1)
            else:
                log("Required Space : " + str(drive_need_size) + "MB\n\n")

if __name__ == "__main__":
    storage = Storage()
    OVIRT_VARS = parse_defaults()
    # do not format if HostVG exists on selected disk...
    print OVIRT_VARS
    existingHostVG = storage.check_existing_hostvg(OVIRT_VARS["OVIRT_INIT"])
    print existingHostVG
    a = storage.perform_partitioning()
    print a

"""
    try:
        OVIRT_VARS = parse_defaults()
        if sys.argv[1] == "AUTO":
            log("Beginning automatic disk partitioning.")
            
            if not OVIRT_VARS["OVIRT_INIT"] is None:
                storage = Storage()
                # do not format if HostVG exists on selected disk...
                existingHostVG = storage.check_existing_hostvg(OVIRT_VARS["OVIRT_INIT"])
                # ... unless overridden by ovirt_firstboot parameter
                if is_firstboot or existingHostVG == False:
                    if storage.check_partition_sizes():
                        log("Partitioning hard disk...")
                        storage.perform_partitioning()
                    else:
                        log("Skip disk partitioning, HostVG exists")
                        sys.exit(1)
        else:
            log("Missing device parameter: unable to partition any disk")
            sys.exit(2)

    except:
        print "Storage Configuration Failed check ovirt.log for details"
        sys.exit(1)
"""
