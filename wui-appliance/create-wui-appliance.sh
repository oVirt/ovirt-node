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
ARCH_DEFAULT=$(uname -p)

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

gen_bridge() {
name=${1}bridge
addr=$2
cat << EOF
<network>
  <name>$name</name>
  <bridge name="$name" stp="off" forwardDelay="0" />
  <ip address="$addr" netmask="255.255.255.0"/>
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

if [ $ME = "create-wui-appliance.sh" ]; then
    # TODO when virFileReadAll is fixed for stdin
    #virsh net-define <(gen_dummy)
    TMPXML=$(mktemp) || exit 1
    gen_bridge "dummy" "192.168.50.1" > $TMPXML
    virsh net-define $TMPXML
    rm $TMPXML
    virsh net-start dummy
    virsh net-autostart dummy

    # define the fake managed nodes we will use
    for i in `seq 3 5` ; do
	virsh undefine node$i >& /dev/null
	TMPXML=$(mktemp)
	gen_fake_managed_node $i > $TMPXML
	virsh define $TMPXML
	rm $TMPXML
    done

    mkdir -p $IMGDIR
    virsh destroy $NAME > /dev/null 2>&1
    virsh undefine $NAME > /dev/null 2>&1
    virt-install -n $NAME -r $RAM -f "$IMGDIR/$IMGNAME" -s $IMGSIZE --vnc \
        --accelerate -v -c "$ISO" --os-type=linux --arch=$ARCH \
        -w network:default -w network:dummy
elif [ $ME = "setup-prod.sh" ]; then
    TMPXML=$(mktemp) || exit 1
    gen_bridge "eth1" "192.168.25.1" > $TMPXML
    virsh net-define $TMPXML
    rm $TMPXML
    virsh net-start eth1bridge
    virsh net-autostart eth1bridge
    
    /usr/sbin/brctl addif eth1bridge eth1
    
    virsh destroy $NAME > /dev/null 2>&1
    virsh undefine $NAME > /dev/null 2>&1
    virt-install -n $NAME -r $RAM -f "$IMGDIR/$IMGNAME" -s $IMGSIZE --vnc \
        --accelerate -v -c "$ISO" --os-type=linux --arch=$ARCH \
        -w network:default -w network:eth1bridge
else
    usage "This script must be run as either create-wui-appliance.sh or setup-prod.sh"
fi

