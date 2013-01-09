#!/bin/bash

#
# Check augeas for lense errors
#

COMMONLIB=${IGOR_LIBDIR}/common/common.sh
[[ -e $COMMONLIB ]] && . $COMMONLIB

igor_highlight "Checking augeas lenses"
augtool "quit"

exit $?
