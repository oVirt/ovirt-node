#!/bin/bash
#
# ovirt-init-functions.sh - Wrapps all functions needed by oVirt at boot time.
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

. /usr/libexec/ovirt-boot-functions

NODE_CONFIG=/etc/sysconfig/node-config

VAR_SUBSYS_OVIRT_EARLY=/var/lock/subsys/ovirt-early
VAR_SUBSYS_NODECONFIG=/var/lock/subsys/node-config
VAR_SUBSYS_OVIRT_POST=/var/lock/subsys/ovirt-post
VAR_SUBSYS_OVIRT_CIM=/var/lock/subsys/ovirt-cim

BONDING_MODCONF_FILE=/etc/modprobe.d/bonding
AUGTOOL_CONFIG=/var/tmp/augtool-config
EARLY_DIR=/etc/ovirt-early.d

#
# ovirt-early
#

get_mac_addresses() {
    local DEVICE=$1

    macs=""
    devices=$(ls -b /sys/class/net/)
    for device in $devices; do
        if [ "$device" != "$DEVICE" ]; then
            mac=$(cat /sys/class/net/$device/address 2>/dev/null)
            if [ -n "$mac" -a "$mac" != "00:00:00:00:00:00" ]; then
                macs="${macs}${mac}=${device},"
            fi
        fi
    done
}

configure_ovirt_management_nic() {
    DEVICE=$1

    if [ -n "$DEVICE" ]; then
        log "Configuring network"
        if ! network_up ; then
            log "Using interface $DEVICE"
            # setup temporary interface to retrieve configuration
            /sbin/dhclient -1 $1 \
             && [ -f /var/run/dhclient.pid ] \
             && kill $(cat /var/run/dhclient.pid)
        fi
        if [ $? -eq 0 ]; then
            # from network-scripts/ifup-post
            IPADDR=$(LC_ALL=C ip -o -4 addr ls dev ${DEVICE} | awk '{ print $4 ; exit }')
            log "Interface brought up with $IPADDR"
            eval $(ipcalc --silent --hostname ${IPADDR} ; echo "status=$?")
            if [ "$status" = "0" ]; then
                hostname $HOSTNAME
                log "Hostname resolved to $HOSTNAME"
                # retrieve remote config
                find_srv ovirt tcp
                if [ -n "$SRV_HOST" -a -n "$SRV_PORT" ]; then
                    log "oVirt Server found at: $SRV_HOST:$SRV_PORT"
                    cfgdb=$(mktemp)
                    get_mac_addresses $DEVICE
                    log "MACs to use: $macs"
                    wget -O $cfgdb --no-check-certificate \
                      "http://$SRV_HOST:$SRV_PORT/ovirt/managed_node/config?host=$(hostname)&macs=$macs"
                    if [ $? -eq 0 ]; then
                        log "Remote configuration bundle retrieved to $cfgdb"
                        /usr/libexec/ovirt-process-config $cfgdb $BONDING_MODCONF_FILE $AUGTOOL_CONFIG
                        if [ $? -eq 0 ]; then
                            log "Remote configuration retrieved and applied"
                            rm $cfgdb
                        else
                            log "Failure to retrieve or apply remote configuration"
                        fi
                    else
                        log "Failed to retrieve configuration bundle"
                    fi
                fi
            fi
        fi
    else
        # for non-PXE boot when BOOTIF parameter is not specified
        # otherwise default network config is invalid
        DEVICE=eth0
    fi
    # default oVirt network configuration:
    # bridge each ethernet device in the system
    BRIDGE=br$DEVICE
    local ifcfg=/etc/sysconfig/network-scripts/ifcfg-$BRIDGE

    # only write a default file if one does not exist
    if [ ! -f $ifcfg ]; then
        log "Applying default configuration to $DEVICE and $BRIDGE"
        printf '%s\n' "DEVICE=$DEVICE" ONBOOT=yes "BRIDGE=$BRIDGE" \
            > /etc/sysconfig/network-scripts/ifcfg-$DEVICE
        printf '%s\n' "DEVICE=$BRIDGE" "BOOTPROTO=dhcp" \
            ONBOOT=yes TYPE=Bridge PEERNTP=yes DELAY=0 \
            > /etc/sysconfig/network-scripts/ifcfg-$BRIDGE
        log "Default config applied"
    fi

    service network restart

}

configure_management_interface() {
    log "Configuring the manangement interface."
    case $OVIRT_RUNTIME_MODE in
        "ovirt")
            configure_ovirt_management_nic $bootif
            if [ -n "$init" ]; then
                /usr/libexec/ovirt-config-storage AUTO
                # initial configuration storage, after /config creation
                ovirt_store_config \
                    /etc/sysconfig/network-scripts/ifcfg-* \
                    $BONDING_MODCONF_FILE
                if [ $upgrade = 1 ]; then
                    # local disk installation for managed mode
                    mount_live
                    /usr/libexec/ovirt-config-boot /live "$bootparams"
                fi
            fi
            ;;
        "managed")
            if [ -x $MANAGEMENT_SCRIPTS_DIR/configure-management-interface ]; then
                log "Executing $MANAGEMENT_SCRIPTS_DIR/configure-management-interface"
                $MANAGEMENT_SCRIPTS_DIR/configure-management-interface
            else
                echo "No script to configure management interface found."
            fi
            ;;
        "none")
            log "Unmanaged node: no management interface to configure."
    esac
}

