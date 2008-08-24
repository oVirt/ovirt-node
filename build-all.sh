#!/bin/bash

#
# build all oVirt components
# - create oVirt Node image (livecd-creator)
# - create local YUM repository with ovirt-wui and ovirt-host-image-pxe RPMs
# - create oVirt Server Suite appliance (appliance-creator)

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
NAME=ovirt-appliance
IMGDIR=/var/lib/libvirt/images
DEP_RPMS="createrepo kvm libvirt livecd-tools appliance-tools"

usage() {
    case $# in 1) warn "$1"; try_h; exit 1;; esac
    cat <<EOF
Usage: $ME [-w] [-n] [-s] [-a] [-c] [-u] [-q] [-m baseurl] [-v git|release|version|none] [-e eth]
  -w: update oVirt WUI RPMs
  -n: update oVirt Node RPMs
  -s: download SRPMs and produce sources tarball
  -a: updates all (WUI, Node, appliance)
  -c: cleanup local oVirt repo and YUM cache
  -u: update running oVirt appliance
  -m: baseurl of a Fedora mirror, default is to use mirrorlist
      e.g. -m http://download.fedora.redhat.com/pub/fedora/linux
  -v: update version type (git, release, version, none) default is git
  -e: ethernet device to use as bridge (i.e. eth1)
  -q: compress appliance image using qcow2
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
    elif [[ "$version_type" == "version" ]]; then
        make bumpversion
    fi
}

# setup repository URLs
# setup_repos <kickstart include> <badpkg1> <badpkg2>...
# e.g. setup_repos $NODE/repos.ks ruby ruby-libs gtk-vnc\*
setup_repos() {
    local ks_include=$1

    # use Fedora + updates - those marked bad
    currentbadupdates=''
    for p in $@; do
        currentbadupdates="$currentbadupdates --excludepkgs=$p"
    done
    fedora_mirror=http://mirrors.fedoraproject.org/mirrorlist
    printf "repo --name=f$F_REL" > $ks_include
    if [ -n "$fedora_url" ]; then
        cat >> $ks_include << EOF
 --baseurl=$fedora_url/releases/$F_REL/Everything/\$basearch/os
EOF
    else
        cat >> $ks_include << EOF
  --mirrorlist=$fedora_mirror?repo=fedora-$F_REL&arch=\$basearch
EOF
    fi
    printf "repo --name=f$F_REL-updates" >> $ks_include
    if [ -n "$fedora_url" ]; then
        cat >> $ks_include << EOF
  --baseurl=$fedora_url/updates/$F_REL/\$basearch \
  $currentbadupdates
EOF
    else
        cat >> $ks_include << EOF
  --mirrorlist=$fedora_mirror?repo=updates-released-f$F_REL&arch=\$basearch \
  $currentbadupdates
EOF
    fi
    # + ovirt.org repo for updates not yet in Fedora
    # + local ovirt repo with locally rebuilt ovirt* RPMs ( options -w and -n )
    #   if not available, ovirt* RPMs from ovirt.org will be used
    excludepkgs=
    if [[ -f $OVIRT/repodata/repomd.xml ]]; then
        excludepkgs='--excludepkgs=ovirt*'
        cat >> $ks_include << EOF
repo --name=ovirt --baseurl=file://$OVIRT
EOF
    fi
    cat >> $ks_include << EOF
repo --name=ovirt-org \
  --baseurl=http://ovirt.org/repos/ovirt/$F_REL/\$basearch $excludepkgs
EOF
}

update_running_appliance() {
    local rpmfile=$1

    local services_rpm=ovirt-wui
    local services_list='ovirt-mongrel-rails ovirt-host-* ovirt-taskomatic'

    if [ $upload_rpms = 1 ]; then
        pkg=$(basename $rpmfile)
        cat $rpmfile | ssh root@192.168.50.2 \
          "cat > $pkg; yum -y --nogpgcheck localupdate $pkg;
           if [ $pkg != ${pkg#$services_rpm} ]; then
             cd /etc/init.d
             for s in $services_list; do
               if service \$s status > /dev/null; then
                 service \$s restart
               fi
             done
           fi"
    fi
}

update_wui=0
update_node=0
update_app=0
upload_rpms=0
include_src=0
fedora_url=
cleanup=0
version_type=git
bridge=
compress=0
err=0 help=0
while getopts wnsacum:v:e:qh c; do
    case $c in
        w) update_wui=1;;
        n) update_node=1;;
        s) include_src=1;;
        a) update_wui=1; update_node=1; update_app=1;;
        c) cleanup=1;;
        u) upload_rpms=1;;
        m) fedora_url=$OPTARG;;
        v) version_type=$OPTARG;;
        e) bridge=$OPTARG;;
        q) compress=1;;
        h) help=1;;
      '?') err=1; warn "invalid option: \`-$OPTARG'";;
        :) err=1; warn "missing argument to \`-$OPTARG' option";;
        *) err=1; warn "internal error: \`-$OPTARG' not handled";;
    esac
