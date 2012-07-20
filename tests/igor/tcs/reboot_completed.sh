#!/bin/bash

# Confirm that the reboot has completed.

[ -e /tmp/reboot-requested ] && {
    echo "Reboot marker still exists."
    exit 1
}

exit 0
