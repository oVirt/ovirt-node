#!/bin/bash -xe
echo "build-artifact.sh"
#this scripts build ovirt-node and ovirt-node-is projects

source ./automation/build-node.sh

rm -rf ../exported-artifacts/*
mkdir -p ../exported-artifacts/
rm -rf "$OVIRT_CACHE_DIR"/ovirt/RPMS/noarch/ovirt-node-plugin-rhn*.rpm
cp "$OVIRT_CACHE_DIR"/ovirt/RPMS/noarch/ovirt-node*.rpm ../exported-artifacts/
