#!/bin/bash

ME=$(basename "$0")
warn() { printf "$ME: $@\n" >&2; }
try_h() { printf "Try \`$ME -h' for more information.\n" >&2; }
die() { warn "$@"; try_h; exit 1; }

NAME=developer
RAM=768
IMGNAME=$NAME.img
IMGSIZE=6

ISO=
IMGDIR_DEFAULT=/var/lib/libvirt/images
ARCH_DEFAULT=$(uname -i)

ARCH=$ARCH_DEFAULT
IMGDIR=$IMGDIR_DEFAULT

usage() {
    case $# in 1) warn "$1"; try_h; exit 1;; esac
    cat <<EOF
Usage: $ME -i install_iso [-d image_dir] [-a x86_64|i686]
  -i: location of installation ISO (required)
  -d: directory to place virtual disk (default: $IMGDIR_DEFAULT)
  -a: architecture for the virtual machine (default: $ARCH_DEFAULT)
  -h: display this help and exit
EOF
}

err=0 help=0
while getopts :a:d:i:m:h c; do
    case $c in
        i) ISO=$OPTARG;;
        d) IMGDIR=$OPTARG;;
        a) ARCH=$OPTARG;;
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
    i686|x86_64);;
    *) usage "invalid architecture: \`$ARCH'";;
esac

gen_dummy() {
cat <<\EOF
<network>
  <name>dummy</name>
  <bridge name="dummybridge" stp="off" forwardDelay="0" />
  <ip address="192.168.50.1" netmask="255.255.255.0"/>
</network>
EOF
}

# TODO when virFileReadAll is fixed for stdin
#virsh net-define <(gen_dummy)
TMPXML=$(mktemp) || exit 1
gen_dummy > $TMPXML
virsh net-define $TMPXML
rm $TMPXML
virsh net-start dummy
virsh net-autostart dummy

mkdir -p $IMGDIR
virsh destroy $NAME > /dev/null 2>&1
virsh undefine $NAME > /dev/null 2>&1
virt-install -n $NAME -r $RAM -f "$IMGDIR/$IMGNAME" -s $IMGSIZE --vnc \
             --accelerate -v -c "$ISO" --os-type=linux --arch=$ARCH \
             -w network:default -w network:dummy
