#!/bin/bash -x

#ISOIMAGE=/root/livecd-ovirt-200710171708.iso
ISOIMAGE=/root/livecd-ovirt-200710181701.iso
ETHERNET_MODULE=e1000e
REMOTE_IP=192.168.25.1
CUSTOM_INIT=/root/ovirt-init

PROGRAMS="/bin/basename /bin/sed /bin/cut /bin/awk /bin/uname /sbin/ifconfig /sbin/ip /sbin/dhclient /sbin/dhclient-script /sbin/route /sbin/consoletype"

# clean up from previous
rm -rf /tftpboot/*

# create the basic TFTP stuff
mkdir -p /tftpboot/pxelinux.cfg
cat <<EOF > /tftpboot/pxelinux.cfg/default
DEFAULT pxeboot
TIMEOUT 30
LABEL pxeboot
      KERNEL vmlinuz
      APPEND initrd=initrd.img
ONERROR LOCALBOOT 0
EOF

cp /usr/lib/syslinux/pxelinux.0 /tftpboot
mkdir -p /mnt/tmp

# pull the initrd and vmlinuz off of the ISO
mount -o loop $ISOIMAGE /mnt/tmp
cp /mnt/tmp/isolinux/vmlinuz /mnt/tmp/isolinux/initrd.img /tftpboot
umount /mnt/tmp

# copy the ISO into place; we will need it for root later
cp $ISOIMAGE /tftpboot

# now edit the initrd
rm -f /tmp/initrd.img
cp /tftpboot/initrd.img /tmp
gzip -dc < /tmp/initrd.img > /tmp/oldinitrd
mkdir /tmp/newinitrd
cd /tmp/newinitrd
cpio -idv < /tmp/oldinitrd
rm -f /tmp/oldinitrd

# find the necessary kernel module for the ethernet device
BOOTKERNEL=`ls lib/modules`
MODULE=`find /lib/modules/$BOOTKERNEL/kernel -name $ETHERNET_MODULE.ko`
cp -f $MODULE lib/modules/$BOOTKERNEL/

mkdir -p var/lib/dhclient var/run

# FIXME: probably better done with "hostpath:newpath", since it is more flexible
# pull in the programs needed
for prog in $PROGRAMS; do
    cp $prog `echo $prog | cut -c2-`
done

# TFTP is special, since we are storing it in /bin, but it comes from /usr/bin
cp /usr/bin/tftp bin/

# now pull in the networking scripts
mkdir -p etc/sysconfig/network-scripts
cp -r /etc/sysconfig/network-scripts/* etc/sysconfig/network-scripts

# finally the init scripts
mkdir -p etc/rc.d/init.d
cp /etc/rc.d/init.d/functions etc/rc.d/init.d

ln -f -s /etc/rc.d/init.d etc/init.d

# last, we need to modify the init script to do the right thing
rm -f init
cp $CUSTOM_INIT init

ISONAME=`basename $ISOIMAGE`
rm -f /tmp/custom_init
cat <<EOF > /tmp/custom_init
insmod /lib/modules/$BOOTKERNEL/$ETHERNET_MODULE.ko
/sbin/ip link set dev eth0 up
/sbin/dhclient eth0
echo "Fetching root filesystem from server..."
/bin/tftp $REMOTE_IP -c get $ISONAME
rootfstype=iso9660
thingtomount=$ISONAME
mountoptions=" -o loop"
EOF

sed -i -e '/# OVIRT: XXXREPLACE_MEXXX/r /tmp/custom_init' init
rm -f /tmp/custom_init

# OK, done with the initrd; package it back up
( find . | cpio -H newc --quiet -o) >| /tmp/newimage
gzip -9 /tmp/newimage

# now put it in place
rm -f /tftpboot/initrd.img.old
mv /tftpboot/initrd.img /tftpboot/initrd.img.old
mv /tmp/newimage.gz /tftpboot/initrd.img

cd /tmp
rm -rf /tmp/newinitrd