done
test $err = 1 && { try_h; exit 1; }
test $help = 1 && { usage; exit 0; }
test "$version_type" != "git" -a "$version_type" != "release" \
    -a "$version_type" != "none" -a "$version_type" != "version" \
    && usage "version type must be git, release, version or none"

if [ $update_node = 1 -o $update_app = 1 ]; then
    test $( id -u ) -ne 0 && die "Node or Appliance update must run as root"
fi

test $upload_rpms = 1 && "$(virsh domstate $NAME 2> /dev/null)" != "running" \
    && die "oVirt appliance is not running"

# now make sure the packages we need are installed
rpm -q $DEP_RPMS > /dev/null 2>&1
if [ $? -ne 0 ]; then
    # one of the previous packages wasn't installed; bail out
    die "Must have $DEP_RPMS installed"
fi

echo "To get latest RPMs from ovirt.org YUM repo:"
echo "# rpm -Uvh http://ovirt.org/repos/ovirt/9/ovirt-release-0.91-1.fc9.noarch.rpm"
echo "# yum update"
set -e
echo -n "appliance-tools-002-1 or newer "
$COMMON/rpm-compare.py GE 0 appliance-tools 002 1
echo ok
echo -n "livecd-tools-017.1-2ovirt1 or newer "
$COMMON/rpm-compare.py GE 0 livecd-tools 017.1 2ovirt1
echo ok
echo -n "libvirt-0.4.4-2ovirt2 or newer "
$COMMON/rpm-compare.py GE 0 libvirt 0.4.4 2ovirt2
echo ok
echo -n "kvm-72-3ovirt3 or newer "
$COMMON/rpm-compare.py GE 0 kvm 72 3ovirt3
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
    update_running_appliance $OVIRT/ovirt-wui*.noarch.rpm
fi

# build oVirt Node image
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
    make distclean
    setup_repos $NODE/repos.ks
    make rpms YUMCACHE=$CACHE
    rm -f $OVIRT/ovirt-host-image*rpm
    cp rpm-build/ovirt-host-image*rpm $OVIRT
    cd $OVIRT
    createrepo .
    update_running_appliance $OVIRT/ovirt-host-image-pxe*.$ARCH.rpm
fi

# build sources tarball
if [ $include_src != 0 ]; then
    setup_repos $BUILD/src.ks
    printf "repo --name=f$F_REL-src" >> $BUILD/src.ks
    if [ -n "$fedora_url" ]; then
        cat >> $BUILD/src.ks << EOF
 --baseurl=$fedora_url/releases/$F_REL/Everything/source/SRPMS
EOF
    else
        cat >> $BUILD/src.ks << EOF
  --mirrorlist=$fedora_mirror?repo=fedora-source-$F_REL&arch=src
EOF
    fi
    printf "repo --name=f$F_REL-updates-src" >> $BUILD/src.ks
    if [ -n "$fedora_url" ]; then
        cat >> $BUILD/src.ks << EOF
  --baseurl=$fedora_url/updates/$F_REL/SRPMS
  $currentbadupdates
EOF
    else
        cat >> $BUILD/src.ks << EOF
  --mirrorlist=$fedora_mirror?repo=updates-released-source-f$F_REL&arch=src \
  $currentbadupdates
EOF
    fi
    cat >> $BUILD/src.ks << EOF
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

# build oVirt Server Suite appliance
if [ $update_app == 1 ]; then
    cd $WUI
    make distclean
    setup_repos $WUI/repos.ks

    if [ $compress = 1 ]; then
        img_ext=qcow
        make appliance-compressed YUMCACHE=$CACHE NAME=$NAME
    else
        img_ext=raw
        make appliance YUMCACHE=$CACHE NAME=$NAME
    fi

    mv $NAME-sda.$img_ext $IMGDIR/$NAME.img
    restorecon -v $IMGDIR/$NAME.img

    bridge_flag=
    if [ -n "$bridge" ]; then
        bridge_flag="-e $bridge"
    fi

    ./create-wui-appliance.sh -d $IMGDIR -n $NAME $bridge_flag

fi
