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

import ovirtnode.ovirtfunctions as _functions
import ovirtnode.iscsi as _iscsi
import shutil
import traceback
import os
import stat
import subprocess
import re
import time
import logging
OVIRT_VARS = _functions.parse_defaults()
from ovirtnode.storage import Storage

logger = logging.getLogger(_functions.PRODUCT_SHORT)


class Install:
    def __init__(self):
        logger.propagate = False
        self.disk = None
        self.partN = -1
        self.s = Storage()
        self.efi_hd = ""

    def kernel_image_copy(self):
        if (not _functions.system("cp -p /live/" + self.syslinux + \
                                 "/vmlinuz0 " + self.initrd_dest)):
            logger.error("kernel image copy failed.")
            return False
        if (not _functions.system("cp -p /live/" + self.syslinux + \
                                 "/initrd0.img " + self.initrd_dest)):
            logger.error("initrd image copy failed.")
            return False
        if (not _functions.system("cp -p /live/" + self.syslinux + \
                                 "/version /liveos")):
            logger.error("version details copy failed.")
            return False
        if (not _functions.system("cp -p /live/LiveOS/squashfs.img " + \
                                  "/liveos/LiveOS")):
            logger.error("squashfs image copy failed.")
            return False
        return True

    def generate_paths(self):
        _functions.mount_live()
        # install oVirt Node image for local boot
        if os.path.exists("/live/syslinux"):
            self.syslinux = "syslinux"
        elif os.path.exists("/live/isolinux"):
            self.syslinux = "isolinux"
        else:
            logger.info("Failed to determine grub pathnames")
            return False

        if _functions.is_iscsi_install():
            self.initrd_dest = "/boot"
            self.grub_dir = "/boot/grub"
            self.grub_prefix = "/grub"
        else:
            self.initrd_dest = "/liveos"
            self.grub_dir = "/liveos/grub"
            self.grub_prefix = "/grub"

        if _functions.grub2_available():
            self.grub_prefix = self.grub_prefix + "2"
            self.grub_dir = self.grub_dir + "2"
            self.grub_config_file = "%s/grub.cfg" % self.grub_dir
        else:
            self.grub_config_file = "%s/grub.conf" % self.grub_dir

        if os.path.exists("/boot/efi/EFI/fedora"):
            self.efi_dir_name = "fedora"
        else:
            self.efi_dir_name = "redhat"
        if _functions.is_efi_boot():
            self.grub_config_file = "/liveos/efi/EFI/%s/grub.cfg" \
                                     % self.efi_dir_name

    def grub_install(self):
        if _functions.is_iscsi_install():
            self.disk = re.sub("p[1,2,3]$", "", findfs(self.boot_candidate))
        device_map = "(hd0) %s" % self.disk
        logger.debug(device_map)
        device_map_conf = open(self.grub_dir + "/device.map", "w")
        device_map_conf.write(device_map)
        device_map_conf.close()

        GRUB_CONFIG_TEMPLATE = """
default saved
timeout 5
hiddenmenu
%(splashscreen)s
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
    savedefault
    """
        GRUB_SETUP_TEMPLATE = """
    grub --device-map=%(grub_dir)s/device.map <<EOF
root (hd0,%(partN)d)
setup --prefix=%(grub_prefix)s (hd0)
EOF
"""

        if _functions.is_efi_boot():
            """ The EFI product path.
                eg: HD(1,800,64000,faacb4ef-e361-455e-bd97-ca33632550c3)
            """
            efi_cmd = "efibootmgr -v"
            efi = _functions.subprocess_closefds(efi_cmd, shell=True,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.STDOUT)
            efi_out = efi.stdout.read().strip()
            matches = re.search(_functions.PRODUCT_SHORT + r'\s+(HD\(.+?\))', \
                                                                       efi_out)
            if matches and matches.groups():
                GRUB_EFIONLY_CONFIG = """%(efi_hd)s"""
                GRUB_CONFIG_TEMPLATE = GRUB_EFIONLY_CONFIG + GRUB_CONFIG_TEMPLATE
                self.grub_dict['efi_hd'] = "device (hd0) " + matches.group(1)
        if os.path.exists("/live/EFI/BOOT/splash.xpm.gz"):
            splashscreen = "splashimage=(hd0,%s)/grub/splash.xpm.gz" \
                % self.partN
        else:
            splashscreen = ""
        self.grub_dict["splashscreen"] = splashscreen
        GRUB_CONFIG_TEMPLATE % self.grub_dict
        grub_conf = open(self.grub_config_file, "w")
        grub_conf.write(GRUB_CONFIG_TEMPLATE % self.grub_dict)
        if self.oldtitle is not None:
            partB = 1
            if self.partN == 1:
                partB = 2
            if _functions.is_iscsi_install():
                partB = 0
                if self.partN == 0:
                    partB = 1
            self.grub_dict['oldtitle'] = self.oldtitle
            self.grub_dict['partB'] = partB
            grub_conf.write(GRUB_BACKUP_TEMPLATE % self.grub_dict)
        grub_conf.close()
        # splashscreen
        _functions.system("cp /live/EFI/BOOT/splash.xpm.gz /liveos/grub")
        # usb devices requires default BOOTX64 entries
        if _functions.is_efi_boot():
            _functions.system("mkdir -p /liveos/efi/EFI/BOOT")
            _functions.system("cp /boot/efi/EFI/redhat/grub.efi /liveos/efi/EFI/BOOT/BOOTX64.efi")
            _functions.system("cp /liveos/efi/EFI/redhat/grub.conf /liveos/efi/EFI/BOOT/BOOTX64.conf")
            _functions.system("umount /liveos/efi")
        if not _functions.is_efi_boot():
            for f in ["stage1", "stage2", "e2fs_stage1_5"]:
                _functions.system("cp /usr/share/grub/x86_64-redhat/%s %s" % \
                                                            (f, self.grub_dir))
            grub_setup_out = GRUB_SETUP_TEMPLATE % self.grub_dict
            logger.debug(grub_setup_out)
            grub_setup = _functions.subprocess_closefds(grub_setup_out,
                                             shell=True,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT)
            grub_results = grub_setup.stdout.read()
            logger.debug(grub_results)
            if grub_setup.wait() != 0 or "Error" in grub_results:
                logger.error("GRUB setup failed")
                return False
        return True

    def grub2_install(self):
        GRUB2_EFI_CONFIG_TEMPLATE = """
insmod efi_gop
insmod efi_uga
"""

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
}    """
        if _functions.is_iscsi_install():
            disk = re.sub("p[1,2,3]$", "", \
                                    _functions.findfs("BootNew"))
            self.grub_dict["partN"] = int(_functions.findfs("BootNew")[-1:])
        else:
            disk = self.disk
        if _functions.is_efi_boot():
            boot_dir = self.initrd_dest + "/efi"
        else:
            boot_dir = self.initrd_dest
        grub_setup_cmd = ("/sbin/grub2-install " + disk +
                          " --boot-directory=" + boot_dir +
                          " --root-directory=" + boot_dir +
                          " --efi-directory=" + boot_dir +
                          " --bootloader-id=" + self.efi_dir_name +
                          " --force")
        _functions.system("echo '%s' >> /liveos/efi/cmd" % grub_setup_cmd)
        logger.info(grub_setup_cmd)
        grub_setup = _functions.subprocess_closefds(grub_setup_cmd, \
                                         shell=True,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
        grub_results = grub_setup.stdout.read()
        logger.info(grub_results)
        if grub_setup.wait() != 0 or "Error" in grub_results:
            logger.error("grub2-install Failed")
            return False
        else:
            logger.debug("Generating Grub2 Templates")
            if _functions.is_efi_boot():
                if not os.path.exists("/liveos/efi/EFI/%s" % self.efi_dir_name):
                    os.makedirs("/liveos/efi/EFI/%s" % self.efi_dir_name)
            grub_conf = open(self.grub_config_file, "w")
            grub_conf.write(GRUB2_CONFIG_TEMPLATE % self.grub_dict)
        if self.oldtitle is not None:
            partB = 0
            if self.partN == 0:
                partB = 1
            self.grub_dict['oldtitle'] = self.oldtitle
            self.grub_dict['partB'] = partB
            grub_conf.write(GRUB2_BACKUP_TEMPLATE % self.grub_dict)
        grub_conf.close()
        if os.path.exists("/liveos/efi/EFI"):
            efi_grub_conf = open("/liveos/efi/EFI/%s/grub.cfg" \
                    % self.efi_dir_name, "w")
            # inject efi console output modules
            efi_grub_conf.write(GRUB2_EFI_CONFIG_TEMPLATE)
            efi_grub_conf.write(GRUB2_CONFIG_TEMPLATE % self.grub_dict)
            if self.oldtitle is not None:
                partB = 0
                if self.partN == 0:
                    partB = 1
                self.grub_dict['oldtitle'] = self.oldtitle
                self.grub_dict['partB'] = partB
                efi_grub_conf.write(GRUB2_BACKUP_TEMPLATE % self.grub_dict)
                efi_grub_conf.close()
            _functions.system("umount /liveos")
            _functions.remove_efi_entry(self.efi_dir_name)
            logger.info("Grub2 Install Completed")
            return True
        return True

    def ovirt_boot_setup(self, reboot="N"):
        self.generate_paths()
        logger.info("Installing the image.")

        if "OVIRT_ROOT_INSTALL" in OVIRT_VARS:
            if OVIRT_VARS["OVIRT_ROOT_INSTALL"] == "n":
                logger.info("Root Installation Not Required, Finished.")
                return True
        self.oldtitle=None
        grub_config_file = None
        _functions.mount_liveos()
        if os.path.ismount("/liveos"):
            if os.path.exists("/liveos/vmlinuz0") and os.path.exists("/liveos/initrd0.img"):
                grub_config_file = self.grub_config_file
        elif not _functions.is_firstboot():
            # find existing iscsi install
            if _functions.findfs("Boot"):
                grub_config_file = "/boot/grub/grub.conf"
            elif os.path.ismount("/dev/.initramfs/live"):
                grub_config_file = "/dev/.initramfs/live/grub/grub.conf"
            elif os.path.ismount("/run/initramfs/live"):
                grub_config_file = "/run/initramfs/live/grub/grub.conf"
            if is_upgrade() and not _functions.is_iscsi_install():
                mount_liveos()
                grub_config_file = "/liveos/grub/grub.conf"
        if _functions.is_efi_boot():
            logger.debug(str(os.listdir("/liveos")))
            _functions.system("umount /liveos")
            _functions.mount_efi(target="/liveos")
            grub_config_file = "/liveos/EFI/%s/grub.cfg" % self.efi_dir_name
        if _functions.is_iscsi_install():
            grub_config_file = "/boot/grub/grub.conf"
        grub_config_file_exists = grub_config_file is not None and os.path.exists(grub_config_file)
        logger.debug("Grub config file is: %s" % grub_config_file)
        logger.debug("Grub config file exists: %s" % grub_config_file_exists)
        if not grub_config_file is None and os.path.exists(grub_config_file):
            f=open(grub_config_file)
            oldgrub=f.read()
            f.close()
            if _functions.grub2_available():
                m=re.search("^menuentry (.*)$", oldgrub, re.MULTILINE)
            else:
                m=re.search("^title (.*)$", oldgrub, re.MULTILINE)
            if m is not None:
                self.oldtitle=m.group(1)
                # strip off extra title characters
                if _functions.grub2_available():
                    self.oldtitle = self.oldtitle.replace('"','').strip(" {")
        _functions.system("umount /liveos/efi")
        _functions.system("umount /liveos")
        if _functions.is_iscsi_install():
            self.boot_candidate = None
            boot_candidate_names = ["BootBackup", "BootUpdate", "BootNew"]
            for trial in range(1, 3):
                time.sleep(1)
                _functions.system("partprobe")
                for candidate_name in boot_candidate_names:
                    if _functions.findfs(candidate_name):
                        self.boot_candidate = candidate_name
                        break
                logger.debug("Trial %s to find candidate (%s)" % \
                             (trial, self.boot_candidate))
                if self.boot_candidate:
                    logger.debug("Found candidate: %s" % self.boot_candidate)
                    break

            if not self.boot_candidate:
                logger.error("Unable to find boot partition")
                label_debug = ''
                for label in os.listdir("/dev/disk/by-label"):
                    label_debug += "%s\n" % label
                label_debug += _functions.subprocess_closefds("blkid", \
                                          shell=True, stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT).stdout.read()
                logger.debug(label_debug)
                return False
            else:
                boot_candidate_dev = _functions.findfs(self.boot_candidate)
            # prepare Root partition update
            if self.boot_candidate != "BootNew":
                e2label_cmd = "e2label \"%s\" BootNew" % boot_candidate_dev
                logger.debug(e2label_cmd)
                if not _functions.system(e2label_cmd):
                    logger.error("Failed to label new Boot partition")
                    return False
            _functions.system("mount LABEL=%s /boot &>/dev/null" % self.boot_candidate)

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
                    iscsiadm_cmd = (("iscsiadm -p %s:%s -m discovery -t " +
                                     "sendtargets") % (
                                        OVIRT_VARS["OVIRT_ISCSI_TARGET_IP"],
                                        OVIRT_VARS["OVIRT_ISCSI_TARGET_PORT"]))
                    _functions.system(iscsiadm_cmd)
                    logger.info("Restarting iscsi service")
                    _functions.system("service iscsi restart")
                except:
                    pass

        candidate = None
        candidate_names = ["RootBackup", "RootUpdate", "RootNew"]
        for trial in range(1, 3):
            time.sleep(1)
            _functions.system("partprobe")
            for candidate_name in candidate_names:
                if _functions.findfs(candidate_name):
                    candidate = candidate_name
                    break
            logger.debug("Trial %s to find candidate (%s)" % (trial,
                                                              candidate))
            if candidate:
                logger.debug("Found candidate: %s" % candidate)
                break

        if not candidate:
            logger.error("Unable to find root partition")
            label_debug = ''
            for label in os.listdir("/dev/disk/by-label"):
                label_debug += "%s\n" % label
            label_debug += _functions.subprocess_closefds("blkid", shell=True,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT).stdout.read()
            logger.debug(label_debug)
            return False

        try:
            candidate_dev = self.disk = _functions.findfs(candidate)
            logger.info(candidate_dev)
            logger.info(self.disk)
            # grub2 starts at part 1
            self.partN = int(self.disk[-1:])
            if not _functions.grub2_available():
                self.partN = self.partN - 1
        except:
            logger.debug(traceback.format_exc())
            return False

        if self.disk is None or self.partN < 0:
            logger.error("Failed to determine Root partition number")
            return False
        # prepare Root partition update
        if candidate != "RootNew":
            e2label_cmd = "e2label \"%s\" RootNew" % candidate_dev
            logger.debug(e2label_cmd)
            if not _functions.system(e2label_cmd):
                logger.error("Failed to label new Root partition")
                return False
        mount_cmd = "mount \"%s\" /liveos" % candidate_dev
        _functions.system(mount_cmd)
        _functions.system("rm -rf /liveos/LiveOS")
        _functions.system("mkdir -p /liveos/LiveOS")
        _functions.mount_live()

        if os.path.isdir(self.grub_dir):
            shutil.rmtree(self.grub_dir)
        if not os.path.exists(self.grub_dir):
            os.makedirs(self.grub_dir)

            if _functions.is_efi_boot():
                logger.info("efi detected, installing efi configuration")
                _functions.system("mkdir /liveos/efi")
                _functions.mount_efi()
                efi_disk = re.sub("p[1,2,3]$", "", self.disk)
                # generate grub legacy config for efi partition
                #remove existing efi entries
                _functions.remove_efi_entry(self.efi_dir_name)
                efi_mgr_cmd = ("efibootmgr -c -l '\\EFI\\%s\\grubx64.efi' " +
                              "-L '%s' -d %s -v") % (self.efi_dir_name,  \
                                               _functions.PRODUCT_SHORT, \
                                               efi_disk)
                logger.info(efi_mgr_cmd)
                _functions.system(efi_mgr_cmd)
        self.kernel_image_copy()

        # reorder tty0 to allow both serial and phys console after installation
        if _functions.is_iscsi_install():
            self.root_param = "root=live:LABEL=Root"
            self.bootparams = "netroot=iscsi:%s::%s::%s ip=br%s:dhcp bridge=br%s:%s " % (
                OVIRT_VARS["OVIRT_ISCSI_TARGET_HOST"],
                OVIRT_VARS["OVIRT_ISCSI_TARGET_PORT"],
                OVIRT_VARS["OVIRT_ISCSI_TARGET_NAME"],
                OVIRT_VARS["OVIRT_BOOTIF"],
                OVIRT_VARS["OVIRT_BOOTIF"],
                OVIRT_VARS["OVIRT_BOOTIF"])
        else:
            self.root_param = "root=live:LABEL=Root"
            self.bootparams = "ro rootfstype=auto rootflags=ro "
        self.bootparams += OVIRT_VARS["OVIRT_BOOTPARAMS"].replace(
                                                            "console=tty0", "")
        if " " in self.disk or os.path.exists("/dev/cciss"):
            # workaround for grub setup failing with spaces in dev.name:
            # use first active sd* device
            self.disk = re.sub("p[1,2,3]$", "", self.disk)
            grub_disk_cmd = "multipath -l \"" + self.disk + \
                            "\" | awk '/ active / {print $3}' | head -n1"
            logger.debug(grub_disk_cmd)
            grub_disk = _functions.subprocess_closefds(grub_disk_cmd,
                                            shell=True,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
            self.disk = grub_disk.stdout.read().strip()
            if "cciss" in self.disk:
                self.disk = self.disk.replace("!", "/")
            # flush to sync DM and blockdev, workaround from rhbz#623846#c14
            sysfs = open("/proc/sys/vm/drop_caches", "w")
            sysfs.write("3")
            sysfs.close()
            partprobe_cmd = "partprobe \"/dev/%s\"" % self.disk
            logger.debug(partprobe_cmd)
            _functions.system(partprobe_cmd)

        if not self.disk.startswith("/dev/"):
            self.disk = "/dev/" + self.disk
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
            logger.error("Unable to determine disk for grub installation " +
                         traceback.format_exc())
            return False

        self.grub_dict = {
        "product": _functions.PRODUCT_SHORT,
        "version": _functions.PRODUCT_VERSION,
        "release": _functions.PRODUCT_RELEASE,
        "partN": self.partN,
        "root_param": self.root_param,
        "bootparams": self.bootparams,
        "disk": self.disk,
        "grub_dir": self.grub_dir,
        "grub_prefix": self.grub_prefix,
        "efi_hd": self.efi_hd
    }
        if not _functions.is_firstboot():
            if os.path.ismount("/live"):
                with open("/live/%s/version" % self.syslinux) as version:
                    for line in version.readlines():
                        if "VERSION" in line:
                            key, value = line.split("=")
                            self.grub_dict["version"] = value.strip()
                        if "RELEASE" in line:
                            key, value = line.split("=")
                            self.grub_dict["release"] = value.strip()

        if _functions.grub2_available():
            if not self.grub2_install():
                logger.error("Grub2 Installation Failed ")
                return False
            else:
                 logger.info("Grub2 EFI Installation Completed ")
        else:
            if not self.grub_install():
                logger.error("Grub Installation Failed ")
                return False
            else:
                logger.info("Grub Installation Completed")

        if _functions.is_iscsi_install():
            # copy default for when Root/HostVG is inaccessible(iscsi upgrade)
            shutil.copy(_functions.OVIRT_DEFAULTS, "/boot")
            # mark new Root ready to go, reboot() in ovirt-function switches it
            # to active
            e2label_cmd = "e2label \"%s\" BootUpdate" % boot_candidate_dev

            if not _functions.system(e2label_cmd):
                logger.error("Unable to relabel " + boot_candidate_dev +
                             " to RootUpdate ")
                return False
        else:
            _functions.system("umount /liveos/efi")
        _functions.system("umount /liveos")
        # mark new Root ready to go, reboot() in ovirt-function switches it
        # to active
        e2label_cmd = "e2label \"%s\" RootUpdate" % candidate_dev
        if not _functions.system(e2label_cmd):
            logger.error("Unable to relabel " + candidate_dev +
                         " to RootUpdate ")
            return False
        _functions.disable_firstboot()
        if _functions.finish_install():
            if _functions.is_firstboot():
                _iscsi.iscsi_auto()
            logger.info("Installation of %s Completed" % \
                                                      _functions.PRODUCT_SHORT)
            if reboot is not None and reboot == "Y":
                f = open('/var/spool/cron/root', 'w')
                f.write('* * * * * sleep 10 && /sbin/reboot\n')
                f.close()
                #ensure crond is started
                _functions.subprocess_closefds("crond", shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            return True
        else:
            return False
