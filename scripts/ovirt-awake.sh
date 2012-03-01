#!/bin/bash
#
# ovirt-awake - Notifies any management server that the node is starting.
#
# Copyright (C) 2008-2010 Red Hat, Inc.
# Written by Darryl L. Pierce <dpierce@redhat.com>
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

. /etc/init.d/functions
. /usr/libexec/ovirt-functions

NODE_CONFIG=/etc/sysconfig/node-config
VAR_SUBSYS_NODECONFIG=/var/lock/subsys/node-config



send_text () {
    local text=${1}

    echo "$text" 1>&3
}

receive_text () {
    read 0<&3
}

error () {
    local text=${1-}

    send_text "ERR: (ovirt-awake) ${text}"
    # log "${text}"
}

ovirt_startup () {
    local mgmthost=${OVIRT_MANAGEMENT_SERVER}
    local mgmtport=${OVIRT_MANAGEMENT_PORT}

    if [[ -z "${mgmthost}" ]] || [[ -z "${mgmtport}" ]]; then
        find_srv identify tcp
        mgmthost=$SRV_HOST
        mgmtport=$SRV_PORT
    fi

    if [[ -n "${mgmthost}" ]] && [[ -n "${mgmtport}" ]]; then
        # log "Notifying oVirt management server: ${mgmthost}:${mgmtport}"
        exec 3<>/dev/tcp/$mgmthost/$mgmtport

        receive_text
        if [ $REPLY == "HELLO?" ]; then
            log "Starting wakeup conversation."
            send_text "HELLO!"
            receive_text
            if [ $REPLY == "MODE?" ]; then
                send_text "AWAKEN"
                receive_text
                KEYTAB=$(echo $REPLY | awk '{ print $2 }')
                if [ -n "$KEYTAB" -a -n "$KEYTAB_FILE" ]; then
                    # log "Retrieving keytab: '$KEYTAB'"
                    wget -q "$KEYTAB" --no-check-certificate --output-document="$KEYTAB_FILE"
                else
                    log "No keytab to retrieve"
                fi
                send_text ACK
            else
                error "Did not get a mode request."
            fi
        else
            error "Did not get a proper startup marker."
        fi
        # log "Disconnecting."
        <&3-
    else
        # log "Missing server information. Failing..."
        return 1
    fi
}

# Override this method to provide support for notifying a management
# system that the node has started and will be available after
# system initialization
start_ovirt_awake () {
    local RC=0

    [ -f "$VAR_SUBSYS_NODECONFIG" ] && exit 0
    {
        touch $VAR_SUBSYS_NODECONFIG
        # log "Starting ovirt-awake."
        case "$OVIRT_RUNTIME_MODE" in
            "none")
                log "Node is operating in unmanaged mode."
                ;;
            "ovirt")
                log "Node is operating in ovirt mode."
                ovirt_startup
                RC=$?
                ;;
            "managed")
                if [ -x /config/$MANAGEMENT_SCRIPTS_DIR/awake ]; then
                    log "Executing /config/$MANAGEMENT_SCRIPTS_DIR/awake"
                    /config/$MANAGEMENT_SCRIPTS_DIR/awake
                else
                    echo "No script found to notify management server during awake state."
                fi
                ;;
        esac

        rm -f $VAR_SUBSYS_NODECONFIG
    
        log "Completed ovirt-awake: RETVAL=$RC"
    } >> $OVIRT_LOGFILE 2>&1
    
    return $RC
}

stop_ovirt_awake () {
    echo -n "Stopping ovirt-awake: "
    success
}

reload_ovirt_awake () {
    stop_ovirt_awake
    start_ovirt_awake
}

# When called with a parameter:
$@

