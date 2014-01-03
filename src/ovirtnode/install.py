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
import ovirt.node.utils.system as _system
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
        self.live_path = None

    def kernel_image_copy(self):
        if (not _functions.system("cp -p %s/vmlinuz0 %s" % \
                                 (self.live_path, self.initrd_dest))):
            logger.error("kernel image copy failed.")
            return False
        if (not _functions.system("cp -p %s/initrd0.img %s" % \
                                 (self.live_path, self.initrd_dest))):
            logger.error("initrd image copy failed.")
            return False
        if (not _functions.system("cp -p %s/version /liveos" \
                                  % self.live_path)):
            logger.error("version details copy failed.")
            return False
        if (not _functions.system("cp %s/LiveOS/squashfs.img /liveos/LiveOS" \
                                  % os.path.split(self.live_path)[0])):
            logger.error("squashfs image copy failed.")
            return False
        return True

    def generate_paths(self):
        _functions.mount_live()
        # install oVirt Node image for local boot
        syslinux_paths = ["/live/syslinux", "/dev/.initramfs/live/syslinux"]

        if os.path.exists("/live/isolinux"):
            self.live_path = "/live/isolinux"

        for d in syslinux_paths:
            if os.path.exists(d):
                self.live_path = d
                break
        if not self.live_path:
            logger.info("Failed to determine grub pathnames")
            return False

        if _functions.is_iscsi_install() or _functions.findfs("Boot"):
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
            if self.efi_dir_name == "fedora":
                self.grub_config_file = "/liveos/efi/EFI/fedora/grub.cfg"
            else:
                self.grub_config_file = "/liveos/efi/EFI/redhat/grub.conf"

    def grub_install(self):
        if _functions.is_iscsi_install() or _functions.findfs("BootNew"):
            self.disk = _functions.findfs("BootNew")
            self.grub_dict["partN"] = int(self.disk[-1:]) - 1
            if not "/dev/mapper/" in self.disk:
                self.disk = self.disk[:-1]
            else:
                self.disk = re.sub("p[1,2,3]$", "", self.disk)
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
            efi_out, efi_err = efi.communicate()
            efi_out = efi_out.strip()
            matches = re.search(_functions.PRODUCT_SHORT + r'\s+(HD\(.+?\))', \
                                                                       efi_out)
            if matches and matches.groups():
                GRUB_EFIONLY_CONFIG = """%(efi_hd)s"""
                GRUB_CONFIG_TEMPLATE = GRUB_EFIONLY_CONFIG + \
                                       GRUB_CONFIG_TEMPLATE
                self.grub_dict['efi_hd'] = "device (hd0) " + matches.group(1)
        if os.path.exists("/live/EFI/BOOT/splash.xpm.gz"):
            if _functions.is_iscsi_install() or _functions.findfs("BootNew"):
                splashscreen = "splashimage=(hd0,%s)/grub/splash.xpm.gz" \
                    % self.grub_dict["partN"]
            else:
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
            if _functions.is_iscsi_install() or _functions.findfs("Boot"):
                partB = partB + 1
            self.grub_dict['oldtitle'] = self.oldtitle
            self.grub_dict['partB'] = partB
            grub_conf.write(GRUB_BACKUP_TEMPLATE % self.grub_dict)
        grub_conf.close()
        # splashscreen
        if _functions.is_iscsi_install() or _functions.findfs("BootNew"):
            _functions.system("cp /live/EFI/BOOT/splash.xpm.gz /boot/grub")
        else:
            _functions.system("cp /live/EFI/BOOT/splash.xpm.gz /liveos/grub")
        # usb devices requires default BOOTX64 entries
        if _functions.is_efi_boot():
            _functions.system("mkdir -p /liveos/efi/EFI/BOOT")
            if _functions.is_iscsi_install() or _functions.findfs("BootNew"):
                _functions.system("cp /tmp/grub.efi \
                                   /liveos/efi/EFI/BOOT/BOOTX64.efi")
            _functions.system("cp /boot/efi/EFI/redhat/grub.efi \
                              /liveos/efi/EFI/BOOT/BOOTX64.efi")
            _functions.system("cp %s /liveos/efi/EFI/BOOT/BOOTX64.conf" \
                              % self.grub_config_file)
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
            grub_results, grub_err = grub_setup.communicate()
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
search --no-floppy --label Root --set root
linux /vmlinuz0 %(root_param)s %(bootparams)s
initrd /initrd0.img
}"""

        GRUB2_BACKUP_TEMPLATE = """
