#!/bin/bash

#
# Wait for a getty to appear
#

TIMEOUT=20

timestamp() { date +%s ; }

STARTTIME=$(timestamp)

while [[ $(timestamp) -lt $(($STARTTIME + $TIMEOUT)) ]];
do
    ps -A | grep getty && exit 0
    sleep 5
done

exit 1
