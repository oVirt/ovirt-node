#!/bin/bash -xe
echo "check-merged.sh"
#this scripts build ovirt-node and ovirt-node-is projects

source ./automation/build-node.sh

if ! make check-local ; then
    die "Node check failed"
fi