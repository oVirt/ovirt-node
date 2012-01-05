#!/usr/bin/python
# ovirtfunctions.py - Copyright (C) 2010 Red Hat, Inc.
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

import subprocess
from subprocess import Popen, PIPE, STDOUT
import os
import tempfile
import string
import sys
import augeas
import socket
import fcntl
import struct
import hashlib
import shutil
import re
import gudev
import cracklib
import libvirt
import logging

OVIRT_LOGFILE="/var/log/ovirt.log"
OVIRT_TMP_LOGFILE="/tmp/ovirt.log"

# label of the oVirt partition
OVIRT_LABEL="OVIRT"
# configuration values are loaded in the following order:
# 1. /etc/sysconfig/node-config sets the default values
# 2. /etc/default/ovirt is loaded to override defaults with karg values
NODE_SYSCONFIG="/etc/sysconfig/node-config"
OVIRT_DEFAULTS="/etc/default/ovirt"
aug = augeas.Augeas()
#   workaround for bind-mounted files
#   see https://fedorahosted.org/augeas/ticket/32
aug.set("/augeas/save/copy_if_rename_fails", "")

# read product / version info
PRODUCT_SHORT = aug.get("/files/etc/default/version/PRODUCT_SHORT")
if PRODUCT_SHORT == None:
    PRODUCT_SHORT = "oVirt"
else:
    PRODUCT_SHORT = PRODUCT_SHORT.strip("'\"")
PRODUCT_VERSION = aug.get("/files/etc/default/version/VERSION")
PRODUCT_RELEASE = aug.get("/files/etc/default/version/RELEASE")

OVIRT_VARS = {}
# Parse all OVIRT_* variables

def parse_defaults():
    global OVIRT_VARS
    if os.path.exists(NODE_SYSCONFIG):
        try:
            f = open(NODE_SYSCONFIG, 'r')
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
        except:
            pass

    f = open(OVIRT_DEFAULTS, 'r')
    for line in f:
        try:
            line = line.strip()
            key, value = line.split("=", 1)
            key = key.strip("=")
            value = value.strip("\"")
            OVIRT_VARS[key] = value
        except:
            pass
    f.close()
    return OVIRT_VARS


# fallback when default is empty
#OVIRT_STANDALONE=${OVIRT_STANDALONE:-0}

OVIRT_BACKUP_DIR="/var/lib/ovirt-backup"

MANAGEMENT_SCRIPTS_DIR="/etc/node.d"

def log(log_entry):
    if is_firstboot():
        log_file = open(OVIRT_TMP_LOGFILE, "a")
    else:
        log_file = open(OVIRT_LOGFILE, "a")
    try: 
        log_file.write(log_entry +"\n")
    except:
        log_file.write(str(log_entry))
    log_file.close()

def augtool(oper, key, value):
    if oper == "set":
        aug.set(key, value)
        aug.save()
        return
    elif oper == "rm":
        aug.remove(key)
        aug.save()
        return
    elif oper == "get":
        value = aug.get(key)
        return value
    elif oper == "match":
        value = aug.match(key)
        return value

def augtool_get(key):
    value = aug.get(key)
    return value
# return 1 if oVirt Node is running in standalone mode
# return 0 if oVirt Node is managed by the oVirt Server
def is_managed():
    if "ovirt_standalone" in OVIRT_VARS["OVIRT_BOOTPARAMS"]:
        return False
    else:
        return True

# oVirt Node in standalone mode does not try to contact the oVirt Server
def is_standalone(self):
    if is_managed:
        return False
    else:
        return True

# return 0 if local storage is configured
# return 1 if local storage is not configured
def is_local_storage_configured():
    ret = os.system("lvs HostVG/Config &>/dev/null")
    if ret > 0:
        return False
    return True

# perform automatic local disk installation
# when at least following boot parameters are present:
# for networking - OVIRT_BOOTIF, management NIC
#       if other ip bootparams are not specified, IPv4 DHCP is assumed
# for storage - OVIRT_INIT, local disk to use
#       if ovirt_vol is not specified, default volume sizes are set
def is_auto_install(self):
    if self.OVIRT_VARS.has_key("OVIRT_BOOTIF") and self.OVIRT_VARS.has_key("OVIRT_INIT"):
        return True
    else:
        return False

# return 0 if this is an upgrade
# return 1 otherwise
def is_upgrade(self):
    if self.OVIRT_VARS.has_key("OVIRT_UPGRADE") and self.OVIRT_VARS["OVIRT_UPGRADE"] == 1:
        return True
    else:
        return False

# return 0 if booted from local disk
# return 1 if booted from other media
def is_booted_from_local_disk():
    ret = os.system("grep -q LABEL=Root /proc/cmdline")
    if ret == 0:
        return True
    else:
        return False

def is_rescue_mode():
    ret = os.system("grep -q rescue /proc/cmdline")
    if ret == 0:
        return True
    # check for runlevel 1/single
    else:
        ret = os.system("runlevel|grep -q '1\|S'")
        if ret == 0:
            return True
        return False

def get_ttyname():
    for f in sys.stdin, sys.stdout, sys.stderr:
        if f.isatty():
            tty = os.ttyname(f.fileno()).replace("/dev/","")
            if "pts" in tty:
                tty = tty.replace("/","")
            return tty
    return None

