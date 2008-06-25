#!/bin/bash

ME=$(basename "$0")
warn() { printf "$ME: $@\n" >&2; }
try_h() { printf "Try \`$ME -h' for more information.\n" >&2; }
die() { warn "$@"; try_h; exit 1; }

RAM=768
IMGSIZE=6000M

ISO=
IMGDIR_DEFAULT=/var/lib/libvirt/images
ARCH_DEFAULT=$(uname -m)

ARCH=$ARCH_DEFAULT
IMGDIR=$IMGDIR_DEFAULT
CONSOLE_FLAG=--noautoconsole

# stupid bridge name so that if all of our checks below fail, we will still
# fail the install
BRIDGENAME=failme

usage() {
    case $# in 1) warn "$1"; try_h; exit 1;; esac
    cat <<EOF
Usage: $ME [-i install_iso | -t install_tree] [-d image_dir] [-a x86_64|i686] [-k kickstart] -v -b
  -i: location of installation ISO
  -t: location of installation tree
  -k: URL of kickstart file for use with installation tree
  -o: Display virt-viewer window during install (implied by -i option)
  -d: directory to place virtual disk (default: $IMGDIR_DEFAULT)
  -a: architecture for the virtual machine (default: $ARCH_DEFAULT)
  -v: Install in developer mode (see http://ovirt.org for details)
  -b: Install in bundled mode (see http://ovirt.org for details)
  -h: display this help and exit
EOF
}

err=0 help=0
devel=0 bundled=0
viewer=0
while getopts :a:d:i:t:k:ohvb c; do
    case $c in
        i) ISO=$OPTARG;;
        t) TREE=$OPTARG;;
        k) KICKSTART=$OPTARG;;
        d) IMGDIR=$OPTARG;;
        a) ARCH=$OPTARG;;
        o) CONSOLE_FLAG=;;
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

test -n "$ISO" -a -n "$TREE" && usage "Can only specify one of -i and -t"

if [ -n "$ISO" ]; then
    test -n "$KICKSTART" && usage "-k not valid in conjunction with -i"
    test -r "$ISO" || usage "missing or unreadable ISO file: \`$ISO'"
    cdrom_arg="-c $ISO"
    # If we're installing from an ISO, we need console to provide kickstart
    CONSOLE_FLAG=
    do_install=1
elif [ -n "$TREE" ]; then
    location_arg="-l $TREE"
    do_install=1
else
    do_install=0
fi

if [ -n "$KICKSTART" ]; then
    extra_flag=-x
    extra_arg="ksdevice=eth0 ks=$KICKSTART"
else
    # If we didn't provide a kickstart, we need console access to provide
    # one at boot time
    CONSOLE_FLAG=
fi

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
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <emulator>$KVM_BINARY</emulator>
    <interface type='network'>
      <mac address='00:16:3e:12:34:$last_mac'/>
      <source network='dummybridge'/>
    </interface>
    <input type='mouse' bus='ps2'/>
    <graphics type='vnc' port='-1' listen='127.0.0.1'/>
  </devices>
</domain>
EOF
}

gen_app() {
    local name=$1
    local disk=$2
    local bridge=$3
    local ram=$4

    cat<<EOF
<domain type='kvm'>
  <name>$name</name>
  <memory>$(( $ram * 1024 ))</memory>
  <currentMemory>$(( $ram * 1024 ))</currentMemory>
  <vcpu>1</vcpu>
  <os>
    <type>hvm</type>
    <boot dev='hd'/>
  </os>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <emulator>$KVM_BINARY</emulator>
    <disk type='file' device='disk'>
      <source file='$disk'/>
      <target dev='hda'/>
    </disk>
    <interface type='network'>
      <source network='default'/>
    </interface>
    <interface type='network'>
      <source network='$bridge'/>
    </interface>
    <input type='mouse' bus='ps2'/>
    <graphics type='vnc' port='-1' listen='127.0.0.1'/>
  </devices>
</domain>
EOF
}

# first, check to see we are root
if [ $( id -u ) -ne 0 ]; then
    die "Must run as root"
fi

# now make sure the packages we need are installed
if [ -e /etc/redhat-release ]; then
    PACKAGES="libvirt kvm virt-manager virt-viewer"
    CHECK=$(rpm $(printf " -q %s " "$PACKAGES")  &> /dev/null; echo $?)
    KVM_BINARY=/usr/bin/qemu-kvm
elif [ -e /etc/debian_version ]; then
    # Works in Ubuntu 8.04. Still needs testing in Debian
    PACKAGES="libvirt0 libvirt-bin kvm qemu virt-manager virt-viewer"
    CHECK=$(dpkg -l $PACKAGES &> /dev/null; echo $?)
    KVM_BINARY=/usr/bin/kvm
else
    die "Not a supported system"
fi

if [ $CHECK -ne 0 ]; then
    # one of the previous packages wasn't installed; bail out
    die "Must have the libvirt, kvm, virt-manager, and virt-viewer packages installed"
fi

if [ $devel = 1 ]; then
    NAME=developer
    BRIDGENAME=dummybridge

    # define the fake managed nodes we will use
    for i in `seq 3 5` ; do
        virsh destroy node$i >& /dev/null
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

virsh net-dumpxml $BRIDGENAME >& /dev/null
RETVAL=$?
if [ $( brctl show | grep -c $BRIDGENAME ) -ne 0 -a $RETVAL -ne 0 ]; then
	# in this case, the bridge exists, but isn't managed by libvirt
	# abort, since the user will have to clean up themselves
	echo "Bridge $BRIDGENAME already exists.  Please make sure you"
	echo "unconfigure $BRIDGENAME, and then try the command again"
	exit 1
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

if [ $do_install = 1 ]; then
    rm -f "$IMGDIR/$IMGNAME"
    qemu-img create -f qcow2 "$IMGDIR/$IMGNAME" $IMGSIZE
    virt-install -n $NAME -r $RAM -f "$IMGDIR/$IMGNAME" --vnc \
        --accelerate -v --os-type=linux --arch=$ARCH \
        -w network:default -w network:$BRIDGENAME \
        $location_arg $cdrom_arg $extra_flag "$extra_arg" --noacpi $CONSOLE_FLAG
else
    test ! -r $IMGDIR/$IMGNAME && die "Disk image not found at $IMGDIR/$IMGNAME"

    TMPXML=$(mktemp)
    gen_app $NAME $IMGDIR/$IMGNAME $BRIDGENAME $RAM > $TMPXML
    virsh define $TMPXML
    rm $TMPXML
    echo "Application defined using disk located at $IMGDIR/$IMGNAME."
    echo "Run virsh start $NAME to start the appliance"
fi
