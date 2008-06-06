#!/bin/bash

#
# build all oVirt components
#
# - create local YUM repository with Fedora subset required by oVirt
# - create local YUM repository with ovirt-wui and ovirt-host-image-pxe RPMs
# - create oVirt admin appliance

# Requires: httpd createrepo pungi libvirt

set -x
cd $(dirname $0)
BASE=$(pwd)
FEDORA=9
ARCH=$(uname -i)
HTDOCS=/var/www/html
OVIRT=$HTDOCS/ovirt
PUNGI=$HTDOCS/pungi
PUNGIKS=$PUNGI/pungi.ks
VIRBR=192.168.122.1

# cleanup repository folders
mkdir -p $PUNGI; rm -rf $PUNGI/*
mkdir -p $OVIRT; rm -rf $OVIRT/*

# build ovirt-wui RPM
cd $BASE/wui
rm -rf rpm-build
make rpms
cp rpm-build/ovirt-wui*rpm $OVIRT
cd $OVIRT
createrepo .

# build Fedora mirror for oVirt
cat > $PUNGIKS << EOF
repo --name=f$FEDORA --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=fedora-$FEDORA&arch=\$basearch
repo --name=f$FEDORA-updates --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=updates-released-f$FEDORA&arch=\$basearch
repo --name=ovirt --baseurl=http://localhost/ovirt

%packages
EOF
cd $BASE
grep -hv "^-" ovirt-host-creator/common-pkgs.ks wui-appliance/common-pkgs.ks >> $PUNGIKS
echo "anaconda-runtime" >> $PUNGIKS
echo "%end" >> $PUNGIKS
cd $PUNGI
pungi --ver=$FEDORA -GCB --nosource  -c $PUNGIKS
restorecon -r .

# build oVirt host image
# NOTE: livecd-tools must run as root
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

# build oVirt admin appliance
cd $BASE/wui-appliance
make clean
cat > repos-x86_64.ks << EOF
url --url http://$VIRBR/pungi/$FEDORA/$ARCH/os
repo --name=ovirt --baseurl=http://$VIRBR/ovirt

EOF
make
cp wui-rel-*.ks $OVIRT
./create-wui-appliance.sh -t http://$VIRBR/pungi/$FEDORA/$ARCH/os -k http://$VIRBR/ovirt/wui-rel-$ARCH.ks -v

set +x

echo "oVirt appliance setup started, check progress with:"
echo "  virt-viewer developer"