def manual_setup():
    logger.info("Checking For Setup Lockfile")
    tty = get_ttyname()
    if os.path.exists("/tmp/ovirt-setup.%s" % tty):
        return True
    else:
        return False
# was firstboot menu already shown?
# state is stored in persistent config partition
def is_firstboot():
    # check if theres a key first
    if OVIRT_VARS.has_key("OVIRT_FIRSTBOOT"):
        if OVIRT_VARS["OVIRT_FIRSTBOOT"] == "1":
            return True
        elif OVIRT_VARS["OVIRT_FIRSTBOOT"] == "0":
            return False
    # in case there's no key, default to True unless booted from disk
    if is_booted_from_local_disk():
        return False
    else:
        return True

def is_stateless():
    # check if theres a key first
    if OVIRT_VARS.has_key("OVIRT_STATELESS"):
        if OVIRT_VARS["OVIRT_STATELESS"] == "1":
            return True
        elif OVIRT_VARS["OVIRT_STATELESS"] == "0":
            return False
    return False

def disable_firstboot():
    if os.path.ismount("/config"):
        aug.set("/files/etc/default/ovirt/OVIRT_FIRSTBOOT", "0")
        aug.set("/files/etc/default/ovirt/OVIRT_INIT", '""')
        aug.set("/files/etc/default/ovirt/OVIRT_UPGRADE", "0")
        aug.save()
        ovirt_store_config("/etc/default/ovirt")

