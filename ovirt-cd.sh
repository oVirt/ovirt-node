#!/bin/bash

. ./ovirt-common.sh

if [ $# -ne 0 ]; then
    echo "Usage: ovirt-cd.sh"
    exit 1
fi

ISO=`create_iso`
echo $ISO