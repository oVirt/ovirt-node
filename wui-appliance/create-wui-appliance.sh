#!/bin/bash

NAME=developer
RAM=512
IMGNAME=${NAME}.img
IMGSIZE=6

usage() {
    echo "usage: $0 -i install_iso [-d image_dir] [-a x86_64|i386] [-m MAC]"
    echo "  -i: location of installation ISO"
    echo "  -d: directory to place virtual disk (default: /var/lib/libvirt/images)"
    echo "  -a: architecture for the virtual machine (default: x86_64)"
    echo "  -m: specify fixed MAC address for the primary network interface"
    exit 1
} >&2

MAC=
ISO=
IMGDIR=/var/lib/libvirt/images
ARCH=x86_64
for i ; do
    case $1 in
        -i)
            [ $# -lt 2 ] && usage
            ISO="$2"
            shift; shift;;
        -d)
            [ $# -lt 2 ] && usage
            IMGDIR="$2"
            shift; shift;;
        -a)
            [ $# -lt 2 ] && usage
            ARCH="$2"
            shift; shift;;
        -m)
            [ $# -lt 2 ] && usage
            MAC="$2"
            shift; shift;;
        -?|-*)
            usage;;
    esac
done

if [ -z $ISO ]; then
    echo "Please supply the location of the OS ISO" >&2
    usage
fi

if [[ "$ARCH" != "i386" && "$ARCH" != "x86_64" ]]; then
    echo "Please specify a valid architecture" >&2
    usage
fi

if [ -n $MAC ]; then
    MAC="-m $MAC"
fi

mkdir -p $IMGDIR

virsh destroy $NAME > /dev/null 2>&1
virsh undefine $NAME > /dev/null 2>&1
virt-install -n $NAME -r $RAM -f $IMGDIR/$IMGNAME -s $IMGSIZE --vnc \
             --accelerate -v -c $ISO --os-type=linux --arch=$ARCH \
             --noreboot $MAC
./ovirt-mod-xml.sh
virsh start $NAME
virt-viewer $NAME &

exit 0
