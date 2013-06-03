#!/bin/sh
#oVirt node autobuild script
#
# Copyright (C) 2008 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.

echo "Running oVirt Node Autobuild"

set -e
set -v

if grep -q "DISTCVS Specfile" ovirt-node.spec; then
    cp ovirt-node.spec distcvs.ovirt-node.spec
fi

test -f Makefile && make -k distclean || :

OVIRT_CACHE_DIR=${AUTOBUILD_SOURCE_ROOT-${HOME}}/ovirt-cache
if [ -n "$AUTOBUILD_PACKAGE_ROOT" ]; then
    OVIRT_LOCAL_DIR=${AUTOBUILD_PACKAGE_ROOT}/rpm/RPMS
else
    OVIRT_LOCAL_DIR=${HOME}/rpmbuild/RPMS/noarch
fi
OVIRT_LOCAL_REPO=file://${OVIRT_LOCAL_DIR}
export OVIRT_LOCAL_REPO OVIRT_CACHE_DIR

rm -f ${OVIRT_LOCAL_DIR}/ovirt-node-*
./autogen.sh --prefix=$AUTOBUILD_INSTALL_ROOT --with-image-minimizer
make
make install

if [ -e distcvs.ovirt-node.spec ]; then
    mv distcvs.ovirt-node.spec ovirt-node.spec
fi

rm -f *.tar.gz
make dist

if [ -f /usr/bin/rpmbuild ]; then
  if [ -n "$AUTOBUILD_COUNTER" ]; then
    EXTRA_RELEASE=".auto$AUTOBUILD_COUNTER"
  else
    NOW=`date +"%s"`
    EXTRA_RELEASE=".$USER$NOW"
  fi
  rpmbuild --nodeps --define "extra_release $EXTRA_RELEASE" -ta --clean *.tar.gz
fi

mkdir -p ${OVIRT_LOCAL_DIR}
# regenerate repo so iso uses new ovirt-node rpms
createrepo -d ${OVIRT_LOCAL_DIR}

cd recipe
make ovirt-node-image.iso 

if ! ls *.iso 2>/dev/null >/dev/null; then
    echo "ISO not created"
    exit 1
fi

#
#copy iso back to main directory for autotest.sh
ln -nf *iso .. ||:

#Don't error out if this doesn't work.
set +e
TMPDIR=$(mktemp -d)
sudo mount -o loop ovirt-node-image.iso $TMPDIR
cp $TMPDIR/isolinux/manifest-srpm.txt ..
cp $TMPDIR/isolinux/manifest-rpm.txt ..
cp $TMPDIR/isolinux/manifest-file.txt.bz2 ..
sudo umount $TMPDIR
rmdir $TMPDIR

cd ..
echo "======================================================" > ovirt-node-image.mini-manifest
echo "Package info in ovirt-node-image.iso" >> ovirt-node-image.mini-manifest
echo "======================================================" >> ovirt-node-image.mini-manifest
egrep '^kernel|kvm|^ovirt-node|libvirt' manifest-srpm.txt | \
sed 's/\.src\.rpm//' >> ovirt-node-image.mini-manifest

# Add additional information to mini-manifest
# Check size of iso and report in mini-manifest
echo "======================================================" >> ovirt-node-image.mini-manifest
size=$(readlink ovirt-node-image.iso | xargs ls -l | awk '{print $5}')
human_size=$(readlink ovirt-node-image.iso | xargs ls -lh | awk '{print $5}')
echo "    Iso Size:  $size  ($human_size)" >> ovirt-node-image.mini-manifest

html_location=/var/www/html/builder/$(basename $(dirname ${AUTOBUILD_SOURCE_ROOT}))
old_size=""
old_human_size=""
if [ -e ${html_location}/artifacts/${AUTOBUILD_MODULE}/ovirt-node-image.iso ]; then
    old_size=$(ls -l ${html_location}/artifacts/${AUTOBUILD_MODULE}/ovirt-node-image.iso | awk '{print $5}')
    old_human_size=$(ls -lh ${html_location}/artifacts/${AUTOBUILD_MODULE}/ovirt-node-image.iso | awk '{print $5}')
    let size_diff=(size-old_size)/1024
    echo "Old Iso Size:  $old_size  ($old_human_size) delta[kB] $size_diff" >> ovirt-node-image.mini-manifest
else
    echo "No old iso found for compairson">> ovirt-node-image.mini-manifest
fi
# md5 and sha256sums
echo "MD5SUM:  $(md5sum ovirt-node-image.iso |awk '{print $1}')" >> ovirt-node-image.mini-manifest
echo "SHA256SUM:  $(sha256sum ovirt-node-image.iso |awk '{print $1}')" >> ovirt-node-image.mini-manifest

echo "======================================================" >> ovirt-node-image.mini-manifest
echo "livecd-tools version:  $(rpm -qa livecd-tools)" >> ovirt-node-image.mini-manifest
