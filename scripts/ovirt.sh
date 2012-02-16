#!/bin/bash
#
# ovirt Start ovirt services
#
### BEGIN INIT INFO
# Provides: ovirt
# Required-Start: ovirt-awake
# Default-Start: 2 3 4 5
# Description: Performs managed node configuration functions.
### END INIT INFO

# Source functions library
. /etc/init.d/functions
. /usr/libexec/ovirt-functions

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
    return $RC
}

stop_ovirt () {
    rm -f $VAR_SUBSYS_OVIRT
}

reload_ovirt () {
        stop_ovirt
        start_ovirt
}

# When called with a parameter:
$@

