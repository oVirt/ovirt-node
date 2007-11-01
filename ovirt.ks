lang en_US.UTF-8
keyboard us
timezone US/Eastern
auth --useshadow --enablemd5
selinux --disabled
firewall --disabled
part / --size 950
services --disabled=iptables --enabled=ntpd
bootloader --timeout=1

repo --name=development --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=rawhide&arch=$basearch

repo --name=libvirt-gssapi --baseurl=http://laforge.boston.redhat.com/rpms


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
wget
krb5-workstation
cyrus-sasl-gssapi
cyrus-sasl
cyrus-sasl-lib
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
-zlib.i386
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
-libgpg-error.i386
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
-cpio
-cyrus-sasl-gssapi.i386
-cyrus-sasl-lib.i386

%post

# the ovirt service

cat > /etc/init.d/ovirt << \EOF
#!/bin/bash
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
        # login to all of the discovered iSCSI servers
	# HACK: this should be delegated to the iSCSI scripts
        for server in `cat /etc/iscsi-servers.conf`; do
            scan=`/sbin/iscsiadm --mode discovery --type sendtargets --portal $server 2>/dev/null`
            if [ $? -ne 0 ]; then
                 echo "Failed scanning $server...skipping"
                 continue
	    fi
            target=`echo $scan | cut -d' ' -f2`
            port=`echo $scan | cut -d':' -f2 | cut -d',' -f1`
            /sbin/iscsiadm --mode node --targetname $target --portal $server:$port --login
        done

        /sbin/iptables -A FORWARD -m physdev --physdev-is-bridged -j ACCEPT
}

stop() {
        /sbin/iptables -D FORWARD -m physdev --physdev-is-bridged -j ACCEPT
        /sbin/iscsiadm --mode node --logoutall=all
        rmmod kvm-intel >& /dev/null
        rmmod kvm-amd >& /dev/null
        rmmod kvm >& /dev/null
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
        echo "Usage: ovirt {start|stop|restart}"
        exit 2
esac
EOF

chmod +x /etc/init.d/ovirt
/sbin/chkconfig ovirt on

# next the dynamic bridge setup service
cat > /etc/init.d/ovirt-bridges << \EOF
#!/bin/bash
#
# ovirt-bridges Start ovirt bridge services
#
# chkconfig: 3 01 99
# description: ovirt-bridges services
#

# Source functions library
. /etc/init.d/functions

start() {
        # find all of the ethernet devices in the system
        cd /sys/class/net
        ETHDEVS=`ls -d eth*`
        cd $OLDPWD
        for eth in $ETHDEVS; do
            BRIDGE=ovirtbr`echo $eth | cut -b4-`
            echo -e "DEVICE=$eth\nONBOOT=yes\nBRIDGE=$BRIDGE" > /etc/sysconfig/network-scripts/ifcfg-$eth
            echo -e "DEVICE=$BRIDGE\nBOOTPROTO=dhcp\nONBOOT=yes\nTYPE=Bridge" > /etc/sysconfig/network-scripts/ifcfg-$BRIDGE
            echo 'DHCLIENTARGS="-R subnet-mask,broadcast-address,time-offset,routers,domain-name,domain-name-servers,host-name,nis-domain,nis-servers,ntp-servers,iscsi-servers,etc-libvirt-nfs-server,libvirt-auth-method"' >> /etc/sysconfig/network-scripts/ifcfg-$BRIDGE
        done

        # find and activate all of the swap partitions on the system

        # get the system pagesize; that determines where the swap signature is
        PAGESIZE=`getconf PAGESIZE`

        # look first at raw partitions
        BLOCKDEVS=`ls /dev/sd? /dev/hd? 2>/dev/null`

        for dev in $BLOCKDEVS; do
            DEVICES="$DEVICEES `/sbin/fdisk -l $dev 2>/dev/null | sed -e 's/*/ /' | awk '$5 ~ /82/ {print $1}' | xargs`"
        done

        # now LVM partitions
        DEVICES="$DEVICES `/usr/sbin/lvscan | awk '{print $2}' | tr -d \"'\"`"

        for device in $DEVICES; do
            sig=`dd if=$device bs=1 count=10 skip=$(( $PAGESIZE - 10 )) 2>/dev/null`
            if [ "$sig" = "SWAPSPACE2" ]; then
                /sbin/swapon $device
            fi
        done
}

stop() {
        # nothing to do
        return
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
        echo "Usage: ovirt-bridges {start|stop|restart}"
        exit 2
esac
EOF

chmod +x /etc/init.d/ovirt-bridges
/sbin/chkconfig ovirt-bridges on

# just to get a boot warning to shut up
touch /etc/resolv.conf

# needed for the iscsi-servers dhcp option
cat > /etc/dhclient.conf << EOF
option iscsi-servers code 200 = array of ip-address;
option etc-libvirt-nfs-server code 201 = text;
option libvirt-auth-method code 202 = text;
EOF

cat > /etc/dhclient-up-hooks << \EOF
if [ -n "$new_iscsi_servers" ]; then
    for s in $new_iscsi_servers; do
        echo $s >> /etc/iscsi-servers.conf
    done
fi
if [ -n "$new_etc_libvirt_nfs_server" ]; then
    echo "$new_etc_libvirt_nfs_server /etc/libvirt/qemu nfs hard,bg,tcp,intr 0 0" >> /etc/fstab
fi
if [ -n "$new_libvirt_auth_method" ]; then
    METHOD=`echo $new_libvirt_auth_method | cut -d':' -f1`
    SERVER=`echo $new_libvirt_auth_method | cut -d':' -f2-`
    get_tls() {
        mkdir -p /etc/pki/CA /etc/pki/libvirt/private
        cd /etc/pki/CA ; wget -q http://$SERVER/cacert.pem
        cd /etc/pki/libvirt/private ; wget -q http://$SERVER/serverkey.pem
        cd /etc/pki/libvirt ; wget -q http://$SERVER/servercert.pem        
    }    
    if [ $METHOD = "tls" ]; then
        get_tls
    elif [ $METHOD = "krb5" ]; then
        # we always need to get TLS to get libvirtd to start up
        get_tls

        mkdir -p /etc/libvirt
        wget -q http://$SERVER/$new_ip_address-libvirt.tab -O /etc/libvirt/krb5.tab
        rm -f /etc/krb5.conf ; wget -q http://$SERVER/krb5.conf -O /etc/krb5.conf
    fi
fi
EOF

chmod +x /etc/dhclient-up-hooks

# make libvirtd listen on the external interfaces
sed -i -e 's/#LIBVIRTD_ARGS="--listen"/LIBVIRTD_ARGS="--listen"/' /etc/sysconfig/libvirtd

cat > /etc/kvm-ifup << \EOF
#!/bin/sh

switch=$(/sbin/ip route list | awk '/^default / { print $NF }')
/sbin/ifconfig $1 0.0.0.0 up
/usr/sbin/brctl addif ${switch} $1
EOF

chmod +x /etc/kvm-ifup

# set up qemu daemon to allow outside VNC connections
sed -i -e 's/# vnc_listen = \"0.0.0.0\"/vnc_listen = \"0.0.0.0\"/' /etc/libvirt/qemu.conf

# set up libvirtd to listen on TCP (for kerberos)
sed -i -e 's/# listen_tcp = 1/listen_tcp = 1/' /etc/libvirt/libvirtd.conf

%end
