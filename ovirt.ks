lang en_US.UTF-8
keyboard us
timezone US/Eastern
auth --useshadow --enablemd5
selinux --disabled
firewall --disabled
part / --size 1024
services --disabled=iptables
bootloader --timeout=1

repo --name=development --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=rawhide&arch=$basearch


%packages
@core
bash
kernel
passwd
policycoreutils
chkconfig
authconfig
rootfiles
dhclient
libvirt
openssh-clients
openssh-server
iscsi-initiator-utils
ntp
kvm
nfs-utils
-policycoreutils
-audit-libs-python
-hdparm
-libsemanage
-ustr
-authconfig
-rhpl
-wireless-tools
-setserial
-prelink
-newt-python
-newt
-selinux-policy-targeted
-selinux-policy
-kudzu
-libselinux-python
-rhpl
-glibc.i686
-xen-libs.i386
-libxml2.i386
-libvirt.i386
-avahi.i386
-libgcrypt.i386
-gnutls.i386
-libstdc++.i386
-e2fsprogs-libs.i386
-ncurses.i386
-readline.i386
-libselinux.i386
-device-mapper-libs.i386
-libdaemon.i386
-dbus-libs.i386
-expat.i386
-libsepol.i386
-libcap.i386
-zlib.i386
-libgpg-error.i386
-libxml2.i386
-libgcc.i386
-kbd
-usermode
-grub
-fedora-logos
-kpartx
-dmraid
-mkinitrd
-parted
-nash
-tar
-openldap
-libuser
-mdadm
-mtools
-cyrus-sasl-lib
-cpio

%post

