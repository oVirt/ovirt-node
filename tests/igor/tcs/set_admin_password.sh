#!/bin/bash

. /usr/libexec/ovirt-functions

PW="ovirt"

unmount_config /etc/passwd /etc/shadow
echo -n $PW | passwd --stdin admin
ovirt_store_config /etc/shadow

exit 0
