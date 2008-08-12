#!/bin/bash

#
# build all oVirt components
# - create oVirt host image (livecd-creator)
# - create local YUM repository with ovirt-wui and ovirt-host-image-pxe RPMs
# - create oVirt admin appliance (appliance-creator)

# Requires: createrepo kvm libvirt livecd-tools appliance-tools

PATH=$PATH:/sbin:/usr/sbin

ME=$(basename "$0")
warn() { printf "$ME: $@\n" >&2; }
try_h() { printf "Try \`$ME -h' for more information.\n" >&2; }
die() { warn "$@"; try_h; exit 1; }

cd $(dirname $0)
BASE=$(pwd)
F_REL=9
ARCH=$(uname -i)
NODE=$BASE/ovirt-host-creator
WUI=$BASE/wui-appliance
BUILD=$BASE/tmp
COMMON=$BASE/common
OVIRT=$BUILD/ovirt
CACHE=$BUILD/cache
DEP_RPMS="createrepo kvm libvirt livecd-tools appliance-tools"

usage() {
    case $# in 1) warn "$1"; try_h; exit 1;; esac
    cat <<EOF
Usage: $ME [-w] [-n] [-s] [-a] [-c] [-v git|release|none] [-e eth]
  -w: update oVirt WUI RPMs
  -n: update oVirt Managed Node RPMs
  -s: include SRPMs and produce source ISO
  -a: updates all (WUI, Node, Appliance)
  -c: cleanup local oVirt repo and YUM cache
  -v: update version type (git, release, none) default is git
  -e: ethernet device to use as bridge (i.e. eth1)
  -h: display this help and exit
EOF
}

bumpver() {
    git checkout version
    if [[ "$version_type" == "git" ]]; then
        make bumpversion
        make bumpgit
    elif [[ "$version_type" == "release" ]]; then
        make bumprelease
    fi
}

update_wui=0 update_node=0
update_app=0
include_src=0
cleanup=0
version_type=git
bridge=
err=0 help=0
while getopts wnsacv:e:h c; do
    case $c in
        w) update_wui=1;;
        n) update_node=1;;
        s) include_src=1;;
        a) update_wui=1; update_node=1; update_app=1;;
        c) cleanup=1;;
        v) version_type=$OPTARG;;
        e) bridge=$OPTARG;;
        h) help=1;;
      '?') err=1; warn "invalid option: \`-$OPTARG'";;
        :) err=1; warn "missing argument to \`-$OPTARG' option";;
        *) err=1; warn "internal error: \`-$OPTARG' not handled";;
    esac
done
test $err = 1 && { try_h; exit 1; }
test $help = 1 && { usage; exit 0; }
test "$version_type" != "git" -a "$version_type" != "release" \
    -a "$version_type" != "none" \
    && usage "version type must be git, release or none"

if [ $update_node = 1 -o $update_app = 1 ]; then
    test $( id -u ) -ne 0 && die "Node or Application Update must run as root"
fi

# now make sure the packages we need are installed
rpm -Uvh http://ovirt.org/repos/ovirt/9/ovirt-release-0.91-1.fc9.noarch.rpm
rpm -q $DEP_RPMS >& /dev/null
if [ $? -ne 0 ]; then
    # one of the previous packages wasn't installed; bail out
    die "Must have $DEP_RPMS installed"
fi
set -e
echo -n "appliance-tools-002-1 or newer "
$COMMON/rpm-compare.py GE 0 appliance-tools 002 1
echo ok
echo -n "livecd-tools-017.1-2ovirt or newer "
$COMMON/rpm-compare.py GE 0 livecd-tools 017.1 2ovirt
echo ok
echo -n "libvirt-0.4.4-2ovirt2 or newer "
$COMMON/rpm-compare.py GE 0 libvirt 0.4.4 2ovirt2
echo ok
echo -n "kvm-72-3ovirt2 or newer "
$COMMON/rpm-compare.py GE 0 kvm 72 3ovirt2
echo ok
if [ $include_src != 0 ]; then
    echo -n "pungi-1.2.18.1-1 or newer "
    $COMMON/rpm-compare.py GE 0 pungi 1.2.18.1 1
    echo ok
fi
set +e

set -x
mkdir -p $OVIRT
mkdir -p $CACHE