# first the ovirt service
(
echo "#!/bin/bash
#
# ovirt Start ovirt services
#
# chkconfig: 3 99 01
# description: ovirt services
#

# Source functions library
. /etc/init.d/functions

start() {
        modprobe kvm
        modprobe kvm-intel >& /dev/null
        modprobe kvm-amd >& /dev/null
        # now login to all of the discovered iSCSI servers
        for server in \`cat /etc/iscsi-servers.conf\`; do
            scan=\`/sbin/iscsiadm --mode discovery --type sendtargets --portal \$server 2>/dev/null\`
            if [ \$? -ne 0 ]; then
                 echo \"Failed scanning \$server...skipping\"
                 continue
	    fi
            target=\`echo \$scan | cut -d' ' -f2\`
            port=\`echo \$scan | cut -d':' -f2 | cut -d',' -f1\`
           /sbin/iscsiadm --mode node --targetname \$target --portal \$server:\$port --login
        done
}

stop() {
        /sbin/iscsiadm --mode node --logoutall=all
        rmmod kvm-intel >& /dev/null
        rmmod kvm-amd >& /dev/null
        rmmod kvm >& /dev/null
}

case \"\$1\" in
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
        echo \"Usage: ovirt {start|stop|restart}\"
        exit 2
esac" ) > /etc/init.d/ovirt
chmod +x /etc/init.d/ovirt
/sbin/chkconfig ovirt on

# next set up the bridge
(
echo "DEVICE=ovirtbr"
echo "BOOTPROTO=dhcp"
echo "ONBOOT=yes"
echo "TYPE=Bridge"
echo "DHCLIENTARGS=\"-R subnet-mask,broadcast-address,time-offset,routers,domain-name,domain-name-servers,host-name,nis-domain,nis-servers,ntp-servers,iscsi-servers,etc-libvirt-nfs-server\""
) > /etc/sysconfig/network-scripts/ifcfg-ovirtbr

# needed for the iscsi-servers dhcp option
(
echo 'option iscsi-servers code 200 = array of ip-address;'
echo 'option etc-libvirt-nfs-server code 201 = text;'
) > /etc/dhclient.conf

(
echo    "if [ -n \"\$new_iscsi_servers\" ]; then"
echo -e "\tfor s in \$new_iscsi_servers; do"
echo -e "\t\techo \$s >> /etc/iscsi-servers.conf"
echo -e "\tdone"
echo    "fi"
echo    "if [ -n \"\$new_etc_libvirt_nfs_server\" ]; then"
echo -e "\techo \"\$new_etc_libvirt_nfs_server /etc/libvirt/qemu nfs hard,bg,tcp,intr 0 0\" >> /etc/fstab"
echo    "fi"
) > /etc/dhclient-up-hooks
chmod +x /etc/dhclient-up-hooks

(
echo "DEVICE=eth0"
echo "ONBOOT=yes"
echo "BRIDGE=ovirtbr"
) > /etc/sysconfig/network-scripts/ifcfg-eth0

# make libvirtd listen on the external interfaces
sed -i -e 's/#LIBVIRTD_ARGS="--listen"/LIBVIRTD_ARGS="--listen"/' /etc/sysconfig/libvirtd

# add the certificates
mkdir -p /etc/pki/CA
( echo "-----BEGIN CERTIFICATE-----
MIIB1DCCAT+gAwIBAgIBADALBgkqhkiG9w0BAQUwETEPMA0GA1UEAxMGUmVkSGF0
MB4XDTA3MTAyMjE3NDc0NloXDTA4MTAyMTE3NDc0NlowETEPMA0GA1UEAxMGUmVk
SGF0MIGcMAsGCSqGSIb3DQEBAQOBjAAwgYgCgYDTUi2Wq2reO+PXP17NzBus9G5B
qcn+kuKwPK5aLRKdJYoqEztE4niqZjVdHZ5YgsVvRZbzyEcgR6J9XiAe8q+Q2Eko
KFr7G5YE7rWccnghQuegA8rA48jtdHdl3p9/waIGqyFc8WoAnFUAkmFgrTDyx0Np
rOosMcU7IbK4Mv5UKwIDAQABo0MwQTAPBgNVHRMBAf8EBTADAQH/MA8GA1UdDwEB
/wQFAwMHBAAwHQYDVR0OBBYEFGUmtydFZZoyGbrXJcWPOnlMkFoqMAsGCSqGSIb3
DQEBBQOBgQCmzTiCnF1ro2WSNC3CNsA7u9K1c3r/M8C4bAW05WgVBpnywlsbq/Oo
FgPOPu29zotlpnjk7ckZ0fXXnAssnz/pdk5P4GvZpvls4E/vHZuWM7YMCwfXhexh
UZEk1NBFUzL7uBhNVXyaq6rJwTuUnv9il3WyJ0QhcH7RWUDHRm1rTw==
-----END CERTIFICATE-----" ) > /etc/pki/CA/cacert.pem

mkdir -p /etc/pki/libvirt/private

( echo "-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQC0TwKj+ipZIC1ZrHSxBR/ttaGPSIUX2FIg5cE9Lnqp3i+F0gb7
wu67gxb+Otpk2Tb5Hgo5pwh+pqjxRSP9PCzNHDg0/6lVxHwE7aEB6bDxky19QECv
1zS5J2wmpYEEtS0a+GNF8TmNm7DJMQQKrgFvwh9uJ2i4xE7B0f5eknFBXwIDAQAB
AoGAUvSm+lp2cVrkgoVdirQY5HzUP9/VnAriflA2f7eKp+yZYLAollwxCgRd58mc
ARoOuL6hZbT7q4lx4M82p6Ov2Ed8mReXNPzjJeoDWZlu71yc5TiZZ2B/DVCq5jOZ
QNHtkh4SXUcvWzZ3y/bU69N2qZMXLceIuUEvEKJF2mhLq8ECQQDBOHaM0kc23HO5
uCsqOSJei8HqEaua3GGZhRak8YK6fiyzyfv2DJHKJCtPYztJHnDZFzQ8yx2doZwY
jTEw4UYbAkEA7uSR7Hyc87Wvp/p30c1z9JzTZwpFShQql4u3YESenZNAfcBiSMWV
0UCF2TLAyZg8+gGhX5dIVlryF4cTlhU2DQJAWDQLQhuXsL6QAX7GDZ9JRjmsSsrI
OIhT8X3kqWUqVTHV/Di/UUHJp6o9Lx9QZ/+CakeCbCIYoeWtWTPS+cpMcwJAWGye
XsyZQ9QiWqjpJO1JWGecEG3Ky+q/AS0kCSwdEfJpUqKdPpZ0J+ocIRMaLQR+vYNQ
+hMDIYO0TGUhKNJdGQJBAKMWQXEawSqZ7Z6w0mizK3S3TYqQY4+WIl+43esYg4MO
psFSgyiKA0os1KcDnQ8slX6il9H5B56ylLe3q2DiNk0=
-----END RSA PRIVATE KEY-----" ) > /etc/pki/libvirt/private/serverkey.pem

( echo "-----BEGIN CERTIFICATE-----
MIICFzCCAYKgAwIBAgIBADALBgkqhkiG9w0BAQUwETEPMA0GA1UEAxMGUmVkSGF0
MB4XDTA3MTAyMjE3NTA0NloXDTA4MTAyMTE3NTA0NlowITEPMA0GA1UEChMGUmVk
SGF0MQ4wDAYDVQQDEwVvdmlydDCBnDALBgkqhkiG9w0BAQEDgYwAMIGIAoGAtE8C
o/oqWSAtWax0sQUf7bWhj0iFF9hSIOXBPS56qd4vhdIG+8Luu4MW/jraZNk2+R4K
OacIfqao8UUj/TwszRw4NP+pVcR8BO2hAemw8ZMtfUBAr9c0uSdsJqWBBLUtGvhj
RfE5jZuwyTEECq4Bb8IfbidouMROwdH+XpJxQV8CAwEAAaN2MHQwDAYDVR0TAQH/
BAIwADATBgNVHSUEDDAKBggrBgEFBQcDATAPBgNVHQ8BAf8EBQMDB6AAMB0GA1Ud
DgQWBBS6Z8CskS7lpn5PBxkxwtwGtNUbhDAfBgNVHSMEGDAWgBRlJrcnRWWaMhm6
1yXFjzp5TJBaKjALBgkqhkiG9w0BAQUDgYEAO1KTzlKS/aF5hu8rWEEKspuWZ8X5
voA/N60UJ6aEVNXezG8LiYKIuuFURvhmGQhk+b0mLUrfVA4g767FcjObu8zxhM0t
3adxSLtov8+wIBHYQG2rmwstsMkoEdxGYmQZ72mFfh+pU/u4Cm0MNLTsCp+NyYhH
S3xMKzQLCZvbtDo=
-----END CERTIFICATE-----" ) > /etc/pki/libvirt/servercert.pem

# add the iptables rule for bridge forwarding
/bin/grep -q "/sbin/iptables -A FORWARD -m physdev --physdev-is-bridged -j ACCEPT" /etc/rc.d/rc.local
RETVAL=$?
if [ $RETVAL -ne 0 ]; then
   echo "/sbin/iptables -A FORWARD -m physdev --physdev-is-bridged -j ACCEPT" >> /etc/rc.d/rc.local
fi

(
echo "#!/bin/sh

switch=\$(/sbin/ip route list | awk '/^default / { print \$NF }')
/sbin/ifconfig \$1 0.0.0.0 up
/usr/sbin/brctl addif \${switch} \$1" ) > /etc/kvm-ifup

chmod +x /etc/kvm-ifup

# set up qemu daemon to allow outside VNC connections
sed -i -e 's/# vnc_listen = \"0.0.0.0\"/vnc_listen = \"0.0.0.0\"/' /etc/libvirt/qemu.conf

%end
