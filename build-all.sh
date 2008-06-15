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
FEDORA=9
ARCH=$(uname -i)
HTDOCS=/var/www/html
OVIRT=$HTDOCS/ovirt
PUNGI=$HTDOCS/pungi
PUNGIKS=$PUNGI/pungi.ks
DEP_RPMS="createrepo httpd kvm libvirt livecd-tools pungi-1.2.18.1"

usage() {
    case $# in 1) warn "$1"; try_h; exit 1;; esac
    cat <<EOF
Usage: $ME [-w] [-n] [-p init|update] [-s] [-d|-b] [-a] [-c] [-v git|release|none]
  -w: update oVirt WUI RPMs
  -n: update oVirt Managed Node RPMs
  -p: update pungi repository (init or update)
  -s: include SRPMs and produce source ISO
  -d: update developer appliance
  -b: update bundled appliance
  -a: updates all (WUI, Node, App), requires -d or -b
  -c: cleanup old repos (pungi and ovirt)
  -v: update version type (git, release, none) default is git
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
app_type=
version_type=git
err=0 help=0
while getopts wnp:sdbahcv: c; do
    case $c in
        w) update_wui=1;;
        n) update_node=1;;
        p) update_pungi=$OPTARG;;
        s) include_src=1;;
        d) update_app=1; app_type="-v";;
        b) update_app=1; app_type="-b";;
        a) update_wui=1; update_node=1; update_app=1; update_pungi=init;;
        c) cleanup=1;;
        v) version_type=$OPTARG;;
        h) help=1;;
      '?') err=1; warn "invalid option: \`-$OPTARG'";;
        :) err=1; warn "missing argument to \`-$OPTARG' option";;
        *) err=1; warn "internal error: \`-$OPTARG' not handled";;
    esac
done
test $err = 1 && { try_h; exit 1; }
test $help = 1 && { usage; exit 0; }
test $update_app = 1 -a -z "$app_type" && usage "Need to specify -d or -b"
test $include_src = 1 -a "$update_pungi" = 0 &&
  usage "Need to specify -p when including source"
test "$update_pungi" != 0 -a "$update_pungi" != "init" \
    -a "$update_pungi" != "update" \
    && usage "-p must provide either init or update argument"
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

mkdir -p $PUNGI
mkdir -p $OVIRT

# cleanup repository folders
if [ $cleanup = 1 ]; then
    update_pungi=init
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
    if [[ "$update_pungi" == "init" ]]; then
        pungi_flags="-GCB"
    elif [[ "$update_pungi" == "update" ]]; then
        pungi_flags="-GC"
    fi

    fedora_mirror=http://mirrors.fedoraproject.org/mirrorlist
    # use Fedora + updates
    cat > $PUNGIKS << EOF
repo --name=f$FEDORA \
  --mirrorlist=$fedora_mirror?repo=fedora-$FEDORA&arch=\$basearch
repo --name=f$FEDORA-updates \
  --mirrorlist=$fedora_mirror?repo=updates-released-f$FEDORA&arch=\$basearch
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
  --baseurl=http://ovirt.org/repos/ovirt/$FEDORA/\$basearch $excludepkgs
EOF
    if [ $include_src != 0 ]; then
        cat >> $PUNGIKS << EOF
repo --name=f$FEDORA-src \
  --mirrorlist=$fedora_mirror?repo=fedora-source-$FEDORA&arch=\$basearch
repo --name=f$FEDORA-updates-src \
  --mirrorlist=$fedora_mirror?repo=updates-released-source-f$FEDORA&arch=\$basearch
repo --name=ovirt-org-src \
  --baseurl=http://ovirt.org/repos/ovirt/$FEDORA/src $excludepkgs
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
    cat >> $PUNGIKS << EOF

anaconda-runtime
%end
EOF
    cd $PUNGI
    pungi --ver=$FEDORA $pungi_flags -c $PUNGIKS --force
    if [ $include_src != 0 ]; then
        pungi --ver=$FEDORA -I  --sourceisos --nosplitmedia -c $PUNGIKS --force
    fi
    restorecon -r .
fi

# build oVirt host image
# NOTE: livecd-tools must run as root
if [ $update_node = 1 ]; then
    cd $BASE/ovirt-host-creator
    rm -rf rpm-build
    cat > repos.ks << EOF
repo --name=f$FEDORA --baseurl=http://localhost/pungi/$FEDORA/$ARCH/os

EOF
    bumpver
    make rpms
    rm -f $OVIRT/ovirt-host-image-pxe*rpm
    cp rpm-build/ovirt-host-image-pxe*rpm $OVIRT
    cd $OVIRT
    createrepo .
fi

# build oVirt admin appliance
# NOTE: create-wui-appliance.sh must be run as root
if [ $update_app == 1 ]; then
    # FIXME: This can go away once we have livecd tools building the appliances
    VIRBR=$(virsh net-dumpxml default | grep "<ip address=" | sed "s/.*ip address='\(.*\)' .*/\1/")
    test -z $VIRBR && die "Could not get ip address of default network for app"

    cd $BASE/wui-appliance
    make clean
    cat > repos-x86_64.ks << EOF
url --url http://$VIRBR/pungi/$FEDORA/$ARCH/os
EOF
    excludepkgs=
    if [[ -f $OVIRT/repodata/repomd.xml ]]; then
        excludepkgs='--excludepkgs=ovirt*'
        cat >> repos-x86_64.ks << EOF
repo --name=ovirt --baseurl=http://$VIRBR/ovirt
EOF
    fi
    cat >> repos-x86_64.ks << EOF
repo --name=ovirt-org --baseurl=http://ovirt.org/repos/ovirt/$FEDORA/x86_64 $excludepkgs

EOF
    make
    cp wui-rel-*.ks $OVIRT
    ./create-wui-appliance.sh \
      -t http://$VIRBR/pungi/$FEDORA/$ARCH/os \
      -k http://$VIRBR/ovirt/wui-rel-$ARCH.ks $app_type

    set +x
    echo "oVirt appliance setup started, check progress with:"
    echo -n "  virt-viewer "
    if [[ "$app_type" == "-b" ]]; then
        echo "bundled"
    else
        echo "developer"
    fi

fi
