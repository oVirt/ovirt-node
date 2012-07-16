#!/bin/bash

#
# Check dmesg for anomalies
#

COMMONLIB=${IGOR_LIBDIR}/common/common.sh
[[ -e $COMMONLIB ]] && . $COMMONLIB

FAILED=false



igor_highlight "Checking dmesg" "="
echo ""

igor_highlight "Looking for kernel Oops"
if dmesg | egrep "^BUG: ";
then
  igor_debug "Kernel Oops found:"
  dmesg
  FAILED=true
else
  igor_debug "No kernel Oops found"
fi

for L in alert emerg;
do
  igor_highlight "Looking for '$L' messages in dmesg"
  N=$(dmesg -l $L | wc -l)
  [[ $N -gt 0 ]] && {
    igor_debug "Messages with level '$L' found in dmesg:"
    dmesg -l $L
    FAILED=true
  } || {
    igor_debug "No '$L' messages in dmesg"
  }
done



if $FAILED;
then
  return 1
fi

exit 0
