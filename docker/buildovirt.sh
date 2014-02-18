#!/bin/bash
# oVirt Node ISO build script
#
# Copyright (C) 2014 Red Hat, Inc.
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

cd /ovirt
git clone http://gerrit.ovirt.org/p/ovirt-node.git
git clone http://gerrit.ovirt.org/p/ovirt-node-iso.git

export OVIRT_NODE_BASE=$PWD
OVIRT_CACHE_DIR=/ovirt/ovirt-cache
OVIRT_LOCAL_REPO=file://${OVIRT_CACHE_DIR}/ovirt
export OVIRT_CACHE_DIR
export OVIRT_LOCAL_REPO
BUILD_NUMBER=999

cd ovirt-node
if [[ "$1" == "master" ]]; then
  git checkout master
else
  git fetch $1 && git checkout FETCH_HEAD
fi
make distclean
./autogen.sh --with-image-minimizer 
make iso publish
CONFIGURE_ARGS="--with-recipe=../ovirt-node/recipe"
if [ ! -z $BUILD_NUMBER ]; then
  CONFIGURE_ARGS+=" --with-build-number=$BUILD_NUMBER"
fi
cd ../ovirt-node-iso
rm *.iso
make distclean
./autogen.sh ${CONFIGURE_ARGS}
make rpms
make iso
