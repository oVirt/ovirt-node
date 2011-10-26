#!/usr/bin/python
# install.py - Copyright (C) 2010 Red Hat, Inc.
# Written by Joey Boggs <jboggs@redhat.com>
#
# This program is free softwaee; you can redistribute it and/or modify
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

# SYNOPSIS
# ovirt-config-boot livecd_path bootparams reboot
#
#       livecd_path - where livecd media is mounted,
#                     parent of LiveOS and isolinux folders
#                     default is /live
#
#       bootparams  - extra boot parameters like console=...
#                     default is $OVIRT_BOOTPARAMS
#
#       reboot      - reboot after install
#                     default is yes

from ovirtnode.ovirtfunctions import *
from ovirtnode.iscsi import *
import shutil
import sys
import traceback
import os
import stat
import subprocess
import re
OVIRT_VARS = parse_defaults()

def ovirt_boot_setup():
    log("installing the image.")

    if OVIRT_VARS.has_key("OVIRT_ROOT_INSTALL"):
        if OVIRT_VARS["OVIRT_ROOT_INSTALL"] == "n":
            log("done.")
            return True

    if OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED") and OVIRT_VARS["OVIRT_ISCSI_ENABLED"] == "y":
        initrd_dest = "/boot"
        grub_dir = "/boot/grub"
        grub_prefix = "/grub"
    else:
        initrd_dest = "/liveos"
        grub_dir = "/liveos/grub"
        grub_prefix = "/grub"

    oldtitle=None
    if os.path.ismount("/liveos"):
        if os.path.exists("/liveos/vmlinuz0") and os.path.exists("/liveos/initrd0.img"):
            f=open("/liveos/grub/grub.conf")
            oldgrub=f.read()
            f.close()
            m=re.search("^title (.*)$", oldgrub, re.MULTILINE)
            if m is not None:
                oldtitle=m.group(1)

        system("umount /liveos")
    candidate=""
    if findfs("Boot"):
        candidate = "Boot"
        mount_boot()
        if not os.path.ismount("/boot"):
            log("Boot partition not available")
            return False
        # Grab OVIRT_ISCSI VARIABLES from boot partition for upgrading
        # file created only if OVIRT_ISCSI_ENABLED=y
        if os.path.exists("/boot/ovirt"):
            try:
                f = open("/boot/ovirt", 'r')
                for line in f:
                    try:
                        line = line.strip()
                        key, value = line.split("\"", 1)
                        key = key.strip("=")
                        key = key.strip()
                        value = value.strip("\"")
                        OVIRT_VARS[key] = value
                    except:
                        pass
                f.close()
                iscsiadm_cmd = "iscsiadm -p %s:%s -m discovery -t sendtargets" % (OVIRT_VARS["OVIRT_ISCSI_TARGET_IP"], OVIRT_VARS["OVIRT_ISCSI_TARGET_PORT"])
                system(iscsiadm_cmd)
                log("Restarting iscsi service")
                system("service iscsi restart")
            except:
                pass
    elif findfs("RootBackup"):
        candidate = "RootBackup"
    elif findfs("RootUpdate"):
        candidate = "RootUpdate"
    elif findfs("RootNew"):
        candidate = "RootNew"
    else:
        log("Unable to find Root partition")
        label_debug = ''
        for label in os.listdir("/dev/disk/by-label"):
            label_debug += "%s\n" % label
        label_debug += subprocess.Popen("blkid", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.read()
        log(label_debug)
        return False

    log("candidate: " + candidate)
    disk = None
    partN = -1
    try:
        candidate_dev = disk = findfs(candidate)
        partN = int(disk[-1:]) - 1
        log("partN: %d" % partN)
    except:
        log(traceback.format_exc())
        return False

    if disk is None or partN < 0:
        log("Failed to determine Root partition number")
        return False
    if not OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED"):
        # prepare Root partition update
        if candidate != "RootNew":
            e2label_cmd = "e2label \"%s\" RootNew" % candidate_dev
            log(e2label_cmd)
            if not system(e2label_cmd):
                log("Failed to label new Root partition")
                return False
        mount_cmd = "mount \"%s\" /liveos" % candidate_dev
        system(mount_cmd)
        system("rm -rf /liveos/LiveOS")
        system("mkdir -p /liveos/LiveOS")
        mount_live()
    # install oVirt Node image for local boot
    if os.path.exists("/live/syslinux"):
        syslinux = "syslinux"
    elif os.path.exists("/live/isolinux"):
        syslinux = "isolinux"
    else:
        return False

    if os.path.isdir(grub_dir):
        shutil.rmtree(grub_dir)
    if not os.path.exists(grub_dir):
        os.makedirs(grub_dir)
        os.makedirs(grub_dir + "/efi")
        system("mount LABEL=EFI "+grub_dir+"/efi")
        system("cp -ra /boot/efi/* " + grub_dir + "/efi")
    if not system("cp -p /live/" + syslinux + "/vmlinuz0 " + initrd_dest):
        log("kernel image copy failed.")
        return False
    if not system("cp -p /live/" + syslinux + "/initrd0.img " + initrd_dest):
        log("initrd image copy failed.")
        return False
    if not system("cp -p /live/" + syslinux + "/version /liveos"):
        log("version details copy failed.")
        return False

    if not OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED"):
        if not system("cp -p /live/LiveOS/squashfs.img /liveos/LiveOS"):
            log("squashfs image copy failed.")
            return False
    # reorder tty0 to allow both serial and phys console after installation
    if OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED") and OVIRT_VARS["OVIRT_ISCSI_ENABLED"] == "y":
        root_param="root=LABEL=ovirt-node-root"
        bootparams="ro rootfstype=ext2 rootflags=ro console=tty0 \
                    netroot=iscsi:$OVIRT_ISCSI_TARGET_IP::$OVIRT_ISCSI_TARGET_PORT::$OVIRT_ISCSI_NODE_NAME ip=eth0:dhcp"
    else:
        root_param="root=live:LABEL=Root"
        bootparams="ro rootfstype=auto rootflags=ro "
    bootparams += OVIRT_VARS["OVIRT_BOOTPARAMS"].replace("console=tty0","")
    if " " in disk or os.path.exists("/dev/cciss"):
        # workaround for grub setup failing with spaces in dev.name:
        # use first active sd* device
        disk = re.sub("p[1,2,3]$", "", disk)
        grub_disk_cmd= "multipath -l \"" + os.path.basename(disk) + "\" | awk '/ active / {print $3}' | head -n1"
        log(grub_disk_cmd)
        grub_disk = subprocess.Popen(grub_disk_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        disk = grub_disk.stdout.read().strip()
        if "cciss" in disk:
            disk = disk.replace("!","/")
        # flush to sync DM and blockdev, workaround from rhbz#623846#c14
        sysfs=open("/proc/sys/vm/drop_caches","w")
        sysfs.write("3")
        sysfs.close()
        partprobe_cmd="partprobe \"/dev/%s\"" % disk
        log(partprobe_cmd)
        system(partprobe_cmd)

    if not disk.startswith("/dev/"):
        disk = "/dev/" + disk
    try:
        if stat.S_ISBLK(os.stat(disk).st_mode):
            try:
                if stat.S_ISBLK(os.stat(disk[:-1]).st_mode):
                    # e.g. /dev/sda2
                    disk = disk[:-1]
            except OSError:
                pass
            try:
                if stat.S_ISBLK(os.stat(disk[:-2]).st_mode):
                    # e.g. /dev/mapper/WWIDp2
                    disk = disk[:-2]
            except OSError:
                pass
    except OSError:
        log("Unable to determine disk for grub installation " + traceback.format_exc())
        return False

    device_map = "(hd0) %s" % disk
    log(device_map)
    device_map_conf = open(grub_dir + "/device.map", "w")
    device_map_conf.write(device_map)
    device_map_conf.close()

    GRUB_CONFIG_TEMPLATE = """
default saved
timeout 5
hiddenmenu
title %(product)s %(version)s-%(release)s
    root (hd0,%(partN)d)
    kernel /vmlinuz0 %(root_param)s %(bootparams)s
    initrd /initrd0.img
    """
    GRUB_BACKUP_TEMPLATE = """
title BACKUP %(oldtitle)s
    root (hd0,%(partB)d)
    kernel /vmlinuz0 root=live:LABEL=RootBackup %(bootparams)s
    initrd /initrd0.img
    """
    GRUB_SETUP_TEMPLATE = """
    grub --device-map=%(grub_dir)s/device.map <<EOF
root (hd0,%(partN)d)
setup --prefix=%(grub_prefix)s (hd0)
EOF
"""

    grub_dict = {
        "product" : PRODUCT_SHORT,
        "version" : PRODUCT_VERSION,
        "release" : PRODUCT_RELEASE,
        "partN" : partN,
        "root_param" : root_param,
        "bootparams" : bootparams,
        "disk" : disk,
        "grub_dir" : grub_dir,
        "grub_prefix" : grub_prefix
    }
    grub_config_file = "%s/grub.conf" % grub_dir
    grub_conf = open(grub_config_file, "w")
    grub_conf.write(GRUB_CONFIG_TEMPLATE % grub_dict)
    if oldtitle is not None:
        partB=0
        if partN == 0:
            partB=1
        grub_dict['oldtitle']=oldtitle
        grub_dict['partB']=partB
        grub_conf.write(GRUB_BACKUP_TEMPLATE % grub_dict)
    grub_conf.close()
    for f in ["stage1", "stage2", "e2fs_stage1_5"]:
        system("cp /usr/share/grub/x86_64-redhat/%s %s" % (f, grub_dir))
    grub_setup_out = GRUB_SETUP_TEMPLATE % grub_dict
    log(grub_setup_out)
    grub_setup = subprocess.Popen(grub_setup_out, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    grub_results = grub_setup.stdout.read()
    log(grub_results)
    if grub_setup.wait() != 0 or "Error" in grub_results:
        log("GRUB setup failed")
        return False
    if OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED") \
       and OVIRT_VARS["OVIRT_ISCSI_ENABLED"] == "y":
        # copy default for when Root/HostVG is inaccessible(iscsi upgrade)
        shutil.copy(OVIRT_DEFAULTS, "/boot")
    else:
        system("sync")
        system("sleep 2")
        system("umount /liveos")
        # mark new Root ready to go, reboot() in ovirt-function switches it to active
        e2label_cmd = "e2label \"%s\" RootUpdate" % candidate_dev
        if not system(e2label_cmd):
            log("Unable to relabel " + candidate_dev + " to RootUpdate ")
            return False
    disable_firstboot()
    if finish_install():
        log("generating iscsi iqn and persisting")
        iscsi_iqn_cmd = subprocess.Popen("/sbin/iscsi-iname", stdout=PIPE)
        iscsi_iqn, err = iscsi_iqn_cmd.communicate()
        set_iscsi_initiator(iscsi_iqn.strip())
        log("done.")
        return True
    else:
        return False

def Usage():

    print "Usage: %s [livecd_path] [bootparams] [reboot(yes/no)]" % sys.argv[0]
    print "       livecd_path - where livecd media is mounted parent of LiveOS"
    print "                     and isolinux folders default is /live"
    print ""
    print "       bootparams - extra boot parameters like console=..."
    print "                    default is \"$OVIRT_BOOTPARAMS\""
    print ""
    print "       reboot     - reboot after install, default is yes"
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        Usage()

    live = sys.argv[1]
    bootparams = sys.argv[2]
    if len(sys.argv) == 3:
        doreboot="yes"
    else:
        doreboot=sys.argv[3]

    if bootparams is None:
        bootparams=OVIRT_VARS["OVIRT_BOOTPARAMS"]

    if OVIRT_VARS["OVIRT_ROOT_INSTALL"] == "n":
        log("done.")
    elif ovirt_boot_setup() and doreboot == "yes":
        reboot()

