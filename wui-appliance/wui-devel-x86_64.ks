install
url --url http://download.fedora.redhat.com/pub/fedora/linux/releases/8/Fedora/x86_64/os/

%include common-install.ks

network --device=eth1 --bootproto=static --ip=192.168.50.2 --netmask=255.255.255.0 --onboot=on

# Create some fake iSCSI partitions
logvol /iscsi3 --name=iSCSI3 --vgname=VolGroup00 --size=64
logvol /iscsi4 --name=iSCSI4 --vgname=VolGroup00 --size=64
logvol /iscsi5 --name=iSCSI5 --vgname=VolGroup00 --size=64

repo --name=f8 --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=fedora-8&arch=x86_64
repo --name=f8-updates --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=updates-released-f8&arch=x86_64
repo --name=ovirt-management --baseurl=http://ovirt.et.redhat.com/repos/ovirt-management-repo/x86_64/

%packages

%include common-pkgs.ks

%post

%include common-post.ks

# make sure our "hostname" resolves to management.priv.ovirt.org
sed -i -e 's/^HOSTNAME.*/HOSTNAME=management.priv.ovirt.org/' /etc/sysconfig/network

cat >> /etc/hosts << \EOF
192.168.50.2 management.priv.ovirt.org
192.168.50.3 node3.priv.ovirt.org
192.168.50.4 node4.priv.ovirt.org
192.168.50.5 node5.priv.ovirt.org
EOF

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

# make sure we don't mount the "fake" iSCSI LUNs, since they are meant to
# be exported
sed -i -e '/\/dev\/VolGroup00\/iSCSI[0-9].*/d' /etc/fstab

# make an NFS directory with some small, fake disks and export them via NFS
# to show off the NFS part of the WUI
mkdir -p /ovirtnfs
for i in `seq 1 5`; do
    dd if=/dev/zero of=/ovirtnfs/disk$i.dsk bs=1 count=1 seek=1G
done
echo "/ovirtnfs 192.168.50.0/24(rw,no_root_squash)" >> /etc/exports

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
    /usr/sbin/dnsmasq -i eth1 -F 192.168.50.6,192.168.50.252 \
        -G 00:16:3e:12:34:57,192.168.50.3 -G 00:16:3e:12:34:58,192.168.50.4 \
        -G 00:16:3e:12:34:59,192.168.50.5 \
        -s priv.ovirt.org \
        -W _ovirt._tcp,management.priv.ovirt.org,80 \
        -W _ipa._tcp,management.priv.ovirt.org,8089 \
        -W _ldap._tcp,managment.priv.ovirt.org,389 \
        --enable-tftp --tftp-root=/tftpboot -M pxelinux.0 \
        -O option:router,192.168.50.1 -O option:ntp-server,192.168.50.2 \
        -R -S 192.168.122.1
    
    # Set up the fake iscsi target
    /usr/sbin/tgtadm --lld iscsi --op new --mode target --tid 1 \
        -T ovirtpriv:storage
    
    #
    # Now associate them to the LVs
    # 
    /usr/sbin/tgtadm --lld iscsi --op new --mode logicalunit --tid 1 \
        --lun 1 -b /dev/VolGroup00/iSCSI3
    /usr/sbin/tgtadm --lld iscsi --op new --mode logicalunit --tid 1 \
        --lun 2 -b /dev/VolGroup00/iSCSI4
    /usr/sbin/tgtadm --lld iscsi --op new --mode logicalunit --tid 1 \
        --lun 3 -b /dev/VolGroup00/iSCSI5
    
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

# get the PXE boot image; this can take a while
PXE_URL=http://ovirt.org/download
IMAGE=ovirt-pxe-host-image-x86_64-0.4.tar.bz2
wget ${PXE_URL}/$IMAGE -O /tmp/$IMAGE
tar -C / -jxvf /tmp/$IMAGE
rm -f /tmp/$IMAGE

%end
