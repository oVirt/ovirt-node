#!/bin/bash

#
# build all oVirt components
#
# - create local YUM repository with Fedora subset required by oVirt
# - create local YUM repository with ovirt-wui and ovirt-host-image-pxe RPMs
# - create oVirt admin appliance

# Requires: createrepo httpd kvm libvirt livecd-tools pungi

ME=$(basename "$0")
warn() { printf "$ME: $@\n" >&2; }
try_h() { printf "Try \`$ME -h' for more information.\n" >&2; }
die() { warn "$@"; try_h; exit 1; }

cd $(dirname $0)
BASE=$(pwd)
FEDORA=9
ARCH=$(uname -i)
HTDOCS=/var/www/html
OVIRT=$HTDOCS/ovirt
PUNGI=$HTDOCS/pungi
PUNGIKS=$PUNGI/pungi.ks
DEP_RPMS="createrepo httpd kvm libvirt livecd-tools pungi"

usage() {
    case $# in 1) warn "$1"; try_h; exit 1;; esac
    cat <<EOF
Usage: $ME [-w] [-n] [-p] [-d|-b] [-a] [-c]
  -w: update oVirt WUI RPMs
  -n: update oVirt Managed Node RPMs
  -p: update pungi repository
  -d: update developer appliance
  -b: update bundled appliance
  -a: updates all (WUI, Node, App), requires -d or -b
  -c: cleanup old repos (pungi and ovirt)
  -h: display this help and exit
EOF
}

update_wui=0 update_node=0
update_pungi=0 update_app=0
cleanup=0
app_type=
err=0 help=0
while getopts wnpdbahc c; do
    case $c in
        w) update_wui=1;;
        n) update_node=1;;
        p) update_pungi=1;;
        d) update_app=1; app_type="-v";;
        b) update_app=1; app_type="-b";;
        a) update_wui=1; update_node=1; update_app=1; update_pungi=1;;
        c) cleanup=1;;
        h) help=1;;
	    '?') err=1; warn "invalid option: \`-$OPTARG'";;
	    :) err=1; warn "missing argument to \`-$OPTARG' option";;
        *) err=1; warn "internal error: \`-$OPTARG' not handled";;
    esac
done
test $err = 1 && { try_h; exit 1; }
test $help = 1 && { usage; exit 0; }
test $update_app = 1 -a -z "$app_type" && usage "Need to specify -d or -b"

if [ $update_node = 1 -o $update_app = 1 ]; then
    test $( id -u ) -ne 0 && die "Node or Application Update must run as root"
fi

set -x

# now make sure the packages we need are installed
rpm -q $DEP_RPMS >& /dev/null
if [ $? -ne 0 ]; then
    # one of the previous packages wasn't installed; bail out
    die "Must have $DEP_RPMS installed"
fi

mkdir -p $PUNGI
mkdir -p $OVIRT

# cleanup repository folders
if [ $cleanup = 1 ]; then
    rm -rf $PUNGI/*
    rm -rf $OVIRT/*
fi

# build ovirt-wui RPM
if [ $update_wui = 1 ]; then
    cd $BASE/wui
    rm -rf rpm-build
    make rpms
    cp rpm-build/ovirt-wui*rpm $OVIRT
    cd $OVIRT
    createrepo .
fi

# build Fedora mirror for oVirt
if [ $update_pungi = 1 ]; then
    cat > $PUNGIKS << EOF
repo --name=f$FEDORA --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=fedora-$FEDORA&arch=\$basearch
repo --name=f$FEDORA-updates --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=updates-released-f$FEDORA&arch=\$basearch

%packages
EOF
    cd $BASE
    grep -hv "^-" ovirt-host-creator/common-pkgs.ks wui-appliance/common-pkgs.ks >> $PUNGIKS
    echo "anaconda-runtime" >> $PUNGIKS
    echo "%end" >> $PUNGIKS
    cd $PUNGI
    pungi --ver=$FEDORA -GCB --nosource  -c $PUNGIKS --force
    restorecon -r .
fi

# If doing either a node or app build, get the default
# network ip address
if [ $update_app = 1 -o $update_node = 1 ]; then
    VIRBR=$(virsh net-dumpxml default | grep "<ip address=" | sed "s/.*ip address='\(.*\)' .*/\1/")
    test -z $VIRBR && die "Could not get ip address of default network for app"
fi

# build oVirt host image
# NOTE: livecd-tools must run as root
if [ $update_node = 1 ]; then
    lokkit --service http
    service libvirtd reload
    cd $BASE/ovirt-host-creator
    rm -rf rpm-build
    cat > repos.ks << EOF
repo --name=f9 --baseurl=http://$VIRBR/pungi/$FEDORA/$ARCH/os

EOF
    make rpms
    cp rpm-build/ovirt-host-image-pxe*rpm $OVIRT
    cd $OVIRT
    createrepo .
fi

# build oVirt admin appliance
# NOTE: create-wui-appliance.sh must be run as root
if [ $update_app == 1 ]; then
    cd $BASE/wui-appliance
    make clean
    cat > repos-x86_64.ks << EOF
url --url http://$VIRBR/pungi/$FEDORA/$ARCH/os
repo --name=ovirt --baseurl=http://$VIRBR/ovirt

EOF
    make
    cp wui-rel-*.ks $OVIRT
    ./create-wui-appliance.sh -t http://$VIRBR/pungi/$FEDORA/$ARCH/os -k http://$VIRBR/ovirt/wui-rel-$ARCH.ks $app_type
    
    echo "oVirt appliance setup started, check progress with:"
    echo "  virt-viewer developer"
fi

set +x
