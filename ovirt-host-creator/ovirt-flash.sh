#!/bin/bash
#
# Create an Ovirt Host USB device (stateless)
# Copyright 2008 Red Hat, Inc.
# Written by Chris Lalancette <clalance@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

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

if [ ! -b "$USBDEVICE" ]; then
    echo "USB device $USBDEVICE doesn't seem to exist"
    exit 2
fi

if [ -z "$ISO" ]; then
    ISO=`create_iso` || exit 1
fi
echo $ISO

# clear out the old partition table
dd if=/dev/zero of=$USBDEVICE bs=4096 count=1
echo -e 'n\np\n1\n\n\nt\n6\na\n1\nw\n' | /sbin/fdisk $USBDEVICE
/sbin/mkdosfs -n ovirt ${USBDEVICE}1
cat /usr/lib/syslinux/mbr.bin > $USBDEVICE
/usr/bin/livecd-iso-to-disk $ISO ${USBDEVICE}1
