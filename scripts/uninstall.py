#!/usr/bin/python
#
# uninstall.py - destroys an installed copy of the oVirt node

# SYNOPSIS
# Destroys the HostVG volume group and logical volumes.
#
import ovirtfunctions
import subprocess
from subprocess import STDOUT, PIPE

def uninstall():
    if os.path.isdir("/dev/HostVG"):
        log("Uninstalling node")
        log("Detaching logging")
        # multipathd holds all mounts under /var in a private namespace
        os.system("service multipathd stop")
        os.system("rm -f /var/lib/multipath/bindings")
        unmount_logging()
        unmount_config("/etc/default/ovirt")
        #get partition info
        root2=""
        rc = os.system("findfs LABEL=RootBackup 2>&1 >/dev/null")
        if rc == 0:
            root2 = "RootBackup"
        rc = os.system("findfs LABEL=RootUpdate 2>&1 >/dev/null")
        if rc == 0:
            root2 = "RootUpdate"
        rc = os.system("findfs LABEL=RootNew 2>&1 >/dev/null")
        if rc == 0:
            root2 = "RootNew"

        root_label_lookup_cmd = "findfs LABEL=Root"
        root_label_lookup = subprocess.Popen(root_label_lookup_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        root_device = root_label_lookup.stdout.read()
        if root_device is None:
            log("Can't find Root device")
            sys.exit(2)
        root_dev, root_part = get_part_info(root_device) 

        root2_label_lookup_cmd = "findfs LABEL=" + root2
        root2_label_lookup = subprocess.Popen(root2_label_lookup_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        root2_device = root2_label_lookup.stdout.read()
        if root2_device is None:
            log("Can't find RootBackup/RootNew/RootUpdate device")
            sys.exit(3)
        root2_dev, root2_part = get_part_info(root2_device)

        pv_lookup_cmd = "pvs --noheadings -o pv_name,vg_name | grep HostVG | awk '{print $1}'"
        pv_lookup = subprocess.Popen(pv_lookup_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        pv_device = pv_lookup.stdout.read()
        if pv_device is None:
            log("Can't find HostVG device")
            sys.exit(4)
        pv_dev, pv_part = get_part_info(pv_device)

        log("Removing volume group")
        wipe_volume_group("HostVG")
        log("Removing partitions")
        os.system("parted -s " + root_dev + "\"rm " + root_part + "\"")
        os.system("pvremove " + vg_dev)
        os.system("parted -s " + root2_dev + "\"rm " + root2_part +"\"")
        os.system("parted -s " + vg_dev + "\"rm " + vg_part + "\"")
        wipe_partitions(pv_dev)
        wipe_partitions(root_dev)
        wipe_partitions(root2_dev)
        #restart multipath
        os.system("multipath -F")
        os.system("multipath -v3")
        os.system("service multipathd start")
        log("Finished uninstalling node.")
    else:
	    log("There is no installed node instance to remove.")
	    log("Aborting")
	    sys.exit(1)
