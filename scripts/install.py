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

from ovirtnode.ovirtfunctions import *
from ovirtnode.iscsi import *
import shutil
import traceback
import os
import stat
import subprocess
import re
OVIRT_VARS = parse_defaults()

class Install:


    def __init__(self):
        self.disk = None
        self.partN = -1

    def kernel_image_copy(self):
        if not system("cp -p /live/" + self.syslinux + "/vmlinuz0 " + self.initrd_dest):
            logger.error("kernel image copy failed.")
            return False
        if not system("cp -p /live/" + self.syslinux + "/initrd0.img " + self.initrd_dest):
            logger.error("initrd image copy failed.")
            return False
        if not system("cp -p /live/" + self.syslinux + "/version /liveos"):
            logger.error("version details copy failed.")
            return False
        if not OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED"):
            if not system("cp -p /live/LiveOS/squashfs.img /liveos/LiveOS"):
                logger.error("squashfs image copy failed.")
                return False
        return True

    def generate_paths(self):
        mount_live()
        # install oVirt Node image for local boot
        if os.path.exists("/live/syslinux"):
            self.syslinux = "syslinux"
        elif os.path.exists("/live/isolinux"):
            self.syslinux = "isolinux"
        else:
            logger.info("Failed to determine grub pathnames")
            return False

        if OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED") and OVIRT_VARS["OVIRT_ISCSI_ENABLED"] == "y":
            self.initrd_dest = "/boot"
            self.grub_dir = "/boot/grub"
            self.grub_prefix = "/grub"
        else:
            self.initrd_dest = "/liveos"
            self.grub_dir = "/liveos/grub"
            self.grub_prefix = "/grub"

        if os.path.exists("/sbin/grub2-install"):
            self.grub_prefix = self.grub_prefix + "2"
            self.grub_dir = self.grub_dir + "2"
            self.grub_config_file = "%s/grub.cfg" % self.grub_dir
        else:
            self.grub_config_file = "%s/grub.conf" % self.grub_dir

    def grub_install(self):
        device_map = "(hd0) %s" % self.disk
        logger.debug(device_map)
        device_map_conf = open(self.grub_dir + "/device.map", "w")
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

        grub_conf = open(self.grub_config_file, "w")
        grub_conf.write(GRUB_CONFIG_TEMPLATE % self.grub_dict)
        if self.oldtitle is not None:
            partB=1
            if partN == 1:
                partB=2
            self.grub_dict['oldtitle']=self.oldtitle
            self.grub_dict['partB']=partB
            grub_conf.write(GRUB_BACKUP_TEMPLATE % self.grub_dict)
        grub_conf.close()
        for f in ["stage1", "stage2", "e2fs_stage1_5"]:
            system("cp /usr/share/grub/x86_64-redhat/%s %s" % (f, self.grub_dir))
        grub_setup_out = GRUB_SETUP_TEMPLATE % self.grub_dict
        logger.debug(grub_setup_out)
        grub_setup = subprocess.Popen(grub_setup_out, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        grub_results = grub_setup.stdout.read()
        logger.debug(grub_results)
        if grub_setup.wait() != 0 or "Error" in grub_results:
            logger.error("GRUB setup failed")
            return False
        return True

    def grub2_install(self):
        GRUB2_CONFIG_TEMPLATE = """
#default saved
set timeout=5
#hiddenmenu
menuentry "%(product)s %(version)s-%(release)s" {
set root=(hd0,%(partN)d)
linux /vmlinuz0 %(root_param)s %(bootparams)s
initrd /initrd0.img
}"""

        GRUB2_BACKUP_TEMPLATE = """
menuentry "BACKUP %(oldtitle)s" {
set root (hd0,%(partB)d)
linux /vmlinuz0 root=live:LABEL=RootBackup %(bootparams)s
initrd /initrd0.img
    """

        grub_setup_cmd = "/sbin/grub2-install " + self.disk + " --boot-directory=" + self.initrd_dest + " --force"
        logger.debug(grub_setup_cmd)
        grub_setup = subprocess.Popen(grub_setup_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        grub_results = grub_setup.stdout.read()
        logger.debug(grub_results)
        if grub_setup.wait() != 0 or "Error" in grub_results:
            logger.error("GRUB setup failed")
            return False
        else:
            logger.debug("Generating Grub2 Templates")
            grub_conf = open(self.grub_config_file, "w")
            grub_conf.write(GRUB2_CONFIG_TEMPLATE % self.grub_dict)
            if self.oldtitle is not None:
                partB=0
                if partN == 0:
                    partB=1
                self.grub_dict['oldtitle']=self.oldtitle
                self.grub_dict['partB']=partB
                grub_conf.write(GRUB2_BACKUP_TEMPLATE % self.grub_dict)
            grub_conf.close()
            logger.info("Grub2 Install Completed")
            return True

    def ovirt_boot_setup(self):
        self.generate_paths()

        logger.info("Installing the image.")

        if OVIRT_VARS.has_key("OVIRT_ROOT_INSTALL"):
            if OVIRT_VARS["OVIRT_ROOT_INSTALL"] == "n":
                logger.info("Root Installation Not Required, Finished.")
                return True

        self.oldtitle=None
        if os.path.ismount("/liveos"):
            if os.path.exists("/liveos/vmlinuz0") and os.path.exists("/liveos/initrd0.img"):
                f=open(self.grub_config_file)
                oldgrub=f.read()
                f.close()
                m=re.search("^title (.*)$", oldgrub, re.MULTILINE)
                if m is not None:
                    self.oldtitle=m.group(1)

            system("umount /liveos")

        if findfs("Boot"):
            candidate = "Boot"
            mount_boot()
            if not os.path.ismount("/boot"):
                logger.error("Boot partition not available, Install Failed")
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
                    logger.info("Restarting iscsi service")
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
            logger.error("Unable to find Root partition")
            label_debug = ''
            for label in os.listdir("/dev/disk/by-label"):
                label_debug += "%s\n" % label
            label_debug += subprocess.Popen("blkid", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.read()
            logger.debug(label_debug)
            return False
        logger.debug("candidate: " + candidate)

        try:
            candidate_dev = self.disk = findfs(candidate)
            logger.info(candidate_dev)
            logger.info(self.disk)
            # grub2 starts at part 1
            self.partN = int(self.disk[-1:])
            if not os.path.exists("/sbin/grub2-install"):
                self.partN = self.partN - 1
            logger.debug("partN: %d" % self.partN)
        except:
            logger.debug(traceback.format_exc())
            return False

        if self.disk is None or self.partN < 0:
            logger.error("Failed to determine Root partition number")
            return False
        if not OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED"):
            # prepare Root partition update
            if candidate != "RootNew":
                e2label_cmd = "e2label \"%s\" RootNew" % candidate_dev
                logger.debug(e2label_cmd)
                if not system(e2label_cmd):
                    logger.error("Failed to label new Root partition")
                    return False
            mount_cmd = "mount \"%s\" /liveos" % candidate_dev
            system(mount_cmd)
            system("rm -rf /liveos/LiveOS")
            system("mkdir -p /liveos/LiveOS")
            mount_live()

        if os.path.isdir(self.grub_dir):
            shutil.rmtree(self.grub_dir)
        if not os.path.exists(self.grub_dir):
            os.makedirs(self.grub_dir)
            os.makedirs(self.grub_dir + "/efi")
            system("mount LABEL=EFI "+self.grub_dir+"/efi")
            system("cp -ra /boot/efi/* " + self.grub_dir + "/efi")
            system("umount /liveos/grub/efi")

        self.kernel_image_copy()

        # reorder tty0 to allow both serial and phys console after installation
        if OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED") and OVIRT_VARS["OVIRT_ISCSI_ENABLED"] == "y":
            self.root_param="root=LABEL=ovirt-node-root"
            self.bootparams="ro rootfstype=ext2 rootflags=ro console=tty0 \
                        netroot=iscsi:$OVIRT_ISCSI_TARGET_IP::$OVIRT_ISCSI_TARGET_PORT::$OVIRT_ISCSI_NODE_NAME ip=eth0:dhcp"
        else:
            self.root_param="root=live:LABEL=Root"
            self.bootparams="ro rootfstype=auto rootflags=ro "
        self.bootparams += OVIRT_VARS["OVIRT_BOOTPARAMS"].replace("console=tty0","")

        if " " in self.disk or os.path.exists("/dev/cciss"):
            # workaround for grub setup failing with spaces in dev.name:
            # use first active sd* device
            self.disk = re.sub("p[1,2,3]$", "", self.disk)
            grub_disk_cmd= "multipath -l \"" + os.path.basename(self.disk) + "\" | awk '/ active / {print $3}' | head -n1"
            logger.debug(grub_disk_cmd)
            grub_disk = subprocess.Popen(grub_disk_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.disk = grub_disk.stdout.read().strip()
            if "cciss" in self.disk:
                self.disk = self.disk.replace("!","/")
            # flush to sync DM and blockdev, workaround from rhbz#623846#c14
            sysfs=open("/proc/sys/vm/drop_caches","w")
            sysfs.write("3")
            sysfs.close()
            partprobe_cmd="partprobe \"/dev/%s\"" % self.disk
            logger.debug(partprobe_cmd)
            system(partprobe_cmd)

        if not self.disk.startswith("/dev/"):
            self.disk = "/dev/" + disk
        try:
            if stat.S_ISBLK(os.stat(self.disk).st_mode):
                try:
                    if stat.S_ISBLK(os.stat(self.disk[:-1]).st_mode):
                        # e.g. /dev/sda2
                        self.disk = self.disk[:-1]
                except OSError:
                    pass
                try:
                    if stat.S_ISBLK(os.stat(self.disk[:-2]).st_mode):
                        # e.g. /dev/mapper/WWIDp2
                        self.disk = self.disk[:-2]
                except OSError:
                    pass
        except OSError:
            logger.error("Unable to determine disk for grub installation " + traceback.format_exc())
            return False

        self.grub_dict = {
        "product" : PRODUCT_SHORT,
        "version" : PRODUCT_VERSION,
        "release" : PRODUCT_RELEASE,
        "partN" : self.partN,
        "root_param" : self.root_param,
        "bootparams" : self.bootparams,
        "disk" : self.disk,
        "grub_dir" : self.grub_dir,
        "grub_prefix" : self.grub_prefix
    }

        if os.path.exists("/sbin/grub2-install"):
            if not self.grub2_install():
                logger.error("Grub2 Installation Failed ")
                return False
            else:
                logger.info("Grub 2 Installation Completed")
        else:
            if not self.grub_install():
                logger.error("Grub Installation Failed ")
                return False
            else:
                logger.info("Grub 2 Installation Completed")

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
                logger.error("Unable to relabel " + candidate_dev + " to RootUpdate ")
                return False
        disable_firstboot()
        if finish_install():
            iscsi_auto()
            logger.info("Installation of %s Completed" % PRODUCT_SHORT)
            return True
        else:
            return False
