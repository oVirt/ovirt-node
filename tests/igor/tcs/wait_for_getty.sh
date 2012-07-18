#!/bin/bash

#
# Wait for a getty to appear
#

TIMEOUT=50

[[ -x /bin/systemctl ]] && systemctl start getty@tty1.service

while [[ $TIMEOUT -gt 0 ]];
do
    echo "Timeout: $TIMEOUT"
    if [[ -x /bin/systemctl ]];
    then
        systemctl -a
        systemctl is-active getty.target && exit 0
    else
        ps -Af
        ps -A | grep getty && exit 0
    fi
    sleep 1
    TIMEOUT=$(($TIMEOUT - 1))
done

echo "No getty disocovered."

exit 1
