#!/bin/bash
#
# ovirt-node-hooks.sh - Wrapps all functions needed by oVirt at boot time.
#
# Copyright (C) 2015 Red Hat, Inc.
# Written by Ryan Barry <rbarry@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.
#
VAR_SUBSYS_OVIRT_HOOKS=/var/lock/subsys/ovirt-node-hooks
HOOK_DIR=/usr/libexec/ovirt-node/hooks
OVIRT_HOOKLOG=/var/log/ovirt-hooks.log

trigger () {
    echo "Called with $1"
    {
        echo "Starting ovirt-node-hooks service for $1"

        # Run on-boot hooks
        echo "Looking at $HOOK_DIR/$1"
        if [[ -d "$HOOK_DIR/$1" ]] && [[ "$(ls -A $HOOK_DIR/$1)" ]];
        then
            for handler in "$HOOK_DIR/$1"/*;
            do
                echo "Running handler: $handler"
                "$handler" >> $OVIRT_HOOKLOG 2>&1
            done
        fi

        echo "Completed ovirt-node-hooks"
    } >> $OVIRT_HOOKLOG 2>&1
}

case "$1" in
    "trigger")
        trigger "$2"
        ;;
    *)
        echo "Please call with trigger [hook]"
        ;;

esac
