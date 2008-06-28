#!/bin/bash

SSH_ARGS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -fY"

if [[ $# < 2 ]]; then
    echo "usage: $0 node vm"
    echo "  node: hostname of node to connect to (i.e. node3)"
    echo "  vm  : name of virtual machine on designated node to view"
    exit 1
fi

NODE=$1
VM=$2

ssh $SSH_ARGS 192.168.50.2 virt-viewer -c qemu+tcp://$NODE.priv.ovirt.org/system $VM
