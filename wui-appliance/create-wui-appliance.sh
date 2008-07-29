#!/bin/bash

ME=$(basename "$0")
warn() { printf "$ME: $@\n" >&2; }
try_h() { printf "Try \`$ME -h' for more information.\n" >&2; }
die() { warn "$@"; try_h; exit 1; }

RAM=768
IMGSIZE=6000M

ISO=
IMGDIR_DEFAULT=/var/lib/libvirt/images
NET_SCRIPTS=/etc/sysconfig/network-scripts
NAME=ovirt-appliance
BRIDGENAME=ovirtbr

IMGDIR=$IMGDIR_DEFAULT

usage() {
    case $# in 1) warn "$1"; try_h; exit 1;; esac
    cat <<EOF
Usage: $ME [-c] [-d image_dir] [-k kickstart] [-e eth]
  -d: directory to place virtual disk (default: $IMGDIR_DEFAULT)
  -c: compress the image (qcow2 compressed)
  -k: appliance kickstart file
  -e: ethernet device to use as bridge (i.e. eth1)
  -h: display this help and exit
EOF
}

err=0 help=0
compress=0
bridge=
while getopts :d:k:he: c; do
    case $c in
        d) IMGDIR=$OPTARG;;
        c) compress=1;;
        k) KICKSTART=$OPTARG;;
        e) bridge=$OPTARG;;
        h) help=1;;
        '?') err=1; warn "invalid option: \`-$OPTARG'";;
        :) err=1; warn "missing argument to \`-$OPTARG' option";;
        *) err=1; warn "internal error: \`-$OPTARG' not handled";;
    esac
done
test $err = 1 && { try_h; exit 1; }
test $help = 1 && { usage; exit 0; }

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
      <source network='$BRIDGENAME'/>
    </interface>
    <serial type='pty'>
      <target port='0'/>
    </serial>
    <console type='pty'>
      <target port='0'/>
    </console>
    <input type='mouse' bus='ps2'/>
    <graphics type='vnc' port='-1' listen='127.0.0.1'/>
  </devices>
</domain>
EOF
}

