#!/bin/bash -x

setup() {
    mkdir -p /mnt/livecd-tmp /mnt/livecd-tmp2 /mnt/livecd-tmp3
    mount -o loop $1 /mnt/livecd-tmp
    mount -o loop /mnt/livecd-tmp/LiveOS/squashfs.img /mnt/livecd-tmp2
    mount -o loop /mnt/livecd-tmp2/LiveOS/ext3fs.img /mnt/livecd-tmp3
}

teardown() {
    umount /mnt/livecd-tmp3
    umount /mnt/livecd-tmp2
    umount /mnt/livecd-tmp
    rmdir /mnt/livecd-tmp*
}

usage() {
    echo "Usage: mount-livecd <setup|teardown> <iso>"
}

if [ $# -ne 2 ]; then
    usage
    exit 1
fi

case "$1" in
    setup)
	setup $2
	;;
    teardown)
	teardown
	;;
    *)
	usage
	;;
esac