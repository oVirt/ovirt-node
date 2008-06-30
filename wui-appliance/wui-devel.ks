install

%include common-install.ks

network --device=eth1 --bootproto=static --ip=192.168.50.2 --netmask=255.255.255.0 --onboot=on --nameserver=192.168.50.2

# Create some fake iSCSI partitions
logvol /iscsi3 --name=iSCSI3 --vgname=VolGroup00 --size=64
logvol /iscsi4 --name=iSCSI4 --vgname=VolGroup00 --size=64
logvol /iscsi5 --name=iSCSI5 --vgname=VolGroup00 --size=64

%include repos.ks

%packages --nobase

%include common-pkgs.ks

%post
exec > /root/kickstart-post.log 2>&1

%include common-post.ks

# make sure our "hostname" resolves to management.priv.ovirt.org
sed -i -e 's/^HOSTNAME.*/HOSTNAME=management.priv.ovirt.org/' \
  /etc/sysconfig/network

# make sure to update the /etc/hosts with the list of all possible DHCP
# addresses we can hand out; dnsmasq uses this
echo "192.168.50.2 management.priv.ovirt.org" >> /etc/hosts
for i in `seq 3 252` ; do
    echo "192.168.50.$i node$i.priv.ovirt.org" >> /etc/hosts
done

# Enable forwarding so this node can act as a router for the .50 network
sed -i 's/net.ipv4.ip_forward = .*/net.ipv4.ip_forward = 1/' /etc/sysctl.conf
cat > /etc/sysconfig/iptables << EOF
*nat
-A POSTROUTING -o eth0 -j MASQUERADE
COMMIT
EOF

principal=ovirtadmin
realm=PRIV.OVIRT.ORG
password=ovirt
cron_file=/etc/cron.hourly/ovirtadmin.cron
ktab_file=/usr/share/ovirt-wui/ovirtadmin.tab

# automatically refresh the kerberos ticket every hour (we'll create the
# principal on first-boot)
cat > $cron_file << EOF
#!/bin/bash
export PATH=/usr/kerberos/bin:$PATH
kdestroy
kinit -k -t $ktab_file $principal@$realm
EOF
chmod 755 $cron_file

ff_profile_dir=uxssq4qb.ovirtadmin

# for firefox, we need to make some subdirs and add some preferences
mkdir -p /root/.mozilla/firefox/$ff_profile_dir
cat >> /root/.mozilla/firefox/$ff_profile_dir/prefs.js << \EOF
user_pref("network.negotiate-auth.delegation-uris", "priv.ovirt.org");
user_pref("network.negotiate-auth.trusted-uris", "priv.ovirt.org");
user_pref("browser.startup.homepage", "http://management.priv.ovirt.org/ovirt");
EOF

cat >> /root/.mozilla/firefox/profiles.ini << EOF
[General]
StartWithLastProfile=1

[Profile0]
Name=ovirtadmin
IsRelative=1
Path=$ff_profile_dir
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

# make sure that we get a kerberos principal on every boot
echo "$cron_file" >> /etc/rc.d/rc.local

# make collectd.conf.
cat > /etc/collectd.conf << \EOF
LoadPlugin network
LoadPlugin logfile
LoadPlugin rrdtool
LoadPlugin unixsock

<Plugin logfile>
        LogLevel info
        File STDOUT
</Plugin>

<Plugin network>
        Listen "0.0.0.0"
</Plugin>

<Plugin rrdtool>
        DataDir "/var/lib/collectd/rrd"
        CacheTimeout 120
        CacheFlush   900
</Plugin>

<Plugin unixsock>
        SocketFile "/var/lib/collectd/unixsock"
</Plugin>

EOF


first_run_file=/etc/init.d/ovirt-wui-dev-first-run
sed -e "s,@cron_file@,$cron_file," \
    -e "s,@principal@,$principal," \
    -e "s,@realm@,$realm," \
    -e "s,@password@,$password,g" \
    -e "s,@ktab_file@,$ktab_file," \
   > $first_run_file << \EOF
#!/bin/bash
#
# ovirt-wui-dev-first-run First run configuration for oVirt WUI Dev appliance
#
# chkconfig: 3 95 01
# description: ovirt dev wui appliance first run configuration
#

