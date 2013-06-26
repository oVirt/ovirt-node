#!/bin/bash -x

#
# Verify that the network is configured correctly
# The intention is to verify the runtime informations (devices and addresses)
# And to not rely on configuration files
#

igor_highlight() { echo "== $1 ==" ; }
igor_debug() { echo "[D] $@" ; }
die() { echo "ERROR: $@" ; exit 1 ; }

COMMONLIB=${IGOR_LIBDIR}/common/common.sh
[[ -e $COMMONLIB ]] && . $COMMONLIB

igor_highlight "Verifying network setup" "="


source /etc/default/ovirt

if [[ -n $OVIRT_BOND_NAME ]];
then
    igor_highlight "Verify creation of configured bond devices"
    set -e

    igor_debug "Checking that '$OVIRT_BOND_NAME' is a bond device"
    test -e "/sys/class/net/$OVIRT_BOND_NAME/bonding/slaves"

    igor_debug "Checking that all slaves '$OVIRT_BOND_SLAVES' are members"
    [[ -z $OVIRT_BOND_SLAVES ]] && die "No bond slaves given"
    for slave in ${OVIRT_BOND_SLAVES/,/ };
    do
        igor_debug "Checking slave '$slave'"
        egrep -q "^$slave| $slave | $slave\$" \
                 /sys/class/net/$OVIRT_BOND_NAME/bonding/slaves
    done

    igor_debug "Checking that options '$OVIRT_BOND_OPTIONS' are used"
    for arg in $OVIRT_BOND_OPTIONS;
    do
        key=${arg%%=*};
        value=${arg##*=};
        fn="/sys/class/net/${OVIRT_BOND_NAME}/bonding/$key"
        igor_debug "Checking '$arg' is in '$fn'"
        real_value=$(cat $fn | cut -d" " -f1)
        if [[ $real_value != $value ]];
        then
            igor_debug "  Failed: '$real_value' != '$value'"
            exit 1
        fi
    done

    igor_debug "Bond link status:"
    ip link show $OVIRT_BOND_NAME
fi


if [[ -n $OVIRT_BOOTIF ]]
then
    igor_highlight "Checking bootif '$OVIRT_BOOTIF' configuration"
    if  [[ -z $OVIRT_NETWORK_LAYOUT || $OVIRT_NETWORK_LAYOUT == "direct" ]];
    then
        igor_highlight "Checking direct network layout"
        # FIXME how to?
    elif [[ -n $OVIRT_NETWORK_LAYOUT && $OVIRT_NETWORK_LAYOUT == "bridged" ]]
    then
        igor_highlight "Checking bridged network layout"
    else
        igor_highlight "Unknown network layout: $OVIRT_NETWORK_LAYOUT"
        exit 1
    fi

    if [[ -n $OVIRT_IP_ADDR ]];
    then
        igor_debug "Checking for static IP address"
        ip link show $OVIRT_BOOTIF
    elif [[ -n $OVIRT_BOOTPROTO && $OVIRT_BOOTPROTO == "dhcp" ]];
    then
        igor_debug "Checking for dhcp lease"
        # FIXME this assumes that this file exists ... and not done differnt
        ls /var/lib/dhclient/*${OVIRT_BOOTIF}.lease
    fi
fi
