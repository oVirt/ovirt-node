#!/bin/bash

#
# DESCRIPTION
#

COMMONLIB=${IGOR_LIBDIR}/common/common.sh
[[ -e $COMMONLIB ]] && . $COMMONLIB

FAILED=true

N=60

while [[ $N -gt 0 ]];
do
    grep "Install Hypervisor" /dev/vcs1 && {
        echo "Installer appears to be running, passed."
        FAILED=false
        break
    }

    sleep 1
    N=$(($N -1 ))
done

if $FAILED;
then
  exit 1
fi

exit 0
