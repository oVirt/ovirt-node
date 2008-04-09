# make sure our "hostname" resolves to management.priv.ovirt.org
sed -i -e 's/^HOSTNAME.*/HOSTNAME=management.priv.ovirt.org/' /etc/sysconfig/network

echo -e "192.168.50.2\t\tmanagement.priv.ovirt.org" >> /etc/hosts

# automatically refresh the kerberos ticket every hour (we'll create the
# principal on first-boot)
cat > /etc/cron.hourly/ovirtadmin.cron << \EOF
#!/bin/bash
/usr/kerberos/bin/kdestroy
/usr/kerberos/bin/kinit -k -t /usr/share/ovirt-wui/ovirtadmin.tab ovirtadmin@PRIV.OVIRT.ORG
EOF
chmod 755 /etc/cron.hourly/ovirtadmin.cron

# for firefox, we need to make some subdirs and add some preferences
mkdir -p /root/.mozilla/firefox/uxssq4qb.ovirtadmin
cat >> /root/.mozilla/firefox/uxssq4qb.ovirtadmin/prefs.js << \EOF
user_pref("network.negotiate-auth.delegation-uris", "priv.ovirt.org");
user_pref("network.negotiate-auth.trusted-uris", "priv.ovirt.org");
user_pref("browser.startup.homepage", "http://management.priv.ovirt.org/ovirt");
EOF

cat >> /root/.mozilla/firefox/profiles.ini << \EOF
[General]
StartWithLastProfile=1

[Profile0]
Name=ovirtadmin
IsRelative=1
Path=uxssq4qb.ovirtadmin
EOF

# make sure we use ourselves as the nameserver (not what we get from DHCP)
cat > /etc/dhclient-exit-hooks << \EOF
echo "search priv.ovirt.org ovirt.org" > /etc/resolv.conf
echo "nameserver 192.168.50.2" >> /etc/resolv.conf
EOF
chmod +x /etc/dhclient-exit-hooks

# make sure that we get a kerberos principal on every boot
echo "/etc/cron.hourly/ovirtadmin.cron" >> /etc/rc.d/rc.local

cat > /etc/init.d/ovirt-wui-dev-first-run << \EOF
#!/bin/bash
#
# ovirt-wui-dev-first-run First run configuration for Ovirt WUI Dev appliance
#
# chkconfig: 3 95 01
# description: ovirt dev wui appliance first run configuration
#

# Source functions library
. /etc/init.d/functions

KADMIN=/usr/kerberos/sbin/kadmin.local

start() {
	echo -n "Starting ovirt-dev-wui-first-run: "
	(
	# set up freeipa
	/usr/sbin/ipa-server-install -r PRIV.OVIRT.ORG -p ovirt -P ovirt -a ovirtwui --hostname management.priv.ovirt.org -u dirsrv -U

	# now create the ovirtadmin user
	$KADMIN -q 'addprinc -randkey ovirtadmin@PRIV.OVIRT.ORG'	
	$KADMIN -q 'ktadd -k /usr/share/ovirt-wui/ovirtadmin.tab ovirtadmin@PRIV.OVIRT.ORG'
	/etc/cron.hourly/ovirtadmin.cron

	) > /var/log/ovirt-wui-dev-first-run.log 2>&1
	RETVAL=$?
	if [ $RETVAL -eq 0 ]; then
		echo_success
	else
		echo_failure
	fi
	echo
}

case "$1" in
  start)
        start
        ;;
  *)
        echo "Usage: ovirt-wui-dev-first-run {start}"
        exit 2
esac

/sbin/chkconfig ovirt-wui-dev-first-run off
EOF
chmod +x /etc/init.d/ovirt-wui-dev-first-run
/sbin/chkconfig ovirt-wui-dev-first-run on

cat > /etc/init.d/ovirt-wui-dev << \EOF
#!/bin/bash
#
# ovirt-wui-dev Ovirt WUI Dev appliance service
#
# chkconfig: 3 60 40 
# description: ovirt dev wui appliance service
#

# Source functions library
. /etc/init.d/functions

start() {
    echo -n "Starting ovirt-wui-dev: "
    /usr/sbin/dnsmasq -F 192.168.50.3,192.168.50.252 -s priv.ovirt.org \
	-W _ovirt._tcp,management.priv.ovirt.org,80 \
	-W _ipa._tcp,management.priv.ovirt.org,8089 \
	-W _ldap._tcp,managment.priv.ovirt.org,389 \
	--enable-tftp --tftp-root=/tftpboot -M pxelinux.0 \
	-O option:router,192.168.50.1 \
	-O option:ntp-server,192.168.50.2 \
	-R -S 192.168.122.1
    
    # Set up the fake iscsi target
    /usr/sbin/tgtadm --lld iscsi --op new --mode target --tid 1 \
	-T ovirtpriv:storage
    
    #
    # Now associate them to the LVs
    # 
    /usr/sbin/tgtadm --lld iscsi --op new --mode logicalunit --tid 1 \
	--lun 1 -b /dev/VolGroup00/iSCSI1
    /usr/sbin/tgtadm --lld iscsi --op new --mode logicalunit --tid 1 \
	--lun 2 -b /dev/VolGroup00/iSCSI2
    /usr/sbin/tgtadm --lld iscsi --op new --mode logicalunit --tid 1 \
	--lun 3 -b /dev/VolGroup00/iSCSI3
    
    # 
    # Now make them available
    #
    /usr/sbin/tgtadm --lld iscsi --op bind --mode target --tid 1 -I ALL

    echo_success
    echo
}

stop() {
    echo -n "Stopping ovirt-wui-dev: "

    # stop access to the iscsi target
    /usr/sbin/tgtadm --lld iscsi --op unbind --mode target --tid 1 -I ALL

    # unbind the LUNs
    /usr/sbin/tgtadm --lld iscsi --op delete --mode logicalunit --tid 1 --lun 3
    /usr/sbin/tgtadm --lld iscsi --op delete --mode logicalunit --tid 1 --lun 2
    /usr/sbin/tgtadm --lld iscsi --op delete --mode logicalunit --tid 1 --lun 1

    # shutdown the target
    /usr/sbin/tgtadm --lld iscsi --op delete --mode target --tid 1

    kill $(cat /var/run/dnsmasq.pid)

    echo_success
    echo
}

case "$1" in
    start)
        start
        ;;
    stop)
	stop
	;;
    restart)
	stop
	start
	;;
    *)
        echo "Usage: ovirt-wui-dev {start|stop|restart}"
        exit 2
esac
EOF
chmod +x /etc/init.d/ovirt-wui-dev
/sbin/chkconfig ovirt-wui-dev on
