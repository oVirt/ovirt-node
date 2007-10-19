#!/bin/bash

if [ $# -eq 1 ]; then
    ISO=
elif [ $# -eq 2 ]; then
    ISO=$2
else
    echo "Usage: ovirt-flash.sh <usbdevice> [iso-image]"
    exit 1
fi

OUT=/tmp/ovirt-flash.$$
USBDEVICE=$1

if [ ! -b "$USBDEVICE" ]; then
    echo "USB device $USBDEVICE doesn't seem to exist"
    exit 2
fi

if [ -z "$ISO" ]; then
    # ISO image not provided on the command-line; build it
    /usr/bin/livecd-creator -c ovirt.ks >& $OUT
    ISO=`ls -1rt livecd-ovirt*.iso | tail -n 1`
fi
echo $ISO

# clear out the old partition table
dd if=/dev/zero of=$USBDEVICE bs=4096 count=1
echo -e 'n\np\n1\n\n\nt\n6\na\n1\nw\n' | /sbin/fdisk $USBDEVICE
/sbin/mkdosfs -n ovirt ${USBDEVICE}1
cat /usr/lib/syslinux/mbr.bin > $USBDEVICE
/usr/bin/livecd-iso-to-disk $ISO ${USBDEVICE}1