# Source functions library
. /etc/init.d/functions

export PATH=/usr/kerberos/bin:$PATH

start() {
	echo -n "Starting ovirt-dev-wui-first-run: "
	(
	# workaround for https://bugzilla.redhat.com/show_bug.cgi?id=451936
	sed -i '/\[kdcdefaults\]/a \ kdc_ports = 88' /usr/share/ipa/kdc.conf.template
	# set up freeipa
	ipa-server-install -r PRIV.OVIRT.ORG -p @password@ -P @password@ -a @password@ \
	  --hostname management.priv.ovirt.org -u dirsrv -U

	# now create the ovirtadmin user
	echo @password@|kinit admin
	# change max username length policy
	ldapmodify -h management.priv.ovirt.org -p 389 -Y GSSAPI <<LDAP
dn: cn=ipaConfig,cn=etc,dc=priv,dc=ovirt,dc=org
changetype: modify
replace: ipaMaxUsernameLength
ipaMaxUsernameLength: 12
LDAP
	ipa-adduser -f Ovirt -l Admin -p @password@ @principal@
	ipa-moduser --setattr krbPasswordExpiration=19700101000000Z @principal@
	ipa-getkeytab -s management.priv.ovirt.org -p @principal@ -k @ktab_file@
	@cron_file@

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

chkconfig ovirt-wui-dev-first-run off
EOF
chmod +x $first_run_file
chkconfig ovirt-wui-dev-first-run on

cat > /etc/init.d/ovirt-wui-dev << \EOF
#!/bin/bash
#
# ovirt-wui-dev oVirt WUI Dev appliance service
#
# chkconfig: 3 60 40 
# description: ovirt dev wui appliance service
#

# Source functions library
. /etc/init.d/functions

start() {
    echo -n "Starting ovirt-wui-dev: "
    dnsmasq -i eth1 -F 192.168.50.6,192.168.50.252 \
        -G 00:16:3e:12:34:57,192.168.50.3 -G 00:16:3e:12:34:58,192.168.50.4 \
        -G 00:16:3e:12:34:59,192.168.50.5 \
        -s priv.ovirt.org \
        -W _ovirt._tcp,management.priv.ovirt.org,80 \
        -W _ipa._tcp,management.priv.ovirt.org,80 \
        -W _ldap._tcp,management.priv.ovirt.org,389 \
        -W _collectd._tcp,management.priv.ovirt.org,25826 \
        -W _identify._tcp,management.priv.ovirt.org,12120 \
        --enable-tftp --tftp-root=/var/lib/tftpboot -M pxelinux.0 \
        -O option:router,192.168.50.2 -O option:ntp-server,192.168.50.2 \
        --dhcp-option=12 \
        -R --local /priv.ovirt.org/ --server 192.168.122.1
    
    # Set up the fake iscsi target
    tgtadm --lld iscsi --op new --mode target --tid 1 \
        -T ovirtpriv:storage
    
    #
    # Now associate them to the LVs
    # 
    tgtadm --lld iscsi --op new --mode logicalunit --tid 1 \
        --lun 1 -b /dev/VolGroup00/iSCSI3
    tgtadm --lld iscsi --op new --mode logicalunit --tid 1 \
        --lun 2 -b /dev/VolGroup00/iSCSI4
    tgtadm --lld iscsi --op new --mode logicalunit --tid 1 \
        --lun 3 -b /dev/VolGroup00/iSCSI5

    # 
    # Now make them available
    #
    tgtadm --lld iscsi --op bind --mode target --tid 1 -I ALL

    echo_success
    echo
}

stop() {
    echo -n "Stopping ovirt-wui-dev: "

    # stop access to the iscsi target
    tgtadm --lld iscsi --op unbind --mode target --tid 1 -I ALL

    # unbind the LUNs
    tgtadm --lld iscsi --op delete --mode logicalunit --tid 1 --lun 3
    tgtadm --lld iscsi --op delete --mode logicalunit --tid 1 --lun 2
    tgtadm --lld iscsi --op delete --mode logicalunit --tid 1 --lun 1

    # shutdown the target
    tgtadm --lld iscsi --op delete --mode target --tid 1

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
chkconfig ovirt-wui-dev on

%end