gen_app() {
    local disk=$1
    local ram=$2

    cat<<EOF
<domain type='kvm'>
  <name>$NAME</name>
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
      <source network='$BRIDGENAME'/>
    </interface>
    <serial type='pty'>
      <target port='0'/>
    </serial>
    <console type='pty'>
      <target port='0'/>
    </console>
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
    die "Must have the $PACKAGES packages installed"
fi

service libvirtd status > /dev/null 2>&1 \
    || service libvirtd start > /dev/null 2>&1
chkconfig libvirtd on

# Cleanup to handle older version of script that used these bridge names
{
    virsh net-destroy dummybridge
    virsh net-undefine dummybridge
    brctl delif eth1bridge eth1
    virsh net-destroy eth1bridge
    virsh net-undefine eth1bridge
} > /dev/null 2>&1

# If we're bridging to a physical network, run some checks to make sure the
# choice of physical eth device is sane
if [ -n "$bridge" ]; then
    # Check to see if the physical device is present
    ifconfig $bridge > /dev/null 2>&1 ; bridge_dev_present=$?
    test $bridge_dev_present != 0 \
        && die "$bridge device not present, aborting!"

    # Check to make sure that the system is not already using the interface
    test -f $NET_SCRIPTS/ifcfg-$bridge \
        && die "$bridge defined in $NET_SCRIPTS, aborting!"

    # Check to see if the eth device is already tied to a non oVirt bridge
    attached_bridge=$(brctl show \
        | awk -v BRIDGE=$bridge '$4~BRIDGE {print $1}')
    test -n "$attached_bridge" -a "$attached_bridge" != "$BRIDGENAME" \
        && die "$bridge already attached to other bridge $attached_bridge"

    # Check to see if the eth device does not have an active inet address
    ip address show dev $bridge \
        | grep "inet.*$bridge" > /dev/null 2>&1 ; bridge_dev_active=$?
    test $bridge_dev_active == 0 \
        && die "$bridge device active with ip address, aborting!"
fi

# define the fake managed nodes we will use. These can be used for both
# developer and bundled, since the bridge name/network config is the same
for i in `seq 3 5` ; do
    virsh destroy node$i >& /dev/null
    virsh undefine node$i >& /dev/null
    TMPXML=$(mktemp)
    gen_fake_managed_node $i > $TMPXML
    virsh define $TMPXML
    rm $TMPXML
done

virsh net-dumpxml $BRIDGENAME >& /dev/null
RETVAL=$?
if [ $( brctl show | grep -c $BRIDGENAME ) -ne 0 -a $RETVAL -ne 0 ]; then
    # in this case, the bridge exists, but isn't managed by libvirt
    # abort, since the user will have to clean up themselves
    echo "Bridge $BRIDGENAME already exists.  Please make sure you"
    echo "unconfigure $BRIDGENAME, and then try the command again"
    exit 1
fi

# Remove old bridge device if it exists
sed -i "/# $BRIDGENAME/d" /etc/rc.d/rc.local
old_bridge=$(brctl show \
    | awk -v BRIDGENAME=$BRIDGENAME '$1~BRIDGENAME {print $4}')
if [ -n "$old_bridge" ]; then
    echo "Removing old bridge $old_bridge"
    ifconfig $old_bridge down
    brctl delif $BRIDGENAME $old_bridge
fi

virsh net-destroy $BRIDGENAME > /dev/null 2>&1
virsh net-undefine $BRIDGENAME > /dev/null 2>&1
TMPXML=$(mktemp) || exit 1
gen_bridge $BRIDGENAME > $TMPXML
virsh net-define $TMPXML
rm $TMPXML
virsh net-start $BRIDGENAME
virsh net-autostart $BRIDGENAME

if [ -n "$bridge" ]; then
    # FIXME: unfortunately, these two can't be done by libvirt at the
    # moment, so we do them by hand here and persist the config by
    # by adding to rc.local
    echo "Adding new bridge $bridge"
    TMPBRCTL=$(mktemp) || exit 1
    cat > $TMPBRCTL << EOF
brctl addif $BRIDGENAME $bridge # $BRIDGENAME
ifconfig $bridge up # $BRIDGENAME
EOF
    chmod a+x $TMPBRCTL /etc/rc.d/rc.local

    cat $TMPBRCTL >> /etc/rc.d/rc.local

    $TMPBRCTL
    rm $TMPBRCTL
fi

# Cleanup to handle older version of script that used these domain names
{
    virsh destroy developer
    virsh undefine developer
    virsh destroy bundled
    virsh undefine bundled
} > /dev/null 2>&1

IMGNAME=$NAME.img
mkdir -p $IMGDIR
virsh destroy $NAME > /dev/null 2>&1
virsh undefine $NAME > /dev/null 2>&1

if [ -n "$KICKSTART" ]; then
    mkdir -p tmp
    set -e
    appliance-creator --config $KICKSTART --name $NAME --tmpdir $(pwd)/tmp
    # FIXME add --compress option to appliance-creator
    if [ $compress -ne 0 ]; then
        echo -n "Compressing the image..."
        qemu-img convert -c $NAME-sda.raw -O qcow2 "$IMGDIR/$IMGNAME"
        rm ovirt-appliance-sda.raw
        echo "done"
    else
        echo -n "Moving the image..."
        mv ovirt-appliance-sda.raw "$IMGDIR/$IMGNAME"
        restorecon -v "$IMGDIR/$IMGNAME"
        echo "done"
    fi
    set +e
fi

test ! -r $IMGDIR/$IMGNAME && die "Disk image not found at $IMGDIR/$IMGNAME"

TMPXML=$(mktemp) || exit 1
# FIXME virt-image to define the appliance instance
gen_app $IMGDIR/$IMGNAME $RAM > $TMPXML
virsh define $TMPXML
rm $TMPXML
echo "Application defined using disk located at $IMGDIR/$IMGNAME."
echo "Run virsh start $NAME to start the appliance"
