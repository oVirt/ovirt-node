#!/bin/bash
# local_boot_trigger.sh - access given URL to signal that node installation
# is done
#
# Scripts in /etc/ovirt-config-boot.d/ are executed just before the node is
# rebooted. This one calls an URL given as a boot parameter e.g.
# local_boot_trigger=http://cobbler.server.example.com/cblr/svc/op/nopxe/system/@HOSTNAME@
# where @HOSTNAME@ is replaced by $(hostname)
# In this example, Cobbler is triggered to change pxelinux config for that
# system to perform a local boot when /etc/cobbler/settings/pxe_just_once
# is set to 1.

trigger_url=
for i in $(cat /proc/cmdline); do
    case $i in
        local_boot_trigger=*)
            trigger_url=${i#local_boot_trigger=}
            ;;
    esac
done

if [ -n "$trigger_url" ]; then
    trigger_url=$(echo $trigger_url | sed -e "s/@HOSTNAME@/$(hostname)/")
    curl --insecure "$trigger_url" 2>&1 >> /var/log/ovirt.log
fi

