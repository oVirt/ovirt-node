#!/bin/bash

. ./ovirt-common.sh

if [ $# -eq 1 ]; then
    ISO=
elif [ $# -eq 2 ]; then
    ISO=$2
else
    echo "Usage: ovirt-flash.sh <usbdevice> [iso-image]"
    exit 1
fi

USBDEVICE=$1
IMGTMP=/var/tmp/ovirt-$$
SQUASHTMP=/var/tmp/ovirt-squash-$$
USBTMP=/var/tmp/ovirt-usb-$$

if [ ! -b "$USBDEVICE" ]; then
    echo "USB device $USBDEVICE doesn't seem to exist"
    exit 2
fi

if [ -z "$ISO" ]; then
    # ISO image not provided on the command-line; build it
    ISO=`create_iso`
fi
echo $ISO

# do setup
mkdir -p $IMGTMP $SQUASHTMP $USBTMP
mount -o loop $ISO $IMGTMP
mount -o loop $IMGTMP/LiveOS/squashfs.img $SQUASHTMP

# clear out the old partition table
dd if=/dev/zero of=$USBDEVICE bs=4096 count=1
echo -e 'n\np\n1\n\n\nt\n83\na\n1\nw\n' | /sbin/fdisk $USBDEVICE

cat /usr/lib/syslinux/mbr.bin > $USBDEVICE
dd if=$SQUASHTMP/LiveOS/ext3fs.img of=${USBDEVICE}1

mount ${USBDEVICE}1 $USBTMP

cp $IMGTMP/isolinux/* $USBTMP

rm -f $USBTMP/isolinux.bin
mv $USBTMP/isolinux.cfg $USBTMP/extlinux.conf

LABEL=`echo $ISO | cut -d'.' -f1 | cut -c-16`
sed -i -e "s/ *append.*/  append initrd=initrd.img root=LABEL=$LABEL ro/" $USBTMP/extlinux.conf

extlinux -i $USBTMP

umount $USBTMP
umount $SQUASHTMP
umount $IMGTMP
rm -rf $SQUASHTMP $IMGTMP $USBTMP
