#!/bin/bash

#
# Services that are expectedt to be running
#

SERVICES="sshd"


COMMONLIB=${IGOR_LIBDIR}/common/common.sh
[[ -e $COMMONLIB ]] && . $COMMONLIB

FAILED=false

for SERVICE in $SERVICES
do
  if service $SERVICE status;
  then
    echo "Running: $SERVICE"
  else
    echo "NOT running: $SERVICE"
    FAILED=true
  fi
done

if $FAILED;
then
  exit 1
fi

exit 0
