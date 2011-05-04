#!/usr/bin/python
# install.py - Copyright (C) 2010 Red Hat, Inc.
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
import shutil
import sys
OVIRT_VARS = parse_defaults()

def ovirt_boot_setup():
    log("installing the image.")

    if OVIRT_VARS.has_key("OVIRT_ROOT_INSTALL"):
        if OVIRT_VARS["OVIRT_ROOT_INSTALL"] == "n":
            log("done.")
            return

    found_boot=False
    if findfs("Boot"):
        found_boot = True
        grub_dev_label = "Boot"
    if findfs("Root"):
        found_boot = False
        grub_dev_label = "Root"
    if found_boot:
        mount_boot()
        if not os.path.ismount("/boot"):
            log("Boot partition not available")
            sys.exit(1)
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
                os.system("iscsiadm_cmd")
                log("Restarting iscsi service")
                os.system("service iscsi restart &>/dev/null")
            except:
                pass
    else:
        grub_dev_label="RootBackup"

    # check that /boot mounted ok and find partition number for GRUB, $4 is to allow 0 as a partition number for grub
    log("grub_dev_label: " + grub_dev_label)
    try:
        disk = findfs(grub_dev_label)
        if disk:
            disk = disk.strip()
            length = len(disk) - 1
            partN = disk[length:]
            partN = int(partN) - 1
            log("partN: " + str(partN))
        else:
            log("Unable to find %s partition") % grub_dev_label
    except:
        log("Failed to determine new Root partition")
        return False
    disk_basename = disk.rstrip(disk[-2:])
    if os.path.exists(disk_basename):
        disk = disk_basename

    if disk is None and partN < 0:
      log("unable to determine Root partition")
      sys.exit(1)
    if not OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED"):
        mount_liveos()
        if not os.path.ismount("/liveos"):
          log("Root partition not available")
          sys.exit(1)
        os.system("umount /liveos")
        # prepare Root partition update
        candidate=""
        if findfs("RootBackup"):
            candidate = "RootBackup"
        elif findfs("RootUpdate"):
            candidate = "RootUpdate"
        elif findfs("RootNew"):
            candidate = "RootNew"
        if candidate == "":
            rc=1
        elif candidate == "RootNew":
            ret = os.system("umount /liveos")
            if ret == 0:
                rc=0
            else:
                log("Failed to unmount /liveos")
                return False
        else:
            candidate_dev = findfs(candidate)
            e2label_cmd = "e2label \"%s\" RootNew" % candidate_dev
            log(e2label_cmd)
            rc = os.system(e2label_cmd)
            log(rc)
        if rc != 0:
          log("root partition not available.")
          label_debug = os.listdir("/dev/disk/by-label")
          log(label_debug)
          return rc
        mount_cmd = "mount \"%s\" /liveos" % candidate_dev
        os.system(mount_cmd)
        os.system("rm -rf /liveos/LiveOS")
        os.system("mkdir -p /liveos/LiveOS")
        mount_live()
    # install oVirt Node image for local boot
    if os.path.exists("/live/syslinux"):
        syslinux = "syslinux"
    elif os.path.exists("/live/isolinux"):
        syslinux = "isolinux"
    else:
        return False

    if OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED") and OVIRT_VARS["OVIRT_ISCSI_ENABLED"] == "y":
        initrd_dest = "/boot"
        grub_dir = "/boot/grub"
        grub_prefix = "/grub"
    else:
        initrd_dest = "/liveos"
        grub_dir = "/liveos/boot/grub"
        grub_prefix = "/boot/grub"
    if os.path.isdir(grub_dir):
        shutil.rmtree(grub_dir)
    if not os.path.exists(grub_dir):
        os.makedirs(grub_dir)
    if system("cp -p /live/" + syslinux + "/vmlinuz0 " + initrd_dest):
        if not system("cp -p /live/" + syslinux + "/initrd0.img " + initrd_dest):
            log("initrd image copy failed.")
            return False
        if not system("cp -p /live/" + syslinux + "/version /liveos"):
            log("version details copy failed.")
            return False
    else:
        log("kernel image copy failed.")
        return False

    if not OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED"):
        rc = os.system("cp -p /live/LiveOS/squashfs.img /liveos/LiveOS")
        if rc > 0:
          log("squashfs image copy failed.")
          return False
    # reorder tty0 to allow both serial and phys console after installation
    if OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED") and OVIRT_VARS["OVIRT_ISCSI_ENABLED"] == "y":
        bootparams="ro root=LABEL=ovirt-node-root roottypefs=ext3 console=tty0 \
                    netroot=iscsi:$OVIRT_ISCSI_TARGET_IP::$OVIRT_ISCSI_TARGET_PORT::$OVIRT_ISCSI_NODE_NAME ip=eth0:dhcp"
    else:
        bootparams="ro root=live:LABEL=Root roottypefs=auto  "
        bootparams += OVIRT_VARS["OVIRT_BOOTPARAMS"].replace("console=tty0","")
    if " " in disk or os.path.exists("/dev/cciss"):
        # workaround for grub setup failing with spaces in dev.name
        grub_disk_cmd= "multipath -l \"" + disk + "\" | awk '/ active / {print $3}'"
        log(grub_disk_cmd)
        grub_disk = subprocess.Popen(grub_disk_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        disk = grub_disk.stdout.read().strip()
        log("disk:" + disk)
        if "cciss" in disk:
            disk = disk.replace("!","/")
        # flush to sync DM and blockdev, workaround from rhbz#623846#c14
        os.system("echo 3 > /proc/sys/vm/drop_caches")
        os.system("partprobe " + "/dev/"+disk)

    grub_config_file = "%s/grub.conf" % grub_dir
    GRUB_CONFIG_TEMPLATE = """
default=0
timeout=5
hiddenmenu
title %(product)s %(version)s-%(release)s
    root (hd0,%(partN)s)
    kernel /vmlinuz0 %(bootparams)s
    initrd /initrd0.img
    """
    device_map_conf = open(grub_dir + "/device.map", "w")
    disk = disk.rstrip('012')
    if "/dev/" in disk:
        device_map_conf.write("(hd0) " + disk)
    else:
        device_map_conf.write("(hd0) /dev/" + disk)
    device_map_conf.close()
    grub_files = ["stage1", "stage2", "e2fs_stage1_5"]
    for file in grub_files:
        os.system("cp /usr/share/grub/x86_64-redhat/" + file + " " + grub_dir)

    GRUB_SETUP_TEMPLATE = """
    grub --device-map=%(grub_dir)s/device.map <<EOF
root (hd0,%(partN)s)
setup --prefix=%(grub_prefix)s (hd0)
EOF
"""

    grub_dict = {
        "product" : PRODUCT_SHORT,
        "version" : PRODUCT_VERSION,
        "release" : PRODUCT_RELEASE,
        "partN" : partN,
        "bootparams" : bootparams,
        "disk" : disk,
        "grub_dir" : grub_dir,
        "grub_prefix" : grub_prefix
    }
    grub_config_out = GRUB_CONFIG_TEMPLATE % grub_dict
    grub_setup_out = GRUB_SETUP_TEMPLATE % grub_dict
    log(grub_setup_out)
    grub_conf = open(grub_config_file, "w")
    grub_conf.write(grub_config_out)
    grub_conf.close()
    grub_setup = subprocess.Popen(grub_setup_out, shell=True, stdout=PIPE, stderr=STDOUT)
    grub_results = grub_setup.stdout.read()
    log(grub_results)
    if not OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED"):
        os.system("sync")
        os.system("sleep 2")
        os.system("umount /liveos")
        # mark new Root ready to go, reboot() in ovirt-function switches it to active
        e2label_cmd = "e2label \"%s\" RootUpdate" % candidate_dev
        ret = os.system(e2label_cmd)
        if ret != 0:
            log("Unable to relabel " + candidate_dev + " to RootUpdate ")
            return False
    if OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED") and OVIRT_VARS["OVIRT_ISCSI_ENABLED"] == "y":
        # copy default for when Root/HostVG is inaccessible(iscsi upgrade)
        shutil.copy(OVIRT_DEFAULTS, "/boot")
    os.system("e2label /dev/disk/by-label/RootNew RootUpdate")
    disable_firstboot()
    if OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED"):
        if OVIRT_VARS["OVIRT_ISCSI_ENABLED"] != "y":
            ovirt_store_firstboot_config()
    if finish_install():
        log("done.")
        return True

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
    try:
        doreboot=sys.argv[3]
        doreboot="no"
    except:
        doreboot = "yes"

    if bootparams is None:
        bootparams=OVIRT_VARS["OVIRT_BOOTPARAMS"]
    if doreboot == "":
        doreboot="yes"

    if OVIRT_VARS["OVIRT_ROOT_INSTALL"] == "n":
        log("done.")
    else:
        rc = ovirt_boot_setup()   #(live, bootparams)
    if rc == 0 and doreboot == "yes":
        disable_firstboot()
        if OVIRT_VARS["OVIRT_ISCSI_ENABLED"] != "y":
            ovirt_store_firstboot_config()
        reboot()