menuentry "BACKUP %(oldtitle)s" {
set root (hd0,%(partB)d)
search --no-floppy --label RootBackup --set root
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
        grub_results, grub_err = grub_setup.communicate()
        logger.info(grub_results)
        if grub_setup.wait() != 0 or "Error" in grub_results:
            logger.error("grub2-install Failed")
            return False
        else:
            logger.debug("Generating Grub2 Templates")
            if _functions.is_efi_boot():
                if not os.path.exists("/liveos/efi/EFI/%s" \
                                      % self.efi_dir_name):
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
        # copy grub.efi to safe location
        if _functions.is_efi_boot():
            shutil.copy("/boot/efi/EFI/%s/grub.efi" % self.efi_dir_name,
                        "/tmp")
        if "OVIRT_ROOT_INSTALL" in OVIRT_VARS:
            if OVIRT_VARS["OVIRT_ROOT_INSTALL"] == "n":
                logger.info("Root Installation Not Required, Finished.")
                return True
        self.oldtitle=None
        grub_config_file = None
        if _functions.findfs("Boot") and _functions.is_upgrade():
            grub_config_file = "/boot/grub/grub.conf"
            if not _functions.connect_iscsi_root():
                return False
        _functions.mount_liveos()
        if os.path.ismount("/liveos"):
            if os.path.exists("/liveos/vmlinuz0") \
                              and os.path.exists("/liveos/initrd0.img"):
                grub_config_file = self.grub_config_file
        elif not _functions.is_firstboot():
            # find existing iscsi install
            if _functions.findfs("Boot"):
                grub_config_file = "/boot/grub/grub.conf"
            elif os.path.ismount("/dev/.initramfs/live"):
                if not _functions.grub2_available():
                    grub_config_file = "/dev/.initramfs/live/grub/grub.conf"
                else:
                    grub_config_file = "/dev/.initramfs/live/grub2/grub.cfg"
            elif os.path.ismount("/run/initramfs/live"):
                grub_config_file = "/run/initramfs/live/grub/grub.conf"
            if _functions.is_upgrade() and not _functions.is_iscsi_install():
                _functions.mount_liveos()
                grub_config_file = "/liveos/grub/grub.conf"
        if _functions.is_efi_boot():
            logger.debug(str(os.listdir("/liveos")))
            _functions.system("umount /liveos")
            _functions.mount_efi(target="/liveos")
            if self.efi_dir_name == "fedora":
                grub_config_file = "/liveos/EFI/fedora/grub.cfg"
            else:
                grub_config_file = "/liveos/EFI/redhat/grub.conf"
        if _functions.is_iscsi_install() or _functions.findfs("Boot"):
            grub_config_file = "/boot/grub/grub.conf"
        grub_config_file_exists = grub_config_file is not None \
            and os.path.exists(grub_config_file)
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
        if _functions.is_iscsi_install() or _functions.findfs("Boot"):
            self.boot_candidate = None
            boot_candidate_names = ["BootBackup", "BootUpdate", "BootNew"]
            for trial in range(1, 3):
                time.sleep(1)
                _functions.system("partprobe")
                for candidate_name in boot_candidate_names:
                    logger.debug(os.listdir("/dev/disk/by-label"))
                    if _functions.findfs(candidate_name):
                        self.boot_candidate = candidate_name
                        break
                logger.debug("Trial %s to find candidate (%s)" % \
                             (trial, candidate_name))
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
            _functions.system("umount /boot")
            _functions.system("mount %s /boot &>/dev/null" \
                              % boot_candidate_dev)

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
                                                              candidate_name))
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
                _functions.system("mkdir -p /liveos/efi/EFI/redhat")
                if _functions.is_iscsi_install() or _functions.is_efi_boot():
                    shutil.copy("/tmp/grub.efi",
                                "/liveos/efi/EFI/redhat/grub.efi")
                else:
                    shutil.copy("/boot/efi/EFI/redhat/grub.efi",
                          "/liveos/efi/EFI/redhat/grub.efi")
                if _functions.is_iscsi_install() or _functions.findfs("BootNew"):
                    self.disk = _functions.findfs("BootNew")
                if not "/dev/mapper/" in self.disk:
                    efi_disk = self.disk[:-1]
                else:
                    efi_disk = re.sub("p[1,2,3]$", "", self.disk)
                # generate grub legacy config for efi partition
                #remove existing efi entries
                _functions.remove_efi_entry(_functions.PRODUCT_SHORT)
                if self.efi_dir_name == "fedora":
                    _functions.add_efi_entry(_functions.PRODUCT_SHORT,
                                             ("\\EFI\\%s\\grubx64.efi" %
                                              self.efi_dir_name),
                                             efi_disk)
                else:
                    _functions.add_efi_entry(_functions.PRODUCT_SHORT,
                                             ("\\EFI\\%s\\grub.efi" %
                                              self.efi_dir_name),
                                             efi_disk)
        self.kernel_image_copy()

        # reorder tty0 to allow both serial and phys console after installation
        if _functions.is_iscsi_install() or _functions.findfs("BootNew"):
            self.root_param = "root=live:LABEL=Root"
            if "OVIRT_NETWORK_LAYOUT" in OVIRT_VARS and \
                OVIRT_VARS["OVIRT_NETWORK_LAYOUT"] == "bridged":
                network_conf = "ip=br%s:dhcp bridge=br%s:%s" % \
                                (OVIRT_VARS["OVIRT_BOOTIF"],
                                 OVIRT_VARS["OVIRT_BOOTIF"],
                                 OVIRT_VARS["OVIRT_BOOTIF"])
            else:
                network_conf = "ip=%s:dhcp" % OVIRT_VARS["OVIRT_BOOTIF"]
            self.bootparams = "netroot=iscsi:%s::%s::%s %s " % (
                OVIRT_VARS["OVIRT_ISCSI_TARGET_HOST"],
                OVIRT_VARS["OVIRT_ISCSI_TARGET_PORT"],
                OVIRT_VARS["OVIRT_ISCSI_TARGET_NAME"],
                network_conf)
            if "OVIRT_ISCSI_NAME" in OVIRT_VARS:
                self.bootparams+= "iscsi_initiator=%s " % \
                    OVIRT_VARS["OVIRT_ISCSI_NAME"]
        else:
            self.root_param = "root=live:LABEL=Root"
            self.bootparams = "ro rootfstype=auto rootflags=ro "
        self.bootparams += OVIRT_VARS["OVIRT_BOOTPARAMS"].replace(
                                                            "console=tty0", ""
                                                            ).replace(
                                                            "rd_NO_MULTIPATH",
                                                            "")
        if " " in self.disk or os.path.exists("/dev/cciss"):
            # workaround for grub setup failing with spaces in dev.name:
            # use first active sd* device
            self.disk = re.sub("p[1,2,3]$", "", self.disk)
            grub_disk_cmd = ("multipath -l " +
                             "\"" + self.disk + "\" " +
                             "| egrep -o '[0-9]+:.*' " +
                             "| awk '/ active / {print $2}' " +
                             "| head -n1")
            logger.debug(grub_disk_cmd)
            grub_disk = _functions.subprocess_closefds(grub_disk_cmd,
                                            shell=True,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
            grub_disk_output, grub_disk_err = grub_disk.communicate()
            self.disk = grub_disk_output.strip()
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
                with open("%s/version" % self.live_path) as version:
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

        if _functions.is_iscsi_install() or _functions.findfs("BootNew"):
            # copy default for when Root/HostVG is inaccessible(iscsi upgrade)
            shutil.copy(_functions.OVIRT_DEFAULTS, "/boot")
            # mark new Boot ready to go, reboot() in ovirt-function switches it
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
                _system.async_reboot()
            return True
        else:
            return False
