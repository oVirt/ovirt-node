#!/bin/bash
# -*- mode: shell-script; indent-tabs-mode: nil; sh-basic-offset: 4; -*-
# ex: ts=8 sw=4 sts=4 et filetype=sh

check() {
    return 0
}

depends() {
    return 0
}

install() {
    inst yes
    inst head
    inst awk
    inst dirname
    inst basename

    inst_hook pre-pivot 01 "$moddir/ovirt-cleanup.sh"
    inst_simple "$moddir/ovirt-boot-functions" /sbin/ovirt-boot-functions
}
