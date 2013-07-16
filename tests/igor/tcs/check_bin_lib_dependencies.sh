#!/bin/bash

#
# Check that all library requirements of
# well known binaries are met
#
igor_highlight() { echo "= $@ ="; }
igor_debug() { echo "[DEBUG] $@"; }
COMMONLIB=${IGOR_LIBDIR}/common/common.sh
[[ -e $COMMONLIB ]] && . $COMMONLIB

FAILED=false

BINARIES="/usr/bin/qemu-system-*"

igor_highlight "Checking the following binaries for missing libraries: $BINARIES" "="
echo ""

for BINARY in $BINARIES;
do
  igor_highlight "Checking $BINARY"

  if ldd $BINARY | grep -q "not found";
  then
    igor_debug "Missing dependencies found:"
    ldd $BINARY
    FAILED=true
  fi
done

if $FAILED;
then
  exit 1
fi

exit 0
