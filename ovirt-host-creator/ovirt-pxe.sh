#!/bin/bash

. ./ovirt-common.sh

if [ $# -eq 2 ]; then
    ETHERNET_MODULE=$1
    REMOTE_IP=$2
    ISO=
elif [ $# -eq 3 ]; then
    ETHERNET_MODULE=$1
    REMOTE_IP=$2
    ISO=$3
else
    echo "Usage: ovirt-pxe.sh <ether_mod> <remote_ip> [iso-image]"
    exit 1
fi

OUT=/tmp/ovirt-pxe.$$

if [ -z "$ISO" ]; then
    ISO=`create_iso`
fi

CUSTOM_INIT=`pwd`/ovirt-init
ISOIMAGE=`pwd`/$ISO
NEWINITDIR=`pwd`/`mktemp -d newinitrdXXXXX`
ISOTMP=`pwd`/`mktemp -d isotmpXXXXXX`
SQUASHFSTMP=`pwd`/`mktemp -d squashfstmpXXXXXX`
EXT3TMP=`pwd`/`mktemp -d ext3tmpXXXXXX`

PROGRAMS="/bin/basename /bin/sed /bin/cut /bin/awk /bin/uname /sbin/ifconfig /sbin/ip /sbin/dhclient /sbin/dhclient-script /sbin/route /sbin/consoletype /bin/cp /bin/mktemp /usr/bin/tftp /usr/bin/logger"

mkdir -p /tftpboot

# clean up from previous
rm -rf /tftpboot/*

# create the basic TFTP stuff
mkdir -p /tftpboot/pxelinux.cfg
cat <<EOF > /tftpboot/pxelinux.cfg/default
DEFAULT pxeboot
TIMEOUT 100
PROMPT 1
LABEL pxeboot
      KERNEL vmlinuz
      APPEND initrd=initrd.img
ONERROR LOCALBOOT 0
EOF

cp /usr/lib/syslinux/pxelinux.0 /tftpboot

mount -o loop $ISOIMAGE $ISOTMP
mount -o loop $ISOTMP/LiveOS/squashfs.img $SQUASHFSTMP
mount -o loop $SQUASHFSTMP/LiveOS/ext3fs.img $EXT3TMP

# pull the initrd and vmlinuz off of the ISO
cp $ISOTMP/isolinux/vmlinuz $ISOTMP/isolinux/initrd.img /tftpboot

# copy the ISO into place; we will need it for root later
cp $ISOIMAGE /tftpboot

# now edit the initrd
rm -f /tmp/initrd.img
cp /tftpboot/initrd.img /tmp
gzip -dc < /tmp/initrd.img > /tmp/oldinitrd
cd $NEWINITDIR
cpio -id < /tmp/oldinitrd
rm -f /tmp/oldinitrd

# find the necessary kernel module for the ethernet device
BOOTKERNEL=`ls lib/modules`
MODULE=`find $EXT3TMP/lib/modules/$BOOTKERNEL/kernel -name $ETHERNET_MODULE.ko`
cp -f $MODULE lib/modules/$BOOTKERNEL/

mkdir -p var/lib/dhclient var/run tmp etc usr/bin
touch etc/resolv.conf

# pull in the programs needed
for prog in $PROGRAMS; do
    cp $EXT3TMP/$prog `echo $prog | cut -c2-`
done

# now pull in the networking scripts
mkdir -p etc/sysconfig/network-scripts
cp -r $EXT3TMP/etc/sysconfig/network-scripts/* etc/sysconfig/network-scripts

# finally the init scripts
mkdir -p etc/rc.d/init.d
cp $EXT3TMP/etc/rc.d/init.d/functions etc/rc.d/init.d

ln -f -s /etc/rc.d/init.d etc/init.d

umount $EXT3TMP
umount $SQUASHFSTMP
umount $ISOTMP

rmdir $EXT3TMP
rmdir $SQUASHFSTMP
rmdir $ISOTMP

# now we need to modify the init script to do the right thing
rm -f init
cp $CUSTOM_INIT init

ISONAME=`basename $ISOIMAGE`
rm -f /tmp/custom_init
cat <<EOF > /tmp/custom_init
insmod /lib/modules/$BOOTKERNEL/$ETHERNET_MODULE.ko
/sbin/ip link set dev eth0 up
/sbin/dhclient eth0
echo "Fetching root filesystem from server..."
/usr/bin/tftp $REMOTE_IP -c get $ISONAME
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

rm -rf $NEWINITDIR