# Destroys a particular volume group and its logical volumes.
# The input (vg) is accepted as either the vg_name or vg_uuid
def wipe_volume_group(vg):
    vg_name_cmd = "vgs -o vg_name,vg_uuid --noheadings 2>/dev/null | grep -w \"" + vg + "\" | awk '{print $1}'"
    vg_name = subprocess.Popen(vg_name_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    vg = vg_name.stdout.read().strip()
    files_cmd = "grep '%s' /proc/mounts|awk '{print $2}'|sort -r" % vg
    files = subprocess.Popen(files_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    files_output = files.stdout.read()
    for file in files_output.split():
        os.system("umount %s &>/dev/null" % file)
    swap_cmd = "grep '%s' /proc/swaps|awk '{print $1}'" % vg
    swap = subprocess.Popen(swap_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    swap_output = swap.stdout.read().strip()
    for d in swap_output.split():
        os.system("swapoff %s &>/dev/null" % d)
    system("vgchange -an %s" % vg)
    vgremove_cmd = "vgremove -ff %s &>> %s" % (vg, OVIRT_TMP_LOGFILE)
    ret = os.system(vgremove_cmd)
    if ret != 0:
        #retry one more time before failing
        os.system(vgremove_cmd)

# find_srv SERVICE PROTO
#
# reads DNS SRV record
# sets SRV_HOST and SRV_PORT if DNS SRV record found, clears them if not
# Example usage:
# find_srv ovirt tcp
def find_srv(srv, proto):
    domain = subprocess.Popen("dnsdomainname 2>/dev/null", shell=True, stdout=PIPE, stderr=STDOUT)
    domain_output = domain.stdout.read()
    if domain_output == "localdomain":
        domain=""
    # FIXME dig +search does not seem to work with -t srv
    # dnsreply=$(dig +short +search -t srv _$1._$2)
    # This is workaround:
    search = subprocess.Popen("grep search /etc/resolv.conf", shell=True, stdout=PIPE, stderr=STDOUT)
    search_output = search.stdout.read()
    search = search_output.replace("search ","")
    domain_search = domain_output + search_output
    for d in domain_search.split():
        dig_cmd = "dig +short -t srv _%s._%s.%s" % (srv, proto,search)
        dig = subprocess.Popen(dig_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        dig_output = dig.stdout.read()
        dig.poll()
        dig_rc = dig.returncode
        if dig_rc == 0:
            try:
                a,b,port,host = dig_output.split("=", 4)
                return (port, host)
            except:
                logger.error("Unable to find srv records")
        return False

def ovirt_setup_libvirtd(self):
    # just to get a boot warning to shut up
    os.system("touch /etc/resolv.conf")

    # make libvirtd listen on the external interfaces
    os.system("sed -i -e 's/^#\(LIBVIRTD_ARGS=\"--listen\"\).*/\1/' /etc/sysconfig/libvirtd")

    # set up qemu daemon to allow outside VNC connections
    os.system("sed -i -e 's/^[[:space:]]*#[[:space:]]*\(vnc_listen = \"0.0.0.0\"\).*/\1/' /etc/libvirt/qemu.conf")
    # set up libvirtd to listen on TCP (for kerberos)
    os.system('sed -i -e "s/^[[:space:]]*#[[:space:]]*\(listen_tcp\)\>.*/\1 = 1/" \
       -e "s/^[[:space:]]*#[[:space:]]*\(listen_tls\)\>.*/\1 = 0/" \
       /etc/libvirt/libvirtd.conf')

def ovirt_setup_anyterm():
   # configure anyterm
   anyterm_conf = open("/etc/sysconfig/anyterm", "w")
   anyterm_conf.write("ANYTERM_CMD='sudo /usr/bin/virsh console %p'")
   anyterm_conf.write("ANYTERM_LOCAL_ONLY=false")
   anyterm_conf.close()
   # permit it to run the virsh console
   os.system("echo 'anyterm ALL=NOPASSWD: /usr/bin/virsh console *' >> /etc/sudoers")

# mount livecd media
# e.g. CD /dev/sr0, USB /dev/sda1,
# PXE /dev/loop0 (loopback ISO)
# not available when booted from local disk installation
def mount_live():
    ret = os.system('cat /proc/mounts|grep -q "none /live"')
    if ret == 0:
        os.system("umount /live")
    live_dev="/dev/live"
    if not os.path.exists(live_dev):
        ret = os.system("losetup /dev/loop0|grep -q '\.iso'")
        if ret == 0:
            # PXE boot
            live_dev="/dev/loop0"
        else:
            # /dev/live if not exist alternative
            client = gudev.Client(['block'])
            version = open("/etc/default/version")
            for line in version.readlines():
                if "PACKAGE" in line:
                    pkg, pkg_name = line.split("=")
            for device in client.query_by_subsystem("block"):
                if device.has_property("ID_CDROM"):
                    dev = device.get_property("DEVNAME")
                    blkid_cmd = "blkid '%s'|grep -q '%s'" % (dev, pkg_name)
                    ret = os.system(blkid_cmd)
                    if ret == 0:
                        live_dev = dev
    os.system("mkdir -p /live")
    os.system("mount -r " + live_dev + " /live &>/dev/null")
    if os.path.ismount("/live"):
        return True
    else:
        return False

# mount root partition
# boot loader + kernel + initrd + LiveOS
def mount_liveos():
    if os.path.ismount("/liveos"):
        return True
    else:
        os.system("mkdir -p /liveos")
        if not system("mount LABEL=Root /liveos"):
            # just in case /dev/disk/by-label is not using devmapper and fails
            for dev in os.listdir("/dev/mapper"):
                if system("e2label \"/dev/mapper/" + dev + "\" 2>/dev/null|grep Root|grep -v Backup"):
                    system("rm -rf /dev/disk/by-label/Root")
                    system("ln -s \"/dev/mapper/" + dev + "\" /dev/disk/by-label/Root")
                    if system("mount LABEL=Root /liveos"):
                        return True
        else:
            return True

# mount config partition
# /config for persistance
def mount_config():
    # Only try to mount /config if the persistent storage exists
    if os.path.exists("/dev/HostVG/Config"):
        os.system("mkdir -p /config")
        if not os.path.ismount("/config"):
            ret = os.system("mount /dev/HostVG/Config /config")
            if ret > 0:
                return False

        # optional config embedded in the livecd image
        if os.path.exists("/live/config"):
            os.system("cp -rv --update /live/config/* /config")

        # bind mount all persisted configs to rootfs
        filelist_cmd = "find /config -type f"
        filelist = subprocess.Popen(filelist_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        filelist = filelist.stdout.read()
        for f in filelist.split():
            logger.debug("Bind Mounting: " + f)
            if os.path.isfile(f) and f != "/config/files":
                target = string.replace(f, "/config", "")
                mounted_cmd = "grep -q " + target + " /proc/mounts"
                mounted = os.system(mounted_cmd)
                if mounted == 0:
                    # skip if already bind-mounted
                    pass
                else:
                    dirname = os.path.dirname(target)
                    os.system("mkdir -p '%s'" % dirname)
                    os.system("touch '%s'" % target)
                    os.system("mount -n --bind '%s' '%s'" % (f,target))
        return True
    else:
        # /config is not available
        return False

def mount_boot(self):
    if os.path.ismount("/boot"):
       return
    else:
        os.system("mkdir -p /boot")
        os.system("mount LABEL=Boot /boot")

# stop any service which keeps /var/log busy
# keep the list of services
def unmount_logging_services():
    # mapping command->service is lame, but works for most initscripts
    logging_services= []
    prgs_cmd = "cd /etc/init.d|lsof -Fc +D /var/log|grep ^c|sort -u"
    prgs = subprocess.Popen(prgs_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    prgs_output = prgs.stdout.read()
    for prg in prgs_output.split():
        svc = prg = prg[1:]
        ret = os.system("service " + svc +" stop &>/dev/null")
        if ret != 0:
            os.system("pkill " + svc)
        logging_services.append(svc)
    return logging_services
    # debugging help
    #os.system("lsof +D /var/log")

# mount logging partition
# this only gets executed when disk is re-partitioned, HostVG/Logging is empty
def mount_logging():
    if os.path.ismount("/var/log"):
        return True
    if os.path.exists("/dev/HostVG/Logging"):
        logger.info("Mounting log partition")
        # temporary mount-point
        log2 = tempfile.mkdtemp()
        os.system("mount /dev/HostVG/Logging " + log2)
        logging_services = unmount_logging_services()
        # save logs from tmpfs
        os.system("cp -av /var/log/* " + log2 + " &>/dev/null")
        # save temporary log
        if os.path.exists("/tmp/ovirt.log"):
            os.system("cp /tmp/ovirt.log " + log2 +"/ovirt.log-tmp &>> /tmp/ovirt.log")
        os.system("mount --move " + log2 + " /var/log")
        shutil.rmtree(log2)
        os.system("restorecon -rv /var/log &>/dev/null")
        for srv in logging_services:
            os.system("service " + srv + " start &>/dev/null")
        # make sure rsyslog restarts
        os.system("service rsyslog start &>/dev/null")
        return
    else:
        # /var/log is not available
        logger.error("The logging partion has not been created. Please create it at the main menu.")
        return False

def unmount_logging():
    if not os.path.ismount("/var/log"):
        return True
    logger.info("Unmounting log partition")
    # plymouthd keeps /var/log/boot.log
    ret = os.system("plymouth --ping")
    if ret == 0:
        os.system("plymouth --quit")
    logging_services = unmount_logging_services()

    ret = os.system("umount /var/log &>/dev/null")
    if ret > 0:
        return ret
    for srv in logging_services:
        os.system("service " + srv + " start &> /dev/null")
    return

# mount data partition
def mount_data():
    if os.path.ismount("/data"):
        return

    if os.path.exists("/dev/HostVG/Data"):
        os.system("mkdir -p /data")
        os.system("mount /data")
        os.system("mkdir -p /data/images")
        os.system("mkdir -p /data/images/rhev")
        os.system("chown 36:36 /data/images/rhev")
        os.system("mkdir -p /var/lib/libvirt/images")
        os.system("mount /var/lib/libvirt/images")
        os.system("restorecon -rv /var/lib/libvirt/images &>/dev/null")
        os.system("mkdir -p /data/core")
        os.system("mkdir -p /var/log/core")
        os.system("mount /var/log/core")
        os.system("restorecon -rv /var/log/core &>/dev/null")
        return
    else:
        # /data is not available
        logger.error("The data partion has not been created. Please create it at the main menu.")
        return False

def mount_data2():
    if os.path.ismount("/data2"):
        return True

    if os.path.exists("/dev/AppVG/Data2"):
        system("mkdir -p /data2")
        system("mount /data2")

    if os.path.ismount("/data2"):
        return True
    else:
        # /data2 is not available
        logger.error("The data2 volume can not be mounted")
        return False

def md5sum(filename):
    m = hashlib.md5()
    with open(filename) as f:
        data = f.read(4096)
        while data:
            m.update(data)
            data = f.read(4096)
        return m.hexdigest()


STRING_TYPE=(str,unicode)
# persist configuration to /config
#   ovirt_store_config /etc/config /etc/config2 ...
#   copy to /config and bind-mount back

def ovirt_store_config(files):
  if not os.path.ismount("/config"):
    logger.error("/config is not mounted")
    return False
  if isinstance(files,STRING_TYPE):
    files_list = []
    files_list.append(files)
  else:
    files_list=files
  for f in files_list:
    filename = os.path.abspath(f)
    persist_it=True
    # ensure that, if this is a directory
    # that it's not already persisted
    if os.path.isdir(filename):
        if os.path.isdir("/config/" + filename):
            logger.warn("Directory already persisted: " + filename)
            logger.warn("You need to unpersist its child directories and/or files and try again.")
            persist_it=False
            rc = 0

    # if it's a file then make sure it's not already persisted
    if os.path.isfile(filename):
        if os.path.isfile("/config/" + filename):
            md5root=md5sum(filename)
            md5stored=md5sum("/config" + filename)
            if md5root == md5stored:
                logger.warn("File already persisted: " + filename)
                persist_it=False
                rc = 0
            else:
                # persistent copy needs refresh
                if system("umount -n " + filename + " 2> /dev/null"):
                    system("rm -f /config"+ filename)
    if persist_it:
        # skip if file does not exist
        if not os.path.exists(filename):
            logger.warn("Skipping, file: " + filename + " does not exist")
        # skip if already bind-mounted
        if not check_bind_mount(filename):
            dirname = os.path.dirname(filename)
            system("mkdir -p /config/" + dirname)
            if system("cp -a " + filename + " /config"+filename):
                if not system("mount -n --bind /config"+filename+ " "+filename):
                    logger.error("Failed to persist: " + filename)
                    rc = 1
                else:
                    logger.info("File: " + filename + " persisted")
                    rc = True
        # register in /config/files used by rc.sysinit
        ret = os.system("grep -q \"^$" + filename +"$\" /config/files 2> /dev/null")
        if ret > 0:
            os.system("echo "+filename+" >> /config/files")
            logger.info("Successfully persisted: " + filename)
            rc = 0
    else:
        logger.warn(filename + " Already persisted")
        rc = 0
    if rc == 0:
        return True

def is_persisted(filename):
    abspath = os.path.abspath(filename)
    if os.path.exists("/config" + abspath):
        return True
    else:
        return False

# unmount bindmounted config files
#       unmount_config /etc/config /etc/config2 ...
#
# Use before running commands which fail on bindmounted files.
# After the file is replaced, call ovirt_store_config /etc/config ...
# to bindmount the config file again.
#

def check_bind_mount(config_file):
    bind_mount_cmd = 'grep -q "%s ext4" /proc/mounts' % config_file
    if os.system(bind_mount_cmd) == 0:
        return True
    else:
        return False

def unmount_config(files):
    if os.path.ismount("/config"):
      if isinstance(files,STRING_TYPE):
        files_list = []
        files_list.append(files)
      else:
        files_list=files
      for f in files_list:
        filename = os.path.abspath(f)
        if check_bind_mount(filename):
            ret = os.system('umount -n "%s" &>/dev/null' % filename)
            if ret == 0:
                if os.path.exists('/config%s' % filename):
                    # refresh the file in rootfs if it was mounted over
                    if os.system('cp -a /config"%s" "%s" &> /dev/null' % (filename,filename)):
                        return True

# remove persistent config files
#       remove_config /etc/config /etc/config2 ...
#
def remove_config(files):
    # if there are no persisted files then just exit
    if os.path.exists("/config/files"):
        if os.path.getsize('/config/files') == 0:
            print "There are currently no persisted files."
            return True
    if os.path.ismount("/config"):
      if isinstance(files,STRING_TYPE):
        files_list = []
        files_list.append(files)
      else:
        files_list=files
      for f in files_list:
            filename = os.path.abspath(f)
            ret = os.system('grep "^%s$" /config/files > /dev/null 2>&1' % filename)
            if ret == 0:
                if check_bind_mount(filename):
                    ret = os.system('umount -n "%s" &>/dev/null' % filename)
                    if ret == 0:
                        if os.path.isdir(filename):
                            ret = os.system('cp -ar /config/"%s"/* "%s"' % (filename,filename))
                            if ret > 0:
                                logger.error(" Failed to unpersist %s" % filename)
                                return False
                            else:
                                logger.info("%s successully unpersisted" % filename)
                                return True
                        else:
                            if os.path.isfile(filename):
                                # refresh the file in rootfs if it was mounted over
                               ret = os.system('cp -a /config"%s" "%s"' % (filename,filename))
                               if ret > 0:
                                    logger.error("Failed to unpersist %s" % filename)
                                    return False
                               else:
                                   logger.info("%s successully unpersisted" % filename)
                    # clean up the persistent store
                    os.system('rm -Rf /config"%s"' % filename)
                    # unregister in /config/files used by rc.sysinit
                    os.system('sed --copy -i "\|^%s$|d" /config/files' % filename)
                else:
                    logger.warn("%s is not a persisted file." % filename)
            else:
                logger.warn("File not explicitly persisted: %s" % filename)

# ovirt_safe_delete_config
#       ovirt_safe_delete_config /etc/config /etc/config2 ...
#
# Use to *permanently* remove persisted configuration file.
# WARNING: file is shredded and removed
#
def ovirt_safe_delete_config(files):
    if isinstance(files,STRING_TYPE):
        files_list = []
        files_list.append(files)
    else:
        files_list=files
    for f in files_list:
        filename = os.path.abspath(f)
        if check_bind_mount(filename):
            os.system('umount -n "%s" &>/dev/null' % filename)

        os.system('sed --copy -i "\|%s$|d" /config/files' % filename)

        if os.path.isdir(filename):
            for child in subprocess.Popen("ls -d '%s'" % filename, shell=True, stdout=PIPE, stderr=STDOUT).stdout.read():
                ovirt_safe_delete_config(child)
            os.system("rm -rf /config'%s'" % filename)
            os.system("rm -rf '%s'" % filename)
        else:
            os.system("shred -u /config'%s'" % filename)
            os.system("shred -u '%s'" % filename)


# compat function to handle different udev versions
def udev_info(name, query):
    # old udev command with shortopts
    udev_cmd = "udevadm info -n %s -q %s" % (name, query)
    udev = subprocess.Popen(udev_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    udev_output = udev.stdout.read()
    udev.poll()
    udev_rc = udev.returncode
    if udev_rc > 0:
        udev_cmd = "udevadm info --name=%s --query=%s" % (name, query)
        udev = subprocess.Popen(udev_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        udev_output = udev.stdout.read()
        udev.poll()
        udev_rc = udev.returncode
    return udev_output

def get_live_disk():
    live_disk=""
    if os.path.exists("/dev/live"):
        live_disk = os.path.dirname(udev_info("/dev/live","path"))
        if "block" in live_disk:
            live_disk = os.path.basename(udev_info("/dev/live","path")).strip()
    elif os.path.exists("/dev/disk/by-label/LIVE"):
        live_disk = os.path.dirname(udev_info("/dev/disk/by-label/LIVE","path"))
        if "block" in live_disk:
            live_disk = os.path.basename(udev_info("/dev/disk/by-label/LIVE","path")).strip()
    else:
        ret = os.system("losetup /dev/loop0|grep -q '\.iso'")
        if ret != 0:
            client = gudev.Client(['block'])
            version = open("/etc/default/version")
            for line in version.readlines():
                if "PACKAGE" in line:
                    pkg, pkg_name = line.split("=")
            for device in client.query_by_subsystem("block"):
                if device.has_property("ID_CDROM"):
                    dev = device.get_property("DEVNAME")
                    blkid_cmd = "blkid '%s'|grep -q '%s' " % (dev, pkg_name)
                    ret = os.system(blkid_cmd)
                    if ret == 0:
                        live_disk = os.path.basename(dev)
    return live_disk

def backup_file(self, file):
    dir = os.path.dirname(file)
    if dir in os.listdir("/"):
        print "unexpected non-absolute dir: %s" % dir
        sys.exit(1)
    os.system("mkdir -p '%s%s'") % (OVIRT_BACKUP_DIR, dir)
    if os.path.exists(file):
        shutil.copy(file, OVIRT_BACKUP_DIR + file)
    #test -f "$1" && cp -pf "$1" "$OVIRT_BACKUP_DIR/${dir:1}"

#add_if_not_exist() {
#    string="$1"
#    file="$2"
#
#    grep -qE "^[[:space:]]*$string($|#|[[:space:]])" "$file" \
#        || echo "$string" >> "$file"
#}

# reboot wrapper
#   cleanup before reboot

def finish_install():
    logger.info("Completing Installation")
    if not OVIRT_VARS.has_key("OVIRT_ISCSI_ENABLED"):
        # setup new Root if update is prepared
        root_update_dev = findfs("RootUpdate")
        root_dev = findfs("Root")
        e2label_rootbackup_cmd = "e2label '%s' RootBackup" % root_dev
        e2label_root_cmd = "e2label '%s' Root" % root_update_dev
        logger.debug(e2label_rootbackup_cmd)
        logger.debug(e2label_root_cmd)
        subprocess.Popen(e2label_rootbackup_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        subprocess.Popen(e2label_root_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    # run post-install hooks
    # e.g. to avoid reboot loops using Cobbler PXE only once
    # Cobbler XMLRPC post-install trigger (XXX is there cobbler SRV record?):
    # wget "http://192.168.50.2/cblr/svc/op/trig/mode/post/system/$(hostname)"
    #   -O /dev/null
    hookdir="/etc/ovirt-config-boot.d"
    for hook in os.listdir(hookdir):
        os.system(os.path.join(hookdir,hook))
    return True

def is_valid_ipv4(ip_address):
    try:
        socket.inet_pton(socket.AF_INET, ip_address)
        return True
    except socket.error:
        return False

def is_valid_ipv6(ip_address):
    try:
        socket.inet_pton(socket.AF_INET6, ip_address)
        return True
    except socket.error:
        return False

def is_valid_hostname(hostname):
    regex_1 = "([a-zA-Z]|[0-9])(([a-zA-Z]|[0-9]|-)*([a-zA-Z]|[0-9]))?$"
    regex_2 = "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$"
    if re.match(regex_1, hostname):
        return True
    else:
        if re.match(regex_2, hostname):
            return True
        else:
            return False

def is_valid_nfs(nfs_entry):
    regex = "^([a-zA-Z0-9_\-]+)([\.][a-zA-Z0-9_\-]+)+([:][/][a-zA-Z0-9\~\(\)_\-]*)+([\.][a-zA-Z0-9\(\)_\-]+)*"
    if re.match(regex, nfs_entry):
        ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', nfs_entry)
        try:
           if ip[0]:
               if is_valid_ipv4(ip[0]):
                   return True
               else:
                   return False
        except:
            # hostname will fail on purpose
            return True
    else:
        return False

def is_valid_host_port(host):
    regex = "^([a-zA-Z0-9_\-]+)([\.][a-zA-Z0-9_\-]+)+([:][0-9\~\(\)_\-]*)+([\.][0-9]+)*$"
    if re.match(regex, host):
        return True
    else:
        return False

def is_valid_url(host):
    regex = "(((http|https)://)|(www\.))+(([a-zA-Z0-9\._-]+\.[a-zA-Z]{2,6})|([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}))(/[a-zA-Z0-9\&amp;%_\./-~-]*)?"
    if re.match(regex, host):
        return True
    else:
        return False

def is_valid_host_or_ip(host_or_ip):
    if host_or_ip != "" :
        if is_valid_ipv4(host_or_ip):
            return True
        if is_valid_ipv6(host_or_ip):
            return True
        if is_valid_hostname(host_or_ip):
            return True
        else:
            return False
    else:
        return True

def is_valid_user_host(user):
    regex = "^[\w-]+(\.[\w-]+)*@([a-z0-9-]+(\.[a-z0-9-]+)*?\.[a-z]{2,6}|(\d{1,3}\.){3}\d{1,3})(:\d{4})?$"
    if re.match(regex, user):
        return True
    else:
        return False

def is_valid_iqn(iqn):
    regex="^iqn\.(\d{4}-\d{2})\.([^:]+):"
    if re.match(regex, iqn):
        return True
    else:
        return False

# Check if networking is already up
def network_up():
    ret = os.system("ip addr show | grep -q 'inet.*scope global'")
    if ret == 0:
        return True
    return False

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        ip = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])
    except:
        ip = ""
    return ip

def get_netmask(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        netmask = fcntl.ioctl(s, 0x891b, struct.pack('256s', ifname))[20:24]
        netmask = socket.inet_ntoa(netmask)
    except:
        netmask = ""
    return netmask

def get_gateway(ifname):
    cmd = "ip route list dev "+ ifname + " | awk ' /^default/ {print $3}'"
    result = subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    result = result.stdout.read().strip()
    return result

def get_ipv6_address(interface):
    inet6_lookup_cmd = "ip addr show dev %s | awk '$1==\"inet6\" && $4==\"global\" { print $2 }'" % interface
    inet6_lookup = subprocess.Popen(inet6_lookup_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    ipv6_addr = inet6_lookup.stdout.read().strip()
    try:
        ip, netmask = ipv6_addr.split("/")
        return (ip,netmask)
    except:
        logger.debug("unable to determine ip/netmask from: " + ipv6_addr)
    return False

def get_ipv6_gateway(ifname):
    cmd = "ip route list dev "+ ifname + " | awk ' /^default/ {print $3}'"
    result = subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    result = result.stdout.read().strip()
    return result

def has_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(),
            0x8915, struct.pack('256s', ifname[:15]))[20:24])
        return True
    except IOError:
        return False

def is_valid_port(port_number):
    regex = "^(6553[0-5]|655[0-2]\d|65[0-4]\d\d|6[0-4]\d{3}|[1-5]\d{4}|[1-9]\d{0,3}|0)$"
    if re.match(regex, port_number):
        return True
    else:
        return False

# Cleans partition tables
def wipe_partitions(drive):
    logger.info("Wiping old boot sector")
    os.system("dd if=/dev/zero of=\""+ drive +"\" bs=1024K count=1 &>>" + OVIRT_TMP_LOGFILE)
    # zero out the GPT secondary header
    logger.info("Wiping secondary gpt header")
    disk_kb = subprocess.Popen("sfdisk -s \""+ drive +"\" 2>/dev/null", shell=True, stdout=PIPE, stderr=STDOUT)
    disk_kb_count = disk_kb.stdout.read()
    os.system("dd if=/dev/zero of=\"" +drive +"\" bs=1024 seek=$(("+ disk_kb_count+" - 1)) count=1 &>>" + OVIRT_TMP_LOGFILE)
    if os.path.exists("/dev/mapper/HostVG-Swap"):
        os.system("swapoff -a")
    # remove remaining HostVG entries from dmtable
    for lv in os.listdir("/dev/mapper/"):
        if "HostVG" in lv:
            os.system("dmsetup remove " +lv + " &>>" + OVIRT_TMP_LOGFILE)


def test_ntp_configuration(self):
    # stop ntpd service for testing
    os.system("service ntpd stop > /dev/null 2>&1")
    for server in OVIRT_VARS["NTP"].split():
        ret = os.system("ntpdate %s > /dev/null 2>&1" % server)
        if ret > 0:
            logger.error("Unable to verify NTP server: %s" % server)
        else:
            logger.info("Verified NTP server: %s" % server)
    os.system("service ntpd start")

def get_dm_device(device):
    dev_major_cmd="stat -c '%t' " + "\"/dev/" + device + "\""
    dev_minor_cmd="stat -c '%T' " + "\"/dev/" + device + "\""
    major_lookup = subprocess.Popen(dev_major_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    minor_lookup = subprocess.Popen(dev_minor_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    major_lookup = major_lookup.stdout.read().strip()
    minor_lookup = minor_lookup.stdout.read().strip()
    dm_cmd = "ls /dev/mapper"
    dm_cmd = subprocess.Popen(dm_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    devices = dm_cmd.stdout.read().strip()
    for dm in devices.split("\n"):
        dm_major_cmd="stat -c '%t' " + "\"/dev/mapper/" + dm + "\""
        dm_minor_cmd="stat -c '%T' " + "\"/dev/mapper/" + dm + "\""
        dm_major_lookup = subprocess.Popen(dm_major_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        dm_minor_lookup = subprocess.Popen(dm_minor_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        dm_major_lookup = dm_major_lookup.stdout.read().strip()
        dm_minor_lookup = dm_minor_lookup.stdout.read().strip()
        if dm_major_lookup == major_lookup and minor_lookup == dm_minor_lookup:
            dm = "/dev/mapper/" + dm
            return dm

def check_existing_hostvg(install_dev):
    if install_dev is "":
        devices_cmd = "pvs --separator=\":\" -o pv_name,vg_name --noheadings 2>/dev/null| grep HostVG |awk -F \":\" {'print $1'}"
    else:
        devices_cmd="pvs --separator=: -o pv_name,vg_name --noheadings 2>/dev/null| grep -v '%s' | grep HostVG | awk -F: {'print $1'}" % install_dev
    devices_cmd = subprocess.Popen(devices_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    devices = devices_cmd.stdout.read().strip()
    if len(devices) > 0:
        logger.error("There appears to already be an installation on another device:")
        for device in devices.split(":"):
            logger.error(device)
        logger.error("The installation cannot proceed until the device is removed")
        logger.error("from the system of the HostVG volume group is removed")
        return devices
    else:
        return False

def translate_multipath_device(dev):
    #trim so that only sdX is stored, but support passing /dev/sdX
    logger.debug("Translating: %s" % dev)
    if dev is None:
        return False
    if "/dev/mapper" in dev:
        return dev
    if "/dev/cciss" in dev:
        cciss_dev_cmd = "cciss_id " + dev
        cciss_dev = subprocess.Popen(cciss_dev_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        dev = "/dev/mapper/" + cciss_dev.stdout.read().strip()
    dm_dev_cmd = "multipath -ll '%s' | egrep dm-[0-9]+" % dev
    dm_dev = subprocess.Popen(dm_dev_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    (dm_dev_output, dummy) = dm_dev.communicate()
    if dm_dev.returncode > 0:
        return dev
    else:
        logger.debug("Translated to: /dev/mapper/" + dm_dev_output.split()[0])
        return "/dev/mapper/"+dm_dev_output.split()[0]

def pwd_lock_check(user):
    passwd_cmd = "passwd -S %s" % user
    passwd = subprocess.Popen(passwd_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    passwd, err = passwd.communicate()
    if "locked" in passwd:
        return True
    else:
        return False

def pwd_set_check(user):
    passwd_cmd = "passwd -S %s" % user
    passwd = subprocess.Popen(passwd_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    passwd, err = passwd.communicate()
    if "set" in passwd:
        return True
    else:
        return False

def get_installed_version_number():
    if mount_liveos():
        existing_version = open("/liveos/version")
        existing_install = {}
        for line in existing_version.readlines():
            try:
                key, value = line.strip().split("=")
                value = value.replace("'", "")
                existing_install[key] = value
            except:
                pass
        if existing_install.has_key("VERSION") and existing_install.has_key("RELEASE"):
            return [existing_install["VERSION"],existing_install["RELEASE"]]
        else:
            return False

def get_media_version_number():
    new_install = {}
    if mount_live():
        try:
            upgrade_version = open("/live/isolinux/version")
        except:
            upgrade_version = open("/live/syslinux/version")
        for line in upgrade_version.readlines():
            try:
                key, value = line.strip().split("=")
                value = value.replace("'", "")
                new_install[key] = value
            except:
                pass
    else:
        logger.error("Failed to mount_live()")
        return False
    if new_install.has_key("VERSION") and new_install.has_key("RELEASE"):
        return [new_install["VERSION"],new_install["RELEASE"]]
    return False

def findfs(label):
    system("partprobe /dev/mapper/*")
    system("udevadm settle")
    blkid_cmd = "/sbin/blkid -c /dev/null -l -o device -t LABEL=\"" + label + "\""
    blkid = subprocess.Popen(blkid_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    blkid_output = blkid.stdout.read().strip()
    return blkid_output

def system(command):
    if os.system(command + " &>> " + OVIRT_TMP_LOGFILE) == 0:
        os.system("echo '\n' >> " + OVIRT_TMP_LOGFILE)
        return True
    else:
        return False

def password_check(password_1, password_2):
          if password_1 != "" and password_2 != "":
              if password_1 != password_2:
                  return (1, "Passwords Do Not Match\n\n\n\n\n\n")
              try:
                  cracklib.FascistCheck(password_1)
              except ValueError, e:
                  return (0, "You have provided a weak password!\nStrong passwords contain a mix of uppercase,\
                          lowercase, numeric and punctuation characters.\n\nThey are six or more characters long and \
                          do not contain dictionary words")
              return (0, "\n\n\n\n\n\n")
          elif password_1 != "" and password_2 == "":
              return (1, "Please Confirm Password\n\n\n\n\n\n")
          return (1, "\n\n\n\n\n\n")

def get_logrotate_size():
    size = augtool_get("/files/etc/logrotate.d/ovirt-node/rule/size")
    if "m" in size.lower():
        multiplier = 1024
    else:
        multiplier = 1
    size = size.lower().rstrip("kmb")
    size = int(size) * multiplier
    return str(size)

def get_virt_hw_status():
    hwvirt_msg = ""
    try:
        conn = libvirt.openReadOnly(None)
        libvirt_capabilities = conn.getCapabilities()
    except:
        return "(Failed to Establish Libvirt Connection)"
    if "kvm" in libvirt_capabilities:
        logger.info("Hardware virtualization detected")
    else:
        hwvirt_msg = "Virtualization hardware is unavailable."
        cpuflags_cmd = "cat /proc/cpuinfo |grep ^flags|tail -n 1"
        cpuflags_lookup = subprocess.Popen(cpuflags_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        cpuflags = cpuflags_lookup.stdout.read().strip()
        if "vmx" in cpuflags or "svm" in cpuflags:
            hwvirt_msg = "(Virtualization hardware detected but disabled)"
        else:
            hwvirt_msg = "(Virtualization hardware was not detected)"
    return hwvirt_msg

def get_mac_address(dev):
    nic_addr_file = open("/sys/class/net/" + dev + "/address")
    dev_address = nic_addr_file.read().strip()
    return dev_address

def logical_to_physical_networks():
    networks = {}
    client = gudev.Client(['net'])
    for device in client.query_by_subsystem("net"):
        try:
            dev_interface = device.get_property("INTERFACE")
            dev_address = get_mac_address(dev_interface)
            bridge_cmd = "/files/etc/sysconfig/network-scripts/ifcfg-%s/BRIDGE" % str(dev_interface)
            dev_bridge =  augtool_get(bridge_cmd)
        except:
            pass
        if not dev_bridge is None:
            networks[dev_bridge] = (dev_interface,dev_address)
    return networks

def pad_or_trim(length, string):
    to_rem = len(string) - length
    # if negative pad name space
    if to_rem < 0:
        while abs(to_rem) != 0:
            string = string + " "
            to_rem = to_rem + 1
    else:
        string = string.rstrip(string[-to_rem:])
    return string

def is_efi_boot():
    if os.path.exists("/sys/firmware/efi"):
        return True
    else:
        return False

class PluginBase(object):
    """Base class for pluggable Hypervisor configuration options.

    Configuration plugins are modules in ovirt_config_setup package.
    They provide implementation of this base class, adding specific
    form elements and processing.
    """

    def __init__(self, name, screen):
        """Initialize a PluginBase instance

        name -- configuration option label
        screen -- parent NodeConfigScreen
        """
        self.name = name
        """A name of the configuration option."""
        self.ncs = screen
        """A NodeConfigScreen instance."""

    def label(self):
        """Returns label for the configuration option."""
        return self.name

    def form(self):
        """Returns form elements for the configuration option.
        Must be implemented by the child class.
        """
        pass

    def action(self):
        """Form processing action for the Hypervisor configuration option.
        Must be implemented by the child class.
        """
        pass

OVIRT_VARS = parse_defaults()

# setup logging facility
if is_firstboot():
    log_file = OVIRT_TMP_LOGFILE
else:
    log_file = OVIRT_LOGFILE

def setup_custom_logger():
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger = logging.getLogger(PRODUCT_SHORT)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

setup_custom_logger()
logger = logging.getLogger(PRODUCT_SHORT)
