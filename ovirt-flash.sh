#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: ovirt-flash.sh <usbdevice>"
    exit 1
fi

OUT=/tmp/output.$$
USBDEVICE="$1"

#/usr/bin/livecd-creator -c ovirt.ks >& $OUT
ISO=`ls -rt livecd-ovirt*.iso | tail -n 1`
echo $ISO

# clear out the old partition table
dd if=/dev/zero of=$USBDEVICE bs=4096 count=1
echo -e 'n\np\n1\n\n\nt\n6\na\n1\nw\n' | /sbin/fdisk $USBDEVICE
/sbin/mkdosfs -n ovirt ${USBDEVICE}1
cat /usr/lib/syslinux/mbr.bin > $USBDEVICE
/usr/bin/livecd-iso-to-disk $ISO ${USBDEVICE}1