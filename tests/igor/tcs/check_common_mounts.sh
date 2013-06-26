#!/bin/bash -x

#
# Verify that the network is configured correctly
#

igor_highlight() { echo "== $1 ==" ; }
igor_debug() { echo "[D] $@" ; }

COMMONLIB=${IGOR_LIBDIR}/common/common.sh
[[ -e $COMMONLIB ]] && . $COMMONLIB

igor_highlight "Checking for well-known mount points" "="

target_has_sources() {
    target=$1
    shift 1
    sources=$@
    igor_debug "Checking target '$target' for '$sources'"
    for source in $sources;
    do
        igor_debug "Checking '$source'"
        findmnt "$target" | egrep "^$target\s+$source" || return 1
    done
}

igor_highlight "Check that /var/log is mounted correctly"
target_has_sources "/var/log" ".*HostVG-Logging" "none.*tmpfs"

igor_highlight "Check that /data is mounted correctly"
target_has_sources "/data" ".*HostVG-Data"
