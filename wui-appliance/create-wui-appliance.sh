#!/bin/bash

ME=$(basename "$0")
warn() { printf "$ME: $@\n" >&2; }
try_h() { printf "Try \`$ME -h' for more information.\n" >&2; }
die() { warn "$@"; try_h; exit 1; }

RAM=768
IMGSIZE=6

ISO=
IMGDIR_DEFAULT=/var/lib/libvirt/images
ARCH_DEFAULT=$(uname -p)

ARCH=$ARCH_DEFAULT
IMGDIR=$IMGDIR_DEFAULT

# stupid bridge name so that if all of our checks below fail, we will still
# fail the install
BRIDGENAME=failme

usage() {
    case $# in 1) warn "$1"; try_h; exit 1;; esac
    cat <<EOF
Usage: $ME -i install_iso [-d image_dir] [-a x86_64|i686]
  -i: location of installation ISO (required)
  -d: directory to place virtual disk (default: $IMGDIR_DEFAULT)
  -a: architecture for the virtual machine (default: $ARCH_DEFAULT)
  -v: Install in developer mode (see http://ovirt.org for details)
  -b: Install in bundled mode (see http://ovirt.org for details)
  -h: display this help and exit
EOF
}

err=0 help=0
devel=0 bundled=0
while getopts :a:d:i:hvb c; do
    case $c in
        i) ISO=$OPTARG;;
        d) IMGDIR=$OPTARG;;
        a) ARCH=$OPTARG;;
        h) help=1;;
        v) devel=1;;
        b) bundled=1;;
	'?') err=1; warn "invalid option: \`-$OPTARG'";;
	:) err=1; warn "missing argument to \`-$OPTARG' option";;
        *) err=1; warn "internal error: \`-$OPTARG' not handled";;
    esac
done
test $err = 1 && { try_h; exit 1; }
test $help = 1 && { usage; exit 0; }

test -z "$ISO" && usage "no ISO file specified"
test -r "$ISO" || usage "missing or unreadable ISO file: \`$ISO'"

test $devel = 1 -a $bundled = 1 && usage "Can only specify one of -v and -b"
test $devel = 0 -a $bundled = 0 && usage "Must specify one of -v or -b"

case $ARCH in
    i686|x86_64);;
    *) usage "invalid architecture: \`$ARCH'";;
esac

gen_bridge() {
name=$1
cat << EOF
<network>
  <name>$name</name>
  <bridge name="$name" stp="off" forwardDelay="0" />
  <ip address="192.168.50.1" netmask="255.255.255.0"/>
</network>
EOF
}

gen_fake_managed_node() {
num=$1
last_mac=$(( 54 + $num ))

cat <<EOF
<domain type='kvm'>
  <name>node$num</name>
  <uuid>25ab2490-7c4c-099f-b647-${num}5ff8efa73f6</uuid>
  <memory>524288</memory>
  <currentMemory>524288</currentMemory>
  <vcpu>1</vcpu>
  <os>
    <type>hvm</type>
    <boot dev='network'/>
  </os>
  <features>
    <acpi/>
  </features>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <emulator>/usr/bin/qemu-kvm</emulator>
    <interface type='network'>
      <mac address='00:16:3e:12:34:$last_mac'/>
      <source network='dummy'/>
    </interface>
    <input type='mouse' bus='ps2'/>
    <graphics type='vnc' port='-1' listen='127.0.0.1'/>
  </devices>
</domain>
EOF
}

if [ $devel = 1 ]; then
    NAME=developer
    BRIDGENAME=dummybridge

    # define the fake managed nodes we will use
    for i in `seq 3 5` ; do
	virsh undefine node$i >& /dev/null
	TMPXML=$(mktemp)
	gen_fake_managed_node $i > $TMPXML
	virsh define $TMPXML
	rm $TMPXML
    done
elif [ $bundled = 1 ]; then
    NAME=bundled
    BRIDGENAME=eth1bridge
fi

# TODO when virFileReadAll is fixed for stdin
#virsh net-define <(gen_dummy)
virsh net-destroy $BRIDGENAME
virsh net-undefine $BRIDGENAME
TMPXML=$(mktemp) || exit 1
gen_bridge $BRIDGENAME > $TMPXML
virsh net-define $TMPXML
rm $TMPXML
virsh net-start $BRIDGENAME
virsh net-autostart $BRIDGENAME

if [ $bundled = 1 ]; then
    # unfortunately, these two can't be done by libvirt at the moment, so
    # we do them by hand here
    # FIXME: how do we make this persistent, so that we survive reboots?
    /usr/sbin/brctl addif $BRIDGENAME eth1
    /sbin/ifconfig eth1 up
fi

IMGNAME=$NAME.img
mkdir -p $IMGDIR
virsh destroy $NAME > /dev/null 2>&1
virsh undefine $NAME > /dev/null 2>&1
virt-install -n $NAME -r $RAM -f "$IMGDIR/$IMGNAME" -s $IMGSIZE --vnc \
    --accelerate -v -c "$ISO" --os-type=linux --arch=$ARCH \
    -w network:default -w network:$BRIDGENAME
