#!/bin/bash

. ${IGOR_LIBDIR}/common/common.sh

. /usr/libexec/ovirt-functions

igor_step_succeeded
reboot

# Don't continue, we want to restart
sleep 60

exit 0
