#!/bin/bash
#
# Create an Ovirt Host PXE boot
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

if [ $# -eq 0 ]; then
    ISO=
elif [ $# -eq 1 ]; then
    ISO=$1
else
    echo "Usage: ovirt-pxe.sh [iso-image]"
    exit 1
fi

ISO=`create_iso $ISO` || exit 1

livecd-iso-to-pxeboot $ISO

# append BOOTIF with PXE MAC info
f=tftpboot/pxelinux.cfg/default
grep -q 'IPAPPEND 2' $f || sed -i '/KERNEL/a \\tIPAPPEND 2' $f