# reuse pungi cache from previous build-all.sh versions
PUNGI=/var/cache/pungi
for repo in f9 f9-updates ovirt-org; do
   if [ ! -e "$CACHE/$repo" -a -e "$PUNGI/$repo" ]; then
       cp -a "$PUNGI/$repo" "$CACHE/$repo"
   fi
done

# cleanup repository and YUM cache
if [ $cleanup = 1 ]; then
    rm -rf $OVIRT/*
    rm -rf $CACHE/*
fi


# stop execution on any error
set -e

# build ovirt-wui RPM
if [ $update_wui = 1 ]; then

    cd $BASE/wui
    rm -rf rpm-build
    bumpver
    make rpms
    rm -f $OVIRT/ovirt-wui*rpm
    cp rpm-build/ovirt-wui*rpm $OVIRT

    cd $OVIRT
    createrepo .
fi

fedora_mirror=http://mirrors.fedoraproject.org/mirrorlist
# use Fedora + updates
currentbadupdates=''
cat > $NODE/repos.ks << EOF
repo --name=f$F_REL \
  --mirrorlist=$fedora_mirror?repo=fedora-$F_REL&arch=\$basearch
repo --name=f$F_REL-updates \
  --mirrorlist=$fedora_mirror?repo=updates-released-f$F_REL&arch=\$basearch \
  $currentbadupdates
EOF
# + ovirt.org repo for updates not yet in Fedora
# + local ovirt repo with locally rebuilt ovirt* RPMs ( options -w and -n )
#   if not available, ovirt* RPMs from ovirt.org will be used
excludepkgs=
if [[ -f $OVIRT/repodata/repomd.xml ]]; then
    excludepkgs='--excludepkgs=ovirt*'
    cat >> $NODE/repos.ks << EOF
repo --name=ovirt --baseurl=file://$OVIRT
EOF
fi
cat >> $NODE/repos.ks << EOF
repo --name=ovirt-org \
  --baseurl=http://ovirt.org/repos/ovirt/$F_REL/\$basearch $excludepkgs
EOF

# build sources tarball
if [ $include_src != 0 ]; then
    cat $NODE/repos.ks - > $BUILD/src.ks << EOF
repo --name=f$F_REL-src \
  --mirrorlist=$fedora_mirror?repo=fedora-source-$F_REL&arch=src
repo --name=f$F_REL-updates-src \
  --mirrorlist=$fedora_mirror?repo=updates-released-source-f$F_REL&arch=src \
  $currentbadupdates
repo --name=ovirt-org-src \
  --baseurl=http://ovirt.org/repos/ovirt/$F_REL/src $excludepkgs

%packages --nobase
EOF
    egrep -hv "^-|^ovirt-host-image" \
      $NODE/common-pkgs.ks \
      $WUI/common-pkgs.ks | sort -u >> $BUILD/src.ks
    echo '%end' >> $BUILD/src.ks
    cd $BUILD
    $BASE/common/getsrpms.py $BUILD/src.ks $CACHE
    cd source
    tar cf ovirt-source.tar SRPMS
fi

# build oVirt host image; note that we unconditionally rebuild the
# ovirt-managed-node RPM, since it is now needed for the managed node
# NOTE: livecd-tools must run as root
if [ $update_node = 1 ]; then
    cd $BASE/ovirt-managed-node
    rm -rf rpm-build
    bumpver
    make rpms
    rm -f $OVIRT/ovirt-managed-node*rpm
    cp rpm-build/ovirt-managed-node*rpm $OVIRT
    cd $OVIRT
    createrepo .

    cd $NODE
    rm -rf rpm-build
    bumpver
    make rpms YUMCACHE=$CACHE
    rm -f $OVIRT/ovirt-host-image*rpm
    cp rpm-build/ovirt-host-image*rpm $OVIRT
    cd $OVIRT
    createrepo .
fi

# build oVirt admin appliance
if [ $update_app == 1 ]; then
    cd $WUI
    make clean
    cp $NODE/repos.ks $WUI/repos.ks
    make

    bridge_flag=
    if [ -n "$bridge" ]; then
        bridge_flag="-e $bridge"
    fi

    ./create-wui-appliance.sh -y $CACHE \
        -k wui-rel.ks \
        $bridge_flag

fi
