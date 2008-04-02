cat > /etc/sysconfig/network-scripts/ifcfg-eth1 << \EOF
# Realtek Semiconductor Co., Ltd. RTL-8139/8139C/8139C+
DEVICE=eth1
BOOTPROTO=static
IPADDR=192.168.50.2
NETMASK=255.255.255.0
BROADCAST=192.168.50.255
HWADDR=00:16:3E:12:34:56
ONBOOT=yes
EOF

# make sure our "hostname" resolves to management.priv.ovirt.org
sed -i -e 's/^HOSTNAME.*/HOSTNAME=management.priv.ovirt.org/' /etc/sysconfig/network

echo -e "192.168.50.2\t\tmanagement.priv.ovirt.org" >> /etc/hosts

cat > /etc/dhcpd.conf << \EOF
allow booting;
allow bootp;
ddns-update-style interim;
ignore client-updates;

option libvirt-auth-method code 202 = text;

subnet 192.168.50.0 netmask 255.255.255.0 {
        option domain-name "priv.ovirt.org";
        option domain-name-servers 192.168.50.2;
        option ntp-servers 192.168.50.2;
        next-server 192.168.50.2;
        option routers 192.168.50.1;
        option libvirt-auth-method "krb5:192.168.50.2:8089/config";
        filename "pxelinux.0";
        host node3 {
                fixed-address 192.168.50.3;
                hardware ethernet 00:16:3e:12:34:57;
        }
        host node4 {
                fixed-address 192.168.50.4;
                hardware ethernet 00:16:3e:12:34:58;
        }
        host node5 {
                fixed-address 192.168.50.5;
                hardware ethernet 00:16:3e:12:34:59;
        }
}
EOF

cat > /etc/sysconfig/dhcpd << \EOF
# Command line options here
DHCPDARGS="eth1"
EOF

cat > /var/named/chroot/etc/named.conf << \EOF
options {
        //listen-on port 53 { 127.0.0.1; };
        //listen-on-v6 port 53 { ::1; };
        directory       "/var/named";
        dump-file       "/var/named/data/cache_dump.db";
        statistics-file "/var/named/data/named_stats.txt";
        memstatistics-file "/var/named/data/named_mem_stats.txt";
        //allow-query     { localhost; };
        recursion yes;
        allow-transfer {"none";};
        allow-recursion {192.168.50.0/24; 127.0.0.1;};
        forward only;
        forwarders { 192.168.122.1; };
};

logging {
        channel default_debug {
                file "data/named.run";
                severity dynamic;
        };
};

zone "." IN {
        type hint;
        file "named.ca";
};

include "/etc/named.rfc1912.zones";

zone "priv.ovirt.org" {
        type master;
        file "priv.ovirt.org.zone";
};

zone "50.168.192.in-addr.arpa" {
        type master;
        file "50.168.192.in-addr.arpa.zone";
};
EOF

cat > /var/named/chroot/var/named/priv.ovirt.org.zone << \EOF
$TTL 86400
@       IN      SOA     @  management.priv.ovirt.org. (
                        28 ; serial
                        180 ; refresh
                        60 ; retry
                        604800 ; expire
                        60 ; ttl
                        )

@       IN      NS      management.priv.ovirt.org.

@       IN      MX      2       priv.ovirt.org.

@       IN      A       192.168.50.2

management      IN      A       192.168.50.2
node3           IN      A       192.168.50.3
node4           IN      A       192.168.50.4
node5           IN      A       192.168.50.5
EOF

cat > /var/named/chroot/var/named/50.168.192.in-addr.arpa.zone << \EOF
$TTL 86400
@       IN      SOA     @       management.priv.ovirt.org.   (
                                8 ; serial
                                28800 ; refresh
                                14400 ; retry
                                3600000 ; expire
                                86400 ; ttl
                                )

@               IN      NS      management.priv.ovirt.org.
2               IN      PTR     management.priv.ovirt.org.
3               IN      PTR     node3.priv.ovirt.org.
4               IN      PTR     node4.priv.ovirt.org.
5               IN      PTR     node5.priv.ovirt.org.
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
	/usr/sbin/ipa-server-install -r PRIV.OVIRT.ORG -p ovirtwui -P ovirtwui -a ovirtwui --hostname management.priv.ovirt.org -u dirsrv -U

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

# Setup the iscsi stuff to be ready on each boot.  Since tgtadm does not use
# a config file append what we need to the rc.local file.  Note that this for
# the developers version only

cat >> /etc/rc.d/rc.local << \EOF
#
# Set up the fake iscsi targets
/usr/sbin/tgtadm --lld iscsi --op new --mode target --tid 1 -T ovirtpriv:storage
#
# Now associate them to the LVs
# 
/usr/sbin/tgtadm --lld iscsi --op new --mode logicalunit --tid 1 --lun 1 -b /dev/VolGroup00/iSCSI1
/usr/sbin/tgtadm --lld iscsi --op new --mode logicalunit --tid 1 --lun 2 -b /dev/VolGroup00/iSCSI2
/usr/sbin/tgtadm --lld iscsi --op new --mode logicalunit --tid 1 --lun 3 -b /dev/VolGroup00/iSCSI3
# 
# Now make them available
#
/usr/sbin/tgtadm --lld iscsi --op bind --mode target --tid 1 -I ALL
EOF

