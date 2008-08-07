#!/bin/bash

#
# build all oVirt components
#
# - create local YUM repository with Fedora subset required by oVirt
# - create local YUM repository with ovirt-wui and ovirt-host-image-pxe RPMs
# - create oVirt admin appliance

# Requires: createrepo httpd kvm libvirt livecd-tools pungi

PATH=$PATH:/sbin:/usr/sbin

ME=$(basename "$0")
warn() { printf "$ME: $@\n" >&2; }
try_h() { printf "Try \`$ME -h' for more information.\n" >&2; }
die() { warn "$@"; try_h; exit 1; }

cd $(dirname $0)
BASE=$(pwd)
F_REL=9
ARCH=$(uname -i)
HTDOCS=/var/www/html
OVIRT=$HTDOCS/ovirt
PUNGI=$HTDOCS/pungi
PUNGIKS=$PUNGI/pungi.ks
DEP_RPMS="createrepo httpd kvm libvirt livecd-tools pungi appliance-tools"

usage() {
    case $# in 1) warn "$1"; try_h; exit 1;; esac
    cat <<EOF
Usage: $ME [-w] [-n] [-p] [-s] [-a] [-c] [-v git|release|none] [-e eth]
  -w: update oVirt WUI RPMs
  -n: update oVirt Managed Node RPMs
  -p: update pungi repository
  -s: include SRPMs and produce source ISO
  -a: updates all (WUI, Node, Appliance)
  -c: cleanup local repos (pungi and ovirt)
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
update_pungi=0 update_app=0
include_src=0
cleanup=0
version_type=git
bridge=
err=0 help=0
while getopts wnpsahcv:e: c; do
    case $c in
        w) update_wui=1;;
        n) update_node=1;;
        p) update_pungi=1;;
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
test $include_src = 1 -a "$update_pungi" = 0 &&
  usage "Need to specify -p when including source"
test "$version_type" != "git" -a "$version_type" != "release" \
    -a "$version_type" != "none" \
    && usage "version type must be git, release or none"

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
set -e
echo -n "pungi-1.2.18.1-1 or newer "
$BASE/ovirt-host-creator/rpm-compare.py GE 0 pungi 1.2.18.1 1
echo ok
echo -n "appliance-tools-002-1 or newer "
$BASE/ovirt-host-creator/rpm-compare.py GE 0 appliance-tools 002 1
echo ok
set +e

mkdir -p $PUNGI
mkdir -p $OVIRT

# cleanup repository folders
if [ $cleanup = 1 ]; then
    update_pungi=1
    rm -rf $PUNGI/*
    rm -rf $OVIRT/*
fi

# If doing either a node or app build, make sure http is running
if [ $update_app = 1 -o $update_node = 1 -o $update_pungi != 0 ]; then
    lokkit --service http
    service httpd status > /dev/null 2>&1 ||
      service httpd start > /dev/null 2>&1
    service libvirtd status > /dev/null 2>&1 ||
      service libvirtd start > /dev/null 2>&1
    service libvirtd reload
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

# build Fedora subset required for oVirt
if [ $update_pungi != 0 ]; then
    pungi_flags="-GC"

    fedora_mirror=http://mirrors.fedoraproject.org/mirrorlist
    # use Fedora + updates
    currentbadupdates=''
    cat > $PUNGIKS << EOF
repo --name=f$F_REL \
  --mirrorlist=$fedora_mirror?repo=fedora-$F_REL&arch=\$basearch
repo --name=f$F_REL-updates \
  --mirrorlist=$fedora_mirror?repo=updates-released-f$F_REL&arch=\$basearch $currentbadupdates
EOF
    # + ovirt.org repo for updates not yet in Fedora
    # + local ovirt repo with locally rebuilt ovirt* RPMs ( options -w and -n )
    #   if not available, ovirt* RPMs from ovirt.org will be used
    excludepkgs=
    if [[ -f $OVIRT/repodata/repomd.xml ]]; then
        excludepkgs='--excludepkgs=ovirt*'
        cat >> $PUNGIKS << EOF
repo --name=ovirt --baseurl=http://localhost/ovirt
EOF
    fi
    cat >> $PUNGIKS << EOF
repo --name=ovirt-org \
  --baseurl=http://ovirt.org/repos/ovirt/$F_REL/\$basearch $excludepkgs
EOF
    if [ $include_src != 0 ]; then
        cat >> $PUNGIKS << EOF
repo --name=f$F_REL-src \
  --mirrorlist=$fedora_mirror?repo=fedora-source-$F_REL&arch=\$basearch
repo --name=f$F_REL-updates-src \
  --mirrorlist=$fedora_mirror?repo=updates-released-source-f$F_REL&arch=\$basearch $currentbadupdates
repo --name=ovirt-org-src \
  --baseurl=http://ovirt.org/repos/ovirt/$F_REL/src $excludepkgs
EOF
    else
        pungi_flags+=" --nosource"
    fi

    cd $BASE
    cat >> $PUNGIKS << EOF

%packages
EOF
    # merge package lists from all oVirt kickstarts
    # exclude ovirt-host-image* (chicken-egg: built at the next step
    # using repo created here)
    egrep -hv "^-|^ovirt-host-image" \
        ovirt-host-creator/common-pkgs.ks \
        wui-appliance/common-pkgs.ks \
        | sort -u >> $PUNGIKS
    cd $PUNGI
    pungi --ver=$F_REL $pungi_flags -c $PUNGIKS --force
    if [ $include_src != 0 ]; then
        pungi --ver=$F_REL -I  --sourceisos --nosplitmedia -c $PUNGIKS --force
    fi
    restorecon -r .
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

    cd $BASE/ovirt-host-creator
    rm -rf rpm-build
    cat > repos.ks << EOF
repo --name=f$F_REL --baseurl=http://localhost/pungi/$F_REL/$ARCH/os
repo --name=ovirt --baseurl=http://localhost/ovirt

EOF
    bumpver
    make rpms
    rm -f $OVIRT/ovirt-host-image*rpm
    cp rpm-build/ovirt-host-image*rpm $OVIRT
    cd $OVIRT
    createrepo .
fi

# build oVirt admin appliance
if [ $update_app == 1 ]; then
    cd $BASE/wui-appliance
    make clean
    cat > repos.ks << EOF
url --url http://localhost/pungi/$F_REL/$ARCH/os
EOF
    excludepkgs=
    if [[ -f $OVIRT/repodata/repomd.xml ]]; then
        excludepkgs='--excludepkgs=ovirt*'
        cat >> repos.ks << EOF
repo --name=ovirt --baseurl=http://localhost/ovirt
EOF
    fi
    cat >> repos.ks << EOF
repo --name=ovirt-org --baseurl=http://ovirt.org/repos/ovirt/$F_REL/$ARCH $excludepkgs

EOF
    make

    bridge_flag=
    if [ -n "$bridge" ]; then
        bridge_flag="-e $bridge"
    fi

    ./create-wui-appliance.sh \
        -k wui-rel.ks \
        $bridge_flag

fi
