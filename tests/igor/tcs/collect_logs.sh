#!/bin/bash

#
# Collect some common ovirt node logs and upload them
#

COMMONLIB=${IGOR_LIBDIR}/common/common.sh
[[ -e $COMMONLIB ]] && . $COMMONLIB

FAILED=false

dmesg 2> /tmp/dmesg

LOGS="/var/log/messages /var/log/ovirt.log /tmp/ovirt.log /var/log/audit.log /tmp/dmesg"

for LOG in $LOGS
do
    [[ -e "$LOG" ]] && {
        igor_add_artifact "$(echo $LOG | sed -r 's#/#.#g')" "$LOG"
    } || {
        echo "'$LOG' does not exist"
    }
done

if $FAILED;
then
  exit 1
fi

exit 0
