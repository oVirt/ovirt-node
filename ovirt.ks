lang en_US.UTF-8
keyboard us
timezone US/Eastern
auth --useshadow --enablemd5
selinux --disabled
firewall --disabled
part / --size 950
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
wget
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

# the ovirt service
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
	# HACK: this should be delegated to the iSCSI scripts
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

   	/sbin/iptables -A FORWARD -m physdev --physdev-is-bridged -j ACCEPT
}

stop() {
        /sbin/iptables -D FORWARD -m physdev --physdev-is-bridged -j ACCEPT
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

# next the dynamic bridge setup service
(
echo "#!/bin/bash
#
# ovirt-bridges Start ovirt bridge services
#
# chkconfig: 3 01 99
# description: ovirt-bridges services
#

# Source functions library
. /etc/init.d/functions

start() {
	cd /sys/class/net
	ETHDEVS=\`ls -d eth*\`
	cd \$OLDPWD
	for eth in \$ETHDEVS; do
	    BRIDGE=ovirtbr\`echo \$eth | cut -b4-\`
	    echo -e \"DEVICE=\$eth\nONBOOT=yes\nBRIDGE=\$BRIDGE\" > /etc/sysconfig/network-scripts/ifcfg-\$eth
	    echo -e \"DEVICE=\$BRIDGE\nBOOTPROTO=dhcp\nONBOOT=yes\nTYPE=Bridge\" > /etc/sysconfig/network-scripts/ifcfg-\$BRIDGE
	    echo 'DHCLIENTARGS=\"-R subnet-mask,broadcast-address,time-offset,routers,domain-name,domain-name-servers,host-name,nis-domain,nis-servers,ntp-servers,iscsi-servers,etc-libvirt-nfs-server,libvirt-auth-method\"' >> /etc/sysconfig/network-scripts/ifcfg-\$BRIDGE
	done
}

stop() {
       # nothing to do
       return
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
        echo \"Usage: ovirt-bridges {start|stop|restart}\"
        exit 2
esac" ) > /etc/init.d/ovirt-bridges
chmod +x /etc/init.d/ovirt-bridges
/sbin/chkconfig ovirt-bridges on

# needed for the iscsi-servers dhcp option
(
echo 'option iscsi-servers code 200 = array of ip-address;'
echo 'option etc-libvirt-nfs-server code 201 = text;'
echo 'option libvirt-auth-method code 202 = text;'
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
echo    "if [ -n \"\$new_libvirt_auth_method\" ]; then"
echo -e "\tMETHOD=\`echo \$new_libvirt_auth_method | cut -d':' -f1\`"
echo -e "\tSERVER=\`echo \$new_libvirt_auth_method | cut -d':' -f2-\`"
echo -e "\tif [ \$METHOD = \"tls\" ]; then"
echo -e "\t\tmkdir -p /etc/pki/CA /etc/pki/libvirt/private"
echo -e "\t\tcd /etc/pki/CA ; wget -q http://\$SERVER/cacert.pem"
echo -e "\t\tcd /etc/pki/libvirt/private ; wget -q http://\$SERVER/serverkey.pem"
echo -e "\t\tcd /etc/pki/libvirt ; wget -q http://\$SERVER/servercert.pem"
echo -e "\tfi"
echo    "fi"
) > /etc/dhclient-up-hooks
chmod +x /etc/dhclient-up-hooks

# make libvirtd listen on the external interfaces
sed -i -e 's/#LIBVIRTD_ARGS="--listen"/LIBVIRTD_ARGS="--listen"/' /etc/sysconfig/libvirtd

(
echo "#!/bin/sh

switch=\$(/sbin/ip route list | awk '/^default / { print \$NF }')
/sbin/ifconfig \$1 0.0.0.0 up
/usr/sbin/brctl addif \${switch} \$1" ) > /etc/kvm-ifup

chmod +x /etc/kvm-ifup

# set up qemu daemon to allow outside VNC connections
sed -i -e 's/# vnc_listen = \"0.0.0.0\"/vnc_listen = \"0.0.0.0\"/' /etc/libvirt/qemu.conf

%end
