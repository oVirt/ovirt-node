#!/bin/sh

. /sbin/ovirt-boot-functions
if [ "$(basename $0)" = "01ovirt-cleanup.sh" ]; then
    . /lib/dracut-lib.sh
fi


# Check firstboot arg
# accept either ovirt-firstboot or firstboot
# return if =0 or =no
# rhbz#640782 - reinstall is alias for firstboot
# uninstall should trigger cleanup as well
if getarg firstboot >/dev/null; then
    fb=$(getarg firstboot)
elif getarg ovirt_firstboot >/dev/null; then
    fb=$(getarg ovirt_firstboot)
elif getarg reinstall >/dev/null; then
    fb=$(getarg reinstall)
elif getarg uninstall >/dev/null; then
    fb=$(getarg uninstall)
else
    info "No firstboot, reinstall or uninstall parameter found"
    return 0
fi

if [ "$fb" = "no" -o "$fb" = 0 ]; then
    info "firtboot reinstall or uninstall parameter set to 0 or no, exitting"
    return 0
fi
info "Found valid firstboot reinstall or uninstall parameter"

# Check storage_init argument
# Accept either storage_init or ovirt_init
# Prefer storage_init
# Blank entry will result in getting first disk

storage_init="$(getargs storage_init)"
if [ $? -eq 1 ]; then
    storage_init="$(getargs ovirt_init)"
    if [ $? -eq 1 ]; then
        info "storage_init or ovirt_init arguments not found"
    else
        info "Found storage_init:  $storage_init"
    fi
fi

# Check for HostVG
lvm pvscan >/dev/null 2>&1

if [ -z "$storage_init" ]; then
    for hostvg in $(lvm pvs --noheadings -o vg_name,pv_name 2>/dev/null | awk '/^  HostVG/{print $2}'); do
        if [ -z "$storage_init" ]; then
            storage_init="$hostvg"
        else
            storage_init="$hostvg,$storage_init"
        fi
        info "Found HostVG on $hostvg"
    done
fi

# storage_init is passed in a specific format
# A comma separated list of HostVG devices
# then optionally, a comma separated list of AppVG devices
# The two lists are separated by a ';'
# e.g, storage_init=/dev/sda,/dev/sdb;/dev/sdc,/dev/sdd
# would partition sda and sdb as part of HostVG and
# sdc and sdd as part of AppVG
# Since we only care which disks are being used, change to a single list
storage_init="$(echo "$storage_init" | sed 's/;/,/')"
info "Replaced all ';' with ',' : $storage_init"
storage_init="$(echo "$storage_init" | sed 's/\*/\\\*/')"
info "Escaped all asterisks:  $storage_init"

oldIFS=$IFS

IFS=","
for dev in $storage_init; do
    dev="$(echo "$dev" | sed 's/\\\*/\*/g')"
    device=$(IFS=$oldIFS parse_disk_id "$dev")
    info "After parsing \"$dev\", we got \"$device\""
    echo "Wiping LVM from device: ${device}"
    IFS=$oldIFS
    for i in $(lvm pvs --noheadings -o pv_name,vg_name --separator=, $device* 2>/dev/null); do
        pv="${i%%,*}"
        vg="${i##*,}"
        if [ -n "$vg" ]; then
            info "Found and removing vg: $vg"
            yes | lvm vgremove -ff "$vg"
        fi
        info "Found and removing pv: $pv"
        yes | lvm pvremove -ff "$pv"
    done
    IFS=,
done

IFS=$oldIFS

return 0