start_ovirt_early () {
    [ -f "$VAR_SUBSYS_NODECONFIG" ] && exit 0
    {
        # FIXME Hack around rhbz#806349 and which might be because of rhbz#807203
        mount -a
        log "Starting ovirt-early"
        _start_ovirt_early
        RETVAL=$?
        # TEMP fix broken libvirtd.conf
        sed -c -i '/^log_filters=/d' /etc/libvirt/libvirtd.conf
        log "Completed ovirt-early"
    } >> $OVIRT_LOGFILE 2>&1
    return $RETVAL
}

_start_ovirt_early () {
    touch $VAR_SUBSYS_OVIRT_EARLY
    # oVirt boot parameters
    #   BOOTIF=link|eth*|<MAC> (appended by pxelinux)
    #   storage_init=[usb|scsi[:serial#]|/dev/...]
    #   storage_vol=BOOT_MB:SWAP_MB:ROOT_MB:CONFIG_MB:LOGGING_MB:DATA_MB
    #   mem_overcommit=<overcommit_ratio>
    #   upgrade
    #   standalone
    #   firstboot
    #   ovirt_runtime_mode
    #   rescue
    #   pxelinux format: ip=<client-ip>:<boot-server-ip>:<gw-ip>:<netmask>
    #   anaconda format: ip=<client-ip> netmask=<netmask> gateway=<gw-ip>
    #   or               ip=dhcp|off
    #   ipv6=dhcp|auto
    #   dns=server[,server]
    #   ntp=server[,server]
    #   vlan=id
    #   ssh_pwauth=[0|1]
    #   syslog=server[:port]
    #   collectd=server[:port]
    #   hostname=fqdn
    #   TBD logrotate maxsize
    #   rhn_type=[classic|sam]
    #   rhn_url=SATELLITE_URL
    #   rhn_CA_CERT=CA_CERT_URL
    #   rhn_username=RHN-USERNAME
    #   rhn_password=RHN-PASSWORD
    #   rhn_profile=RHNPROFILE
    #   rhn_activationkey=ACTIVATIONKEY
    # RHN registration, activation key takes precedence
    #   rhn_proxy=PROXY-HOST:PORT
    #   rhn_proxyuser=PROXY-USERNAME
    #   rhn_proxypassword=PROXY-PASSWORD
    #   snmp_password=<authpassphrase>

    #   BOOTIF=link|eth*|<MAC> (appended by pxelinux)
    # network boot interface is assumed to be on management network where
    # management server is reachable
    # BOOTIF=<MAC> e.g. BOOTIF=01-00-16-3e-12-34-57
    # PXELINUX option IPAPPEND 2 in pxelinux.cfg appends MAC address
    # of the booting node
    # BOOTIF=link - take first eth for which ethtool reports link
    # BOOTIF=eth* e.g. BOOTIF=eth0 - use given interface
    bootif=

    #   ovirt_init=HOSTVGDISK1[,HOSTVGDISK2...][;APPVGDISK1[,APPVGDISK2...]]
    #   where DISK=[ata|cciss|scsi|usb[:serial#]|/dev/...]
    # local installation target disks
    # Allow specification of multiple disks per VG
    # usb|scsi - select disk type, as reported by udev ID_BUS
    # serial# - select exact disk using serial number, as reported by
    #           udev ID_SERIAL
    # e.g. ovirt_init=usb:Generic_STORAGE_DEVICE_0000145418-0:0
    # /dev/... - use specified disk device
    #            (for cases when HAL doesn't handle it)
    # w/o value - grab the first disk (/dev/?da)
    init=
    init_app=

    #   storage_vol=:SWAP_MB::CONFIG_MB:LOGGING_MB:DATA_MB:SWAP2_MB:DATA2_MB
    #   or
    #   storage_vol=size[,{Swap|Data|Config|Logging|Data2|Swap2}][:size...]
    # local partition sizes in MB
    # LVs ending in 2 go to AppVG, all the others fall into HostVG
    vol_boot_size=
    vol_swap_size=
    vol_root_size=
    vol_config_size=
    vol_logging_size=
    # data size can be set to 0 to disable data partition, -1 to use
    # remaining free space after the other above partitions are defined
    # or a specific positive number in MB
    vol_data_size=

    # swap2 and data2 will be placed into AppVG, 0 disables, data2
    # can be -1 or a positive number in MB for each
    vol_swap2_size=
    vol_data2_size=

    #   swap_encrypt={Swap|Swap2},cypher1[:cypher2...][;{Swap|Swap2}...]
    # request swap encryption
    # the default cypher is set to aes-cbc-essiv:sha256
    crypt_swap=
    crypt_swap2=

    #   upgrade
    # install/update oVirt Node image on the local installation target disk
    upgrade=

    #   mem_overcommit=<overcommit_ratio>
    # set the swap size coefficient
    overcommit=

    #   standalone
    # force oVirt Node standalone mode
    standalone=1

    #   firstboot
    # force firstboot configuration even if it has already been run
    # in auto-install mode, overwrite the disk chosen by storage_init parameter
    firstboot=

    # wipe_fakeraid
    # force the wiping of fakeraid metadata when auto-installing
    # otherwise, the auto-install will fail
    wipe_fakeraid=

    #   ovirt_runtime_mode
    # overrides the runtime mode defined in /etc/sysconfig/node-config
    runtime_mode=

    # ovirt_stateless
    stateless=

    #   rescue
    # enter emergency shell for fixing configuration issues
    rescue=

    #   rootpw=<encrypted_password>
    # sets a temporary root password, change is forced on first login
    # password is crypted, same as Kickstart option rootpw --iscrypted
    # WARNING: use for debugging only, this is not secure!
    rootpw=

    #   adminpw=<encrypted_password>
    # sets a temporary password for admin, change is forced on first login
    # password is crypted, same as Kickstart option rootpw --iscrypted
    # WARNING: use for debugging only, this is not secure!
    adminpw=

    #   snmp_password=<authpassphrase>
    # enable snmpd and set password for "root" SNMPv3 USM user
    snmp_password=

    # CIM related options
    # cim_enabled=0|1
    # cim_passwd=<encrypted password>
    cim_passwd=
    cim_enabled=

    #   pxelinux format: ip=<client-ip>:<boot-server-ip>:<gw-ip>:<netmask>
    #   anaconda format: ip=<client-ip> netmask=<netmask> gateway=<gw-ip>
    #   or               ip=dhcp|off
    #   ipv6=dhcp|auto
    #   dns=server[,server]
    #   ntp=server[,server]
    #   vlan=id
    #   ssh_pwauth=[0|1]
    # static network configuration
    ip_address=
    ip_gateway=
    ip_netmask=
    vlan=
    netmask=
    gateway=
    ipv6=
    dns=
    ntp=
    ssh_pwauth=
    uninstall=

    # hostname=fqdn
    # hostname
    hostname=

    #   syslog=server[:port]
    # default syslog server
    syslog_server=
    syslog_port=

    #   collectd=server[:port]
    # default collectd server
    collectd_server=
    collectd_port=

    #   rhn_type=[classic|sam]
    #           default is classic
    #   rhn_url=SATELLITE_URL
    #   rhn_CA_CERT=CA_CERT_URL
    #   rhn_username=RHN-USERNAME
    #   rhn_password=RHN-PASSWORD
    #   rhn_profile=RHNPROFILE
    #   rhn_activationkey=ACTIVATIONKEY
    # RHN registration, activation key takes precedence
    #   rhn_proxy=PROXY-HOST:PORT
    #   rhn_proxyuser=PROXY-USERNAME
    #   rhn_proxypassword=PROXY-PASSWORD
    rhn_type=classic
    rhn_url=
    rhn_ca_cert=
    rhn_username=
    rhn_password=
    rhn_profile=
    rhn_activationkey=
    rhn_proxy=
    rhn_proxyuser=
    rhn_proxypassword=

    # save boot parameters like console= for local disk boot menu
    bootparams=
    cat /etc/system-release >> $OVIRT_LOGFILE
    # determine iscsi_install status
    if grep -q iscsi_install /proc/cmdline; then
        iscsi_install=0
    else
        iscsi_install=1
    fi

    for i in $(cat /proc/cmdline); do
        case $i in
            uninstall*)
                uninstall='yes'
                ;;
            BOOTIF=*)
            i=${i#BOOTIF=}
            case "$i" in
                eth*)
                bootif=$i
                ;;
                link)
                for eth in $(cd /sys/class/net; echo eth*); do
                    if ethtool $eth 2>/dev/null|grep -q "Link detected: yes"
                    then
                        bootif=$eth
                        break
                    fi
                done
                ;;
                ??-??-??-??-??-??-??)
                i=${i#??-}
                bootif=$(grep -il $(echo $i|sed 's/-/:/g') /sys/class/net/eth*/address|rev|cut -d/ -f2|rev)
                ;;
            esac
            ;;
            storage_init* | ovirt_init*)
            i=${i#ovirt_init}
            i=${i#storage_init}
            if [ -z "$i" ]; then
                # 'storage_init' without value: grab first disk
                init=$(ls -1 /dev/?da /dev/cciss/c?d? 2>/dev/null |head -n1)
            else
                i=${i#=}
                eval $(printf $i|awk -F\; '{ print "hostvgdisks="$1; print "appvgdisks="$2; }')
                # Look into HostVG disks
                if [ -n "$hostvgdisks" ]; then
                    oldIFS="$IFS"
                    IFS=,
                    init=
                    for d in $hostvgdisks; do
                        did="$(IFS="$oldIFS" parse_disk_id "$d")"
                        if [ -z "$did" -a $iscsi_install == 1 ]; then
                            autoinstall_failed
                        fi
                        if [ -n "$init" ]; then
                            init="$init${SEP}$did"
                        else
                            init="$did"
                        fi
                    done
                    IFS="$oldIFS"
                fi
                # Look into AppVG disks
                if [ -n "$appvgdisks" ]; then
                    oldIFS="$IFS"
                    IFS=,
                    init_app=
                    for d in $appvgdisks; do
                        did="$(IFS="$oldIFS" parse_disk_id "$d")"
                        if [ -z "$did" ]; then
                            autoinstall_failed
                        fi
                        if [ -n "$init_app" ]; then
                            init_app="$init_app${SEP}$did"
                        else
                            init_app="$did"
                        fi
                    done
                    IFS="$oldIFS"
                fi
            fi
            if [ -z "$init" -a $iscsi_install == 1 ]; then
                log "Selected disk $i is not valid."
            fi
            ;;
            storage_vol* | ovirt_vol=*)
            i=${i#ovirt_vol=}
            i=${i#storage_vol=}
            eval $(printf $i|awk -F: '{ print "lv1="$1; print "lv2="$2; print "lv3="$3; print "lv4="$4; print "lv5="$5; print "lv6="$6; print "lv7="$7; print "lv8="$8; }')
            # Reads each provided LV size and assign them
            # NOTE: Boot and Root size are ignored by o-c-storage
            for p in $(seq 1 8); do
                var=lv$p
                size=
                lv=
                if [ -n "${!var}" ]; then
                    eval $(printf '${!var}'|awk -F, '{ print "size="$1; print "lv="$2; }')
                    if [ -n "${size}" ]; then
                        case "${lv}" in
                            Boot)
                            vol_boot_size=$size
                            ;;
                            Swap)
                            vol_swap_size=$size
                            ;;
                            Root)
                            vol_root_size=$size
                            ;;
                            Config)
                            vol_config_size=$size
                            ;;
                            Logging)
                            vol_logging_size=$size
                            ;;
                            Data)
                            vol_data_size=$size
                            ;;
                            Swap2)
                            vol_swap2_size=$size
                            ;;
                            Data2)
                            vol_data2_size=$size
                            ;;
                            *)
                            ## This is here to preserve old styled syntax (in order)
                            ## BOOT_MB:SWAP_MB:ROOT_MB:CONFIG_MB:LOGGING_MB:DATA_MB:SWAP2_MB:DATA2_MB
                            case "$p" in
                                1)
                                vol_boot_size=$size
                                ;;
                                2)
                                vol_swap_size=$size
                                ;;
                                3)
                                vol_root_size=$size
                                ;;
                                4)
                                vol_config_size=$size
                                ;;
                                5)
                                vol_logging_size=$size
                                ;;
                                6)
                                vol_data_size=$size
                                ;;
                                7)
                                vol_swap2_size=$size
                                ;;
                                8)
                                vol_data2_size=$size
                                ;;
                            esac
                            ;;
                        esac
                    fi
                fi
            done
            ;;
            upgrade* | ovirt_upgrade* | local_boot | local_boot=* | ovirt_local_boot*)
            upgrade=1
            if ! grep -q admin /etc/passwd; then
                unmount_config /etc/passwd /etc/shadow
                useradd -g admin -s /usr/libexec/ovirt-admin-shell admin
                [ ! grep -q ^%wheel /etc/sudoers ] && echo "%wheel	ALL=(ALL)	NOPASSWD: ALL" >> /etc/sudoers
                /usr/sbin/usermod -p $(grep ^root /etc/shadow | sed 's/:/ /g' | awk '{print $2}') admin
                persist /etc/shadow /etc/passwd
            fi
            if ! grep -q ^cim /etc/passwd; then
                unmount_config /etc/passwd /etc/shadow
                useradd -g cim -s /usr/libexec/ovirt-admin-shell cim
                persist /etc/shadow /etc/passwd
            fi
            ;;
            standalone=no | standalone=0 | ovirt_standalone=no | ovirt_standalone=0)
            standalone=0
            bootparams="$bootparams $i"
            ;;
            standalone* | ovirt_standalone*)
            standalone=1
            bootparams="$bootparams $i"
            ;;
            firstboot=no | firstboot=0 | ovirt_firstboot=no | ovirt_firstboot=0 | reinstall=0 | reinstall=no)
            firstboot=0
            ;;
            firstboot* | ovirt_firstboot* | reinstall)
            firstboot=1
            ;;
            wipe_fakeraid=no | wipe_fakeraid=0 )
            wipe_fakeraid=0
            ;;
            wipe_fakeraid*)
            wipe_fakeraid=1
            ;;
            stateless=no | stateless=0 | ovirt_stateless=no | ovirt_stateless=0)
            stateless=0
            ;;
            stateless* | ovirt_stateless* | stateless)
            stateless=1
            ;;
            install*)
            install=1
            ;;
            runtime_mode*)
            runtime_mode=${i#runtime_mode=}
            ;;
            rescue)
            rescue=1
            ;;
            adminpw=*)
            adminpw=${i#adminpw=}
            ;;
            rootpw=*)
            rootpw=${i#rootpw=}
            if [ -z "$adminpw" ]; then
                adminpw=$rootpw
            fi
            ;;
            cim_passwd=*)
            cim_passwd=${i#cim_passwd=}
            ;;
            cim_enabled=0 | cim_enabled=no)
            cim_enabled=0
            ;;
            enable_cim* | enable_cim | cim_enabled* | cim_enabled)
            cim_enabled=1
            ;;
            snmp_password=*)
            snmp_password=${i#snmp_password=}
            ;;

            mem_overcommit* | ovirt_overcommit*)
            i=${i#mem_overcommit=}
            i=${i#ovirt_overcommit=}
            eval $(printf $i|awk -F: '{print "overcommit="$1;}')
            ;;

            ip=*)
            i=${i#ip=}
            if [ "$i" = "dhcp" ]; then
                ip_address=
            else
                eval $(printf $i|awk -F: '{print "ip_address="$1; print "ip_gateway="$3; print "ip_netmask="$4}')
            fi
            ;;
            netmask=*)
            netmask=${i#netmask=}
            ;;
            gateway=*)
            gateway=${i#gateway=}
            ;;
            ipv6=*)
            ipv6=${i#ipv6=}
            ;;
            dns=*)
            dns=${i#dns=}
            ;;
            ntp=*)
            ntp=${i#ntp=}
            ;;
            hostname=*)
            hostname=${i#hostname=}
            ;;
            vlan=*)
            vlan=${i#vlan=}
            ;;
            ssh_pwauth=1 | ssh_pwauth=true)
            ssh_pwauth=yes
            ;;
            ssh_pwauth=0 | ssh_pwauth=false)
            ssh_pwauth=no
            ;;
            syslog=*)
            i=${i#syslog=}
            eval $(printf $i|awk -F: '{print "syslog_server="$1; print "syslog_port="$2;}')
            ;;
            netconsole=*)
            i=${i#netconsole=}
            eval $(printf $i|awk -F: '{print "netconsole_server="$1; print "netconsole_port="$2;}')
            ;;
            collectd=*)
            i=${i#collectd=}
            eval $(printf $i|awk -F: '{print "collectd_server="$1; print "collectd_port="$2;}')
            ;;
            rhn_type=*)
            rhn_type=${i#rhn_type=}
            ;;
            rhn_url=*)
            rhn_url=${i#rhn_url=}
            ;;
            rhn_ca_cert=*)
            rhn_ca_cert=${i#rhn_ca_cert=}
            ;;
            rhn_username=*)
            rhn_username=${i#rhn_username=}
            ;;
            rhn_password=*)
            rhn_password=${i#rhn_password=}
            ;;
            rhn_profile=*)
            rhn_profile=${i#rhn_profile=}
            ;;
            rhn_activationkey=*)
            rhn_activationkey=${i#rhn_activationkey=}
            ;;
            rhn_proxy=*)
            rhn_proxy=${i#rhn_proxy=}
            ;;
            rhn_proxyuser=*)
            rhn_proxyuser=${i#rhn_proxyuser=}
            ;;
            rhn_proxypassword=*)
            rhn_proxypassword=${i#rhn_proxypassword=}
            ;;
            ovirt_early=*)
            bootparams="$bootparams $i"
            i=${i#ovirt_early=}
            ovirt_early=$(echo $i|tr ",:;" " ")
            ;;
            # Don't store these parameters in /etc/default/ovirt
            BOOT_IMAGE=* | initrd=* | check | linux | liveimg | \
            root=* | rootfstype=* | rootflags=* | ro | single | install)
            ;;
            crashkernel=*)
            bootparams="$bootparams $i"
            ;;
            kdump_nfs=*)
            kdump_nfs=${i#kdump_nfs=}
            ;;
            iscsi_name=*)
            iscsi_name=${i#iscsi_name=}
            ;;
            iscsi_init=*)
            iscsi_init=${i#iscsi_init=}
            ;;
            iscsi_server=*)
            i=${i#iscsi_server=}
            eval $(printf $i|awk -F: '{print "iscsi_target_host="$1; print "iscsi_target_port="$2;}')
            ;;
            iscsi_target_name=*)
            iscsi_target_name=${i#iscsi_target_name=}
            ;;
            iscsi_install*)
            iscsi_install="Y"
            ;;
            swap_encrypt=* | ovirt_swap_encrypt=* )
            i=${i#ovirt_swap_encrypt=}
            i=${i#swap_encrypt=}
            eval $(printf $i|awk -F\; '{ print "swap1="$1; print "swap2="$2; }')
            for p in 1 2; do
                var=swap$p
                swapdev=
                swapcyph=
                local default_cypher="aes-cbc-essiv:sha256"
                if [ -n "${!var}" ]; then
                    eval $(printf ${!var} |awk -F, '{ print "swapdev="$1; print "swapcyph="$2; }')
                    if [ "${swapdev}" = "Swap" ]; then
                        if [ -n "${swapcyph}" ]; then
                            crypt_swap=${swapcyph}
                        else
                            crypt_swap=${default_cypher}
                        fi
                    elif [ "${swapdev}" = "Swap2" ]; then
                        if [ -n "${swapcyph}" ]; then
                            crypt_swap2=${swapcyph}
                        else
                            crypt_swap2=${default_cypher}
                        fi
                    fi
                fi
            done
            ;;
            *)
            # check the params to be ignored before adding to bootparams
            varname=${i%=*}
            if ! grep -qw $varname /etc/ovirt-commandline.d/* 2>/dev/null; then
                bootparams="$bootparams $i"
            fi
            ;;
        esac
    done

    for hook in $ovirt_early; do
        pre="$EARLY_DIR/pre-$hook"
        if [ -e "$pre" ]; then
            . "$pre"
        fi
    done

    if [ -z "$ip_netmask" ]; then
        ip_netmask=$netmask
    fi
    if [ -z "$ip_gateway" ]; then
        ip_gateway=$gateway
    fi
    # Handle uninstall arg
    # need to wipe mbr if passed
    if [ "$uninstall" = "yes" ]; then
        oldIFS=$IFS
        log "Found uninstall arg, wiping mbr from init disks"
        IFS=$SEP
        for init_disk in $init $init_app $(get_boot_device); do
            echo "Wiping $init_disk"
            wipe_mbr "$init_disk"
        done
        IFS=$oldIFS
        log "Uninstall complete, rebooting"
        /sbin/reboot
    fi


    # save boot parameters as defaults for ovirt-config-*
    params="bootif init init_app vol_boot_size vol_swap_size vol_root_size vol_config_size vol_logging_size vol_data_size vol_swap2_size vol_data2_size crypt_swap crypt_swap2 upgrade standalone overcommit ip_address ip_netmask ip_gateway ipv6 dns ntp vlan ssh_pwauth syslog_server syslog_port collectd_server collectd_port bootparams hostname firstboot rhn_type rhn_url rhn_ca_cert rhn_username rhn_password rhn_profile rhn_activationkey rhn_proxy rhn_proxyuser rhn_proxypassword runtime_mode kdump_nfs iscsi_name snmp_password install netconsole_server netconsole_port stateless cim_enabled wipe_fakeraid iscsi_init iscsi_target_name iscsi_target_host iscsi_target_port iscsi_install"
    # mount /config unless firstboot is forced
    if [ "$firstboot" != "1" ]; then
        mount_config
    fi
    log "Updating $OVIRT_DEFAULTS"
    tmpaug=$(mktemp)
    for p in $params; do
        PARAM=$(uc $p)
        value=$(ptr $p)
        if [ -n "$value" -o $p = 'init' -o $p = 'bootif' -o $p = 'upgrade' -o $p = 'install' ]; then
            log "Updating OVIRT_$PARAM to '$value'"
            echo "set /files$OVIRT_DEFAULTS/OVIRT_$PARAM '\"$value\"'" \
                >> $tmpaug
        fi
    done
    augtool $tmpaug
    . $OVIRT_DEFAULTS
    if [ "$firstboot" != "1" -a -f /etc/ovirt-crypttab ]; then
        mount_crypt_swap
    fi
    if [ -f /etc/sysconfig/network ]; then
        . /etc/sysconfig/network
        if [ -n "$HOSTNAME" ]; then
            hostname $HOSTNAME
        fi
    fi

    if [ -n "$cim_passwd" ]; then
        log "Setting temporary admin password: $cim_passwd"
        unmount_config /etc/passwd /etc/shadow
        /usr/sbin/usermod -p "$cim_passwd" cim
    fi
    if [ -n "$adminpw" ]; then
        log "Setting temporary admin password: $adminpw"
        unmount_config /etc/passwd /etc/shadow
        /usr/sbin/usermod -p "$adminpw" admin
        chage -d 0 admin
    fi
    if [ -n "$rootpw" ]; then
        log "Setting temporary root password: $rootpw"
        unmount_config /etc/passwd /etc/shadow
        /usr/sbin/usermod -p "$rootpw" root
        chage -d 0 root
    fi
    # check if root or admin password is expired, this might be upon reboot
    # in case of automated installed with rootpw or adminpw parameter!
    if LC_ALL=C chage -l root | grep  -q "password must be changed" \
        || LC_ALL=c chage -l admin | grep -q "password must be changed"; then
        unmount_config /etc/passwd /etc/shadow
        # PAM will force password change at first login
        # so make sure we persist it after a successful login
        cat >> /etc/profile << EOF
# added by ovirt-early
if [ "$USER" = "root" -o "$USER" = "admin" ]; then
    sudo persist /etc/passwd /etc/shadow
    if LC_ALL=C sudo chage -l root | grep  -q "password must be changed" \
        || LC_ALL=C sudo chage -l admin | grep -q "password must be changed"; then
        sudo /usr/libexec/ovirt-functions unmount_config /etc/passwd /etc/shadow
    fi
fi
EOF
    fi

    if [ "$rescue" = 1 ]; then
        log "Rescue mode requested, starting emergency shell"
        stop_log
        plymouth --hide-splash
        bash < /dev/console > /dev/console 2> /dev/console
        plymouth --show-splash
        start_log
    fi

    # link to the kernel image for kdump
    chcon -t boot_t /boot-kdump
    if is_booted_from_local_disk; then
        mount_boot
        if [ -f /dev/.initramfs/live/backup-vmlinuz ]; then
            # try backup image
            cp -p /dev/.initramfs/live/backup-vmlinuz0 /boot-kdump/vmlinuz-$(uname -r)
        else
            cp -p /dev/.initramfs/live/vmlinuz0 /boot-kdump/vmlinuz-$(uname -r)
        fi
    else
        # try source image
        mount_live
        if [ -e /live/*linux/vmlinuz0 ]; then
            cp -p /live/*linux/vmlinuz0 /boot-kdump/vmlinuz-$(uname -r)
        fi
    fi

    if [ "$standalone" = 1 ]; then
        log "Skip runtime mode configuration."
    else
        configure_management_interface
    fi

    rm -f $VAR_SUBSYS_OVIRT_EARLY

    for hook in $ovirt_early; do
        post="$EARLY_DIR/post-$hook"
        if [ -e "$post" ]; then
            . "$post"
        fi
    done

    return 0
}

stop_ovirt_early () {
    echo -n "Stopping ovirt-early: "
    success
}

reload_ovirt_early () {
    stop_ovirt_early
    start_ovirt_early
}

#
# ovirt-awake
#

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
        log "Starting ovirt-awake."
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

#
# ovirt-firstboot
#
VAR_SUBSYS_OVIRT_FIRSTBOOT=/var/lock/subsys/ovirt-firstboot

trap '__st=$?; stop_log; exit $__st' 0
trap 'exit $?' 1 2 13 15

check_version(){
    if [ -e "/dev/HostVG/Root" ]; then
    log "                                          "
    log "   Major version upgrades are not allowed."
    log "   Please uninstall existing version and reinstall."
    log "   Press Enter to drop to emergency shell."
    read < /dev/console
    bash < /dev/console
    fi
}

start_ovirt_firstboot ()
{
    if is_managed; then
        exit 0
    fi

    if ! is_firstboot && ! is_auto_install && ! is_upgrade && ! is_install && ! is_stateless; then
        return
    fi

    touch $VAR_SUBSYS_OVIRT_FIRSTBOOT
    /sbin/restorecon -e /var/lib/stateless/writable -e /data -e /config -e /proc -e /sys -rv / >> $OVIRT_TMP_LOGFILE 2>&1

    # Hide kernel messages on the console
    dmesg -n 1

    is_stateless
    stateless=$?

    is_auto_install
    auto_install=$?
    if [ "$auto_install" = "0" -o "$stateless" = "0" ]; then
        /usr/libexec/ovirt-auto-install
        rc=$?
        # Handle Log file
        if [ -f $OVIRT_TMP_LOGFILE ]; then
            cat $OVIRT_TMP_LOGFILE >> $OVIRT_LOGFILE
            rm -f $OVIRT_TMP_LOGFILE
        fi
        if [ $rc -ne 0 ]; then
            autoinstall_failed
        fi
    elif [ "$auto_install" = "2" ]; then
        echo "Device specified in storage_init does not exist"
        autoinstall_failed
    fi

    if is_stateless; then
        return 0
    fi

    if is_auto_install || is_upgrade; then
        plymouth --hide-splash
        mount_live
        check_version
        # auto install covers this already
        if ! is_auto_install; then
            /usr/libexec/ovirt-config-boot /live "$OVIRT_BOOTPARAMS" no
        fi
        if [ $? -ne 0 ]; then
            autoinstall_failed
        fi
        disable_firstboot
        ovirt_store_firstboot_config || autoinstall_failed
        reboot
        if [ $? -ne 0 ]; then
            autoinstall_failed
        fi
        return 1
    fi

    if is_firstboot || is_install ; then
        plymouth --hide-splash

        export LVM_SUPPRESS_FD_WARNINGS=0
        /usr/libexec/ovirt-config-installer -x < /dev/console

        plymouth --show-splash
    fi
    disable_firstboot

    ovirt_store_firstboot_config >> $OVIRT_LOGFILE 2>&1

    rm -f $VAR_SUBSYS_OVIRT_FIRSTBOOT
}

stop_ovirt_firstboot () {
    return 0
}

reload_ovirt_firstboot () {
    stop_ovirt_firstboot
    start_ovirt_firstboot
}

#
# ovirt
#
VAR_SUBSYS_OVIRT=/var/lock/subsys/ovirt

ovirt_start() {
    if is_standalone; then
        return 0
    fi
    find_srv ipa tcp
    if [ -n "$SRV_HOST" -a -n "$SRV_PORT" ]; then
        krb5_conf=/etc/krb5.conf
        # FIXME this is IPA specific
        wget -q --no-check-certificate \
            http://$SRV_HOST:$SRV_PORT/ipa/config/krb5.ini -O $krb5_conf.tmp
        if [ $? -ne 0 ]; then
            log "Failed to get $krb5_conf"; return 1
        fi
        mv $krb5_conf.tmp $krb5_conf
    else
        log "skipping Kerberos configuration"
    fi


    find_srv collectd udp
    if [ -n "$SRV_HOST" -a -n "$SRV_PORT" ]; then
        collectd_conf=/etc/collectd.conf
        if [ -f $collectd_conf.in ]; then
            sed -e "s/@COLLECTD_SERVER@/$SRV_HOST/" \
                -e "s/@COLLECTD_PORT@/$SRV_PORT/" \
                -e "/<Plugin rrdtool>/,/<\/Plugin>/d" $collectd_conf.in \
                > $collectd_conf
            if [ $? -ne 0 ]; then
                log "Failed to write $collectd_conf"; return 1
            fi
        fi
    else
        log "skipping collectd configuration, collectd service not available"
    fi

    find_srv qpidd tcp
    if [ -n "$SRV_HOST" -a -n "$SRV_PORT" ]; then
        libvirt_qpid_conf=/etc/sysconfig/libvirt-qpid
        if [ -f $libvirt_qpid_conf ]; then
            echo "LIBVIRT_QPID_ARGS=\"--broker $SRV_HOST --port $SRV_PORT\"" >> $libvirt_qpid_conf
            echo "/usr/kerberos/bin/kinit -k -t /etc/libvirt/krb5.tab qpidd/`hostname`" >> $libvirt_qpid_conf
        fi
        matahari_conf=/etc/sysconfig/matahari
        if [ -f $matahari_conf ]; then
            echo "MATAHARI_ARGS=\"--broker $SRV_HOST --port $SRV_PORT\"" >> $matahari_conf
            echo "/usr/kerberos/bin/kinit -k -t /etc/libvirt/krb5.tab qpidd/`hostname`" >> $matahari_conf
        fi
    else
        log "skipping libvirt-qpid and matahari configuration, could not find $libvirt_qpid_conf"
    fi
}

start_ovirt () {
    [ -f "$VAR_SUBSYS_OVIRT" ] && exit 0
    {
        log "Starting ovirt"
        touch $VAR_SUBSYS_OVIRT
        case $OVIRT_RUNTIME_MODE in
            "ovirt")
                ovirt_start
                ;;
            "managed")
                if [ -x $MANAGEMENT_SCRIPTS_DIR/ready ]; then
                    log "Executing $MANAGEMENT_SCRIPTS_DIR/ready."
                    $MANAGEMENT_SCRIPTS_DIR/ready
                    RC=$?
                else
                    log "No script to perform node activation."
                fi
        esac
        rm -f $VAR_SUBSYS_OVIRT
        log "Completed ovirt"
    } >> $OVIRT_LOGFILE 2>&1
    return $RC
}

stop_ovirt () {
    rm -f $VAR_SUBSYS_OVIRT
}

reload_ovirt () {
        stop_ovirt
        start_ovirt
}

#
# ovirt-post
#
start_ovirt_post() {
    [ -f "$VAR_SUBSYS_OVIRT_POST" ] && exit 0
    {
        log "Starting ovirt-post"
        # wait for libvirt to finish initializing
        local count=0
        while true; do
            if virsh connect qemu:///system --readonly >/dev/null 2>&1; then
                break
            elif [ "$count" == "100" ]; then
                log "Libvirt did not initialize in time..."
                return 1
            else
                log "Waiting for libvirt to finish initializing..."
                count=$(expr $count + 1)
                sleep 1
            fi

            touch $VAR_SUBSYS_OVIRT_POST

        done
        BACKUP=$(mktemp)
        ISSUE=/etc/issue
        ISSUE_NET=/etc/issue.net
        egrep -v "[Vv]irtualization hardware" $ISSUE > $BACKUP
        cp -f $BACKUP $ISSUE
        rm $BACKUP
        hwvirt=$(virsh --readonly capabilities)
        if [[ $hwvirt =~ kvm ]]; then
            log "Hardware virtualization detected"
        else
            log "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            log "!!! Hardware Virtualization Is Unavailable !!!"
            log "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

            echo "Virtualization hardware is unavailable." >> $ISSUE

            flags=$(cat /proc/cpuinfo | grep "^flags")
            if [[ $flags =~ vmx ]] || [[ $flags =~ svm ]]; then
                echo "(Virtualization hardware was detected but is disabled)" >> $ISSUE
            else
                echo "(No virtualization hardware was detected on this system)" >> $ISSUE
            fi
        fi
        if is_local_storage_configured; then
            echo "" >> $ISSUE
            echo "Please login as 'admin' to configure the node" >> $ISSUE
        fi
        cp -f $ISSUE $ISSUE_NET

        # Small hack to fix https://bugzilla.redhat.com/show_bug.cgi?id=805313

        service network restart 2>/dev/null

        if is_standalone; then
            return 0
        fi

        # persist selected configuration files
        ovirt_store_config \
            /etc/krb5.conf \
            /etc/node.d \
            /etc/sysconfig/node-config \
            /etc/libvirt/krb5.tab \
            /etc/ssh/ssh_host*_key*

        . /usr/libexec/ovirt-functions

        # successfull boot from /dev/HostVG/Root
        if grep -q -w root=live:LABEL=Root /proc/cmdline; then
            # set first boot entry as permanent default
            ln -snf /dev/.initramfs/live/grub /boot/grub
            mount -o rw,remount LABEL=Root /dev/.initramfs/live > /tmp/grub-savedefault.log 2>&1
            echo "savedefault --default=0" | grub >> /tmp/grub-savedefault.log 2>&1
            mount -o ro,remount LABEL=Root /dev/.initramfs/live >> /tmp/grub-savedefault.log 2>&1
        fi

        # perform any post startup operations
        case $OVIRT_RUNTIME_MODE in
        esac

        rm -f $VAR_SUBSYS_OVIRT_POST

        log "Completed ovirt-post"
    } >> $OVIRT_LOGFILE 2>&1
}

stop_ovirt_post () {
    echo -n "Stopping ovirt-post: "
    success
}

reload_ovirt_post () {
    stop_ovirt_post
    start_ovirt_post
}


#
# ovirt-cim
#
start_ovirt_cim() {
    [ -f "$VAR_SUBSYS_OVIRT_cim" ] && exit 0
    {
        log "Starting ovirt-cim"

        touch $VAR_SUBSYS_OVIRT_CIM

        if is_cim_enabled; then
            python -c 'from ovirtnode.ovirtfunctions import *; manage_firewall_port("5989","open","tcp")'
            service sblim-sfcb start
        fi

        rm -f $VAR_SUBSYS_OVIRT_CIM

        log "Completed ovirt-cim"
    } >> $OVIRT_LOGFILE 2>&1
}

stop_ovirt_cim () {
    echo -n "Stopping ovirt-cim: "
    if service sblim-sfcb status >/dev/null; then
        python -c 'from ovirtnode.ovirtfunctions import *; manage_firewall_port("5989","close","tcp")'
        service sblim-sfcb stop
    fi
    success
}

reload_ovirt_cim () {
    stop_ovirt_cim
    start_ovirt_cim
}


#
# If called with a param from service file:
#
$@
