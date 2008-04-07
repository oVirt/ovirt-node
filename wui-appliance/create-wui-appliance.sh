#!/bin/bash

ME=$(basename "$0")
warn() { printf "$ME: $@\n" >&2; }
try_h() { printf "Try \`$ME -h' for more information.\n" >&2; }
die() { warn "$@"; try_h; exit 1; }

NAME=developer
RAM=512
IMGNAME=$NAME.img
IMGSIZE=6

MAC=
ISO=
IMGDIR_DEFAULT=/var/lib/libvirt/images
ARCH_DEFAULT=x86_64

ARCH=$ARCH_DEFAULT
IMGDIR=$IMGDIR_DEFAULT

usage() {
    case $# in 1) warn "$1"; try_h; exit 1;; esac
    cat <<EOF
Usage: $ME -i install_iso [-d image_dir] [-a x86_64|i386] [-m MAC]
  -i: location of installation ISO (required)
  -d: directory to place virtual disk (default: $IMGDIR_DEFAULT)
  -a: architecture for the virtual machine (default: $ARCH_DEFAULT)
  -m: specify fixed MAC address for the primary network interface
  -h: display this help and exit
EOF
}

err=0 help=0
while getopts :a:d:i:m:h c; do
    case $c in
        i) ISO=$OPTARG;;
        d) IMGDIR=$OPTARG;;
        a) ARCH=$OPTARG;;
        m) MAC=$OPTARG;;
        h) help=1;;
	'?') err=1; warn "invalid option: \`-$OPTARG'";;
	:) err=1; warn "missing argument to \`-$OPTARG' option";;
        *) err=1; warn "internal error: \`-$OPTARG' not handled";;
    esac
done
test $err = 1 && { try_h; exit 1; }
test $help = 1 && { usage; exit 0; }

test -z "$ISO" && usage "no ISO file specified"
test -r "$ISO" || usage "missing or unreadable ISO file: \`$ISO'"

case $ARCH in
    i386|x86_64);;
    *) usage "invalid architecture: \`$ARCH'";;
esac

if [ -n "$MAC" ]; then
    MAC="-m $MAC"
fi

mkdir -p $IMGDIR

virsh destroy $NAME > /dev/null 2>&1
virsh undefine $NAME > /dev/null 2>&1
virt-install -n $NAME -r $RAM -f "$IMGDIR/$IMGNAME" -s $IMGSIZE --vnc \
             --accelerate -v -c "$ISO" --os-type=linux --arch=$ARCH \
             --noreboot $MAC
./ovirt-mod-xml.sh
virsh start $NAME
virt-viewer $NAME &

exit 0
