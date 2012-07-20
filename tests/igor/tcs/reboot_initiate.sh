#!/bin/bash

. ${IGOR_LIBDIR}/common/common.sh

. /usr/libexec/ovirt-functions

echo "Setting marker to detect reboot."
igor_set_reboot_marker

echo "Reboot initiated"
igor_step_succeeded
reboot

# Don't continue, we want to restart
sleep 60

exit 0
