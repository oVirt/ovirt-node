#!/bin/bash
#
# oVirt node autotest script
#
# Copyright (C) 2009 Red Hat, Inc.
# Written by Darryl L. Pierce <dpierce@redhat.com>
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

# To include autotesting on the build system, you need to insert the
# following snippet *BEFORE* the text that reads "Output Stages":
# ---8<[begin]---
#  # Integration test
#  {
#    name = integration
#    label = Test group
#    module = Test::AutoBuild::Stage::Test
#    # Don't abort entire cycle if the module test fails
#    critical = 0
#  }
# ---8<[end]---
#
# This will, for each module whose autobuild.sh is run, to have a matching
# autotest.sh to run as well.
#
# To run these tests locally, you will need to open port 69 TCP and UDP and have
# an ISO file.

exit 0

ME=$(basename "$0")
WORKDIR=$(mktemp -d)
warn() { printf '%s: %s\n' "$ME" "$*" >&2; }
die() {  warn "$*"; exit 1; }
debug() { if $debugging; then log "[DEBUG] %s" "$*"; fi }

trap '__st=$?; cleanup_after_testing; exit $__st' 1 2 3 13 15
trap 'cleanup_after_testing' 0

# set -e
# set -u

log () {
    date=$(date)
    printf "${date} $*\n"
}

usage () {
    cat <<EOF
Usage: $ME [-n test_name] [LOGFILE]
  -i: set the ISO filename (defualt: ovirt-node-image.iso)
  -n: the name of the specific autotest to run (default: run all autotests)
  -d: enable more verbose output (default: disabled)
  -t: change the timeout between markers (in ms, default: 120)
  -v: enable tracing (default: disabled)
  -w: launch virt-viewer for each VM (default: no window shown)
  -h: display this help and exit
EOF
}

# $1 - the test function to call
execute_test () {
    local testname=$1

    if [ -z $testname ]; then die "Missing test name"; fi

    log "Executing test: $testname"

    eval $testname

    rc=$?
    log "Completed test: $testname [result=$rc]"

    if [ $rc -ne 0 ]; then
        log "Build fails smoke tests."
    fi

    return $rc
}

# setup a node for pxeboot
# $1 - the working directory
# $2 - kernel arguments; if present then they replace all default flags
setup_pxeboot () {
    local workdir=$1
    local kernelargs=$2
    local pxedefault=$workdir/tftpboot/pxelinux.cfg/default

    debug "setup for pxeboot: isofile=${isofile} workdir=${workdir} kernelargs='${kernelargs}' pxedefault=${pxedefault}"
    (cd $workdir && sudo livecd-iso-to-pxeboot $isofile) > /dev/null 2>&1
    sudo chmod -R 777 $workdir

    # set default kernel arguments if none were provided
    # the defaults boot in standalone mode
    if [ -z "$kernelargs" ]; then
        kernelargs="standalone"
    fi

    local definition="DEFAULT pxeboot"
    definition="${definition}\nTIMEOUT 20"
    definition="${definition}\nPROMPT 0"
    definition="${definition}\nLABEL pxeboot"
    definition="${definition}\n     KERNEL vmlinuz0"
    definition="${definition}\n     IPAPPEND 2"
    definition="${definition}\n     APPEND rootflags=loop initrd=initrd0.img root=/${isoname} rootfstype=auto console=tty0 check console=ttyS0,115200n8 $kernelargs"

    debug "pxeboot definition=\n${definition}"
    sudo bash -c "printf \"${definition}\" > $pxedefault"
}

# Starts a simple instance of dnsmasq.
# $1 - the iface on which dnsmasq works
# $2 - the root for tftp files
# $3 - the mac address for the node (ignored if blank)
# $4 - the nodename
start_dnsmasq () {
    local iface=$1
    local tftproot=$2
    local macaddress=$3
    local nodename=$4
    local pidfile=$2/dnsmasq.pid

    stop_dnsmasq
    debug "Starting dnsmasq"
    dns_startup="sudo /usr/sbin/dnsmasq --read-ethers
                   --dhcp-range=${NETWORK}.100,${NETWORK}.254,255.255.255.0,24h
                   --conf-file=
                   --interface=${iface}
                   --bind-interfaces
                   --except-interface=lo
                   --dhcp-boot=tftpboot/pxelinux.0
                   --enable-tftp
                   --tftp-root=${tftproot}
                   --log-facility=$WORKDIR/dnsmasq-${nodename}.log
                   --log-queries
                   --log-dhcp
                   --pid-file=${pidfile}"
    if [ -n "$macaddress" ]; then
        dns_startup="${dns_startup} --dhcp-host=${macaddress},${NODE_ADDRESS}"
    fi
    # start dnsmasq
    eval $dns_startup
    debug "pidfile=$pidfile"
    DNSMASQ_PID=$(sudo cat $pidfile)
    debug "DNSMASQ_PID=${DNSMASQ_PID}"
}

# Kills the running instance of dnsmasq.
stop_dnsmasq () {
    if [ -n "${DNSMASQ_PID-}" -a "${DNSMASQ_PID-}" != "0" ]; then
        local check=$(ps -ef | awk "/${DNSMASQ_PID}/"' { if ($2 ~ '"${DNSMASQ_PID}"') print $2 }')

        if [[ "${check}" == "${DNSMASQ_PID}" ]]; then
            sudo kill -9 $DNSMASQ_PID
            return
        fi
    fi
    DNSMASQ_PID="0"
}

# Creates a virt network.
# $1 - the node name
# $2 - the network interface name
# $3 - use DHCP (any value)
# $4 - start dnsmsq (def. false)
start_networking () {
    local nodename=$1
    local ifacename=$2
    local use_dhcp=${3-false}
    local start_dnsmasq=${4-false}
    local workdir=$5
    local definition=""
    local network=$NETWORK
    local xmlfile=$WORKDIR/$nodename-$ifacename.xml

    debug "start_networking ()"
    for var in nodename ifacename use_dhcp start_dnsmasq workdir network xmlfile; do
        eval debug "::$var: \$$var"
    done

    definition="<network>\n<name>${ifacename}</name>\n<forward mode='nat' />\n<bridge name='${ifacename}' stp='on' forwardDelay='0' />"
    definition="${definition}\n<ip address='${network}.1' netmask='255.255.255.0'>"
    if $use_dhcp; then
        definition="${definition}\n<dhcp>\n<range start='${network}.100' end='${network}.199' />\n</dhcp>"
    fi
    definition="${definition}\n</ip>\n</network>"

    debug "Saving network definition file to: ${xmlfile}\n"
    sudo printf "${definition}" > $xmlfile
    sudo virsh net-define $xmlfile > /dev/null 2>&1
    debug "Starting network."
    sudo virsh net-start $ifacename > /dev/null 2>&1

    if [ "${use_dhcp}" == "false" ]; then
        if $start_dnsmasq; then
            start_dnsmasq $ifacename $workdir "" $nodename
        fi
    fi
}

# Destroys the test network interface
# $1 - the network name
# $2 - stop dnsmasq (def. false)
stop_networking () {
    local networkname=${1-}
    local stop_dnsmasq=${2-true}

    # if no network was supplied, then check for the global network
    if [ -z "$networkname" ]; then
        networkname=${NETWORK_NAME-}
    fi

    # exit if preserve was enabled
    if $preserve_vm; then return; fi

    if [ -n "${networkname}" ]; then
        debug "Destroying network interface: ${networkname}"
        check=$(sudo virsh net-list --all)
        if [[ "${check}" =~ "${networkname}" ]]; then
            if [[ "{$check}" =~ active ]]; then
                sudo virsh net-destroy $networkname > /dev/null 2>&1
            fi
            sudo virsh net-undefine $networkname > /dev/null 2>&1
        fi
    fi

    if $stop_dnsmasq; then
        stop_dnsmasq
    fi
}

# creates a HD disk file
# $1 - filename for disk file
# $2 - size (##M or ##G)
create_hard_disk () {
    local filename=$1
    local size=$2

    debug "Creating hard disk: filename=${filename} size=${size}"
    sudo qemu-img create -f raw $filename "${size}M" > /dev/null 2>&1
    sudo chcon -t virt_image_t $filename > /dev/null 2>&1
}

# Creates the XML for a virtual machine.
# $1 - the file to write the xml
# $2 - the node name
# $3 - memory size (in kb)
# $4 - boot device
# $5 - the local hard disk (if blank then no disk is used)
# $6 - the cdrom disk (if blank then no cdrom is used)
# $7 - the network bridge (if blank then 'default' is used)
# $8 - optional arguments
define_node () {
    local filename=$1
    local nodename=$2
    local memory=$3
    local boot_device=$4
    local harddrive=$5
    local cddrive=$6
    local bridge=${7-default}
    local options=${8-}
    local result=""

    # flexible options
    # define defaults, then allow the caller to override them as needed
    local arch=$(uname -i)
    local serial="true"
    local vncport="-1"
    local bootdev='hd'

    # first destroy the node
    destroy_node $nodename

    if [ -n "$options" ]; then eval "$options"; fi

    debug "define_node ()"
    for var in filename nodename memory harddrive cddrive bridge options arch serial vncport bootdev; do
eval debug "::$var: \$$var"
    done

    result="<domain type='kvm'>\n<name>${nodename}</name>\n<memory>${memory}</memory>\n <vcpu>1</vcpu>"

    # begin the os section
    # inject the boot device
    result="${result}\n<os>\n<type arch='${arch}' machine='pc'>hvm</type>"
    result="${result}\n<boot dev='${boot_device}' />"
    result="${result}\n</os>"

    # virtual machine features
    result="${result}\n<features>"
    result="${result}\n<acpi />"
    if [ -z "${noapic-}" ]; then result="${result}\n<apic />"; fi
    result="${result}\n<pae /></features>"
    result="${result}\n<clock offset='utc' />"
    result="${result}\n<on_poweroff>destroy</on_poweroff>"
    result="${result}\n<on_reboot>restart</on_reboot>"
    result="${result}\n<on_crash>restart</on_crash>"

    # add devices
    result="${result}\n<devices>"
    # inject the hard disk if defined
    if [ -n "$harddrive" ]; then
        debug "Adding a hard drive to the node"
        result="${result}\n<disk type='file' device='disk'>"
        result="${result}\n<source file='$harddrive' />"
        result="${result}\n<target dev='vda' bus='virtio' />"
        result="${result}\n</disk>"
    fi
    # inject the cdrom drive if defined
    if [ -n "$cddrive" ]; then
        debug "Adding a CDROM drive to the node"
        result="${result}\n<disk type='file' device='cdrom'>"
        result="${result}\n<source file='${cddrive}' />"
        result="${result}\n<target dev='hdc' bus='ide' />"
        result="${result}\n</disk>"
    fi
    # inject the bridge network
    result="${result}\n<interface type='network'>"
    result="${result}\n<source network='${bridge}' />"
    result="${result}\n</interface>"
    # inject the serial port
    if [ -n "$serial" ]; then
        result="${result}\n<serial type='pty' />"
    fi
    # inject the vnc port
    if [ -n "$vncport" ]; then
        result="${result}\n<console type='pty' />"
        result="${result}\n<graphics type='vnc' port='${vncport}' autoport='yes' keyman='en-us' />"
    fi
    # finish the device section
    result="${result}\n</devices>"

    result="${result}\n</domain>"

    debug "Node definition: ${filename}"
    sudo printf "$result" > $filename

    # now define the vm
    sudo virsh define $filename > /dev/null 2>&1

    if [ $? != 0 ]; then die "Unable to define virtual machine: $nodename"; fi
}

# $1 - the node name
# $2 - the boot device (def. "hd")
# $3 - the memory size in kb (def. 524288)
# $4 - hard disk size (if blank then no hard disk)
# $5 - the cd drive image file (if blank then no cd drive)
# $6 - option arguments
configure_node () {
    local nodename=$1
    local boot_device=$2
    local memory=$3
    local hdsize=$4
    local hdfile=""
    local cdfile=$5
    local args=$6
    local nodefile=$WORKDIR/$nodename.xml

    if [ -z "${boot_device}" ]; then boot_device="hd"; fi
    if [ -z "${memory}" ]; then memory="524288"; fi

    debug "configure_node ()"
    for var in nodename boot_device memory hdsize hdfile cdfile args nodefile; do
        eval debug "::$var: \$$var"
    done

    # create the hard disk file
    if [ -n "${hdsize}" ]; then
        hdfile=$WORKDIR/$nodename-hd.img
        create_hard_disk $hdfile $hdsize
    fi

    define_node $nodefile $nodename "${memory}" "${boot_device}" "${hdfile}" "${cdfile}" $IFACE_NAME "${args}"
}

# $1 - the node name
# $2 - undefine the node (def. true)
destroy_node () {
    local nodename=$1
    local undefine=${2-true}

    # if preserving nodes then exit
    if $preserve_vm; then return; fi

    if [ -n "${nodename}" ]; then
        check=$(sudo virsh list --all)
        if [[ "${check}" =~ "${nodename}" ]]; then
            if [[ "${check}" =~ running ]]; then
                sudo virsh destroy $nodename > /dev/null 2>&1
            fi
            if $undefine; then
                sudo virsh undefine $nodename > /dev/null 2>&1
            fi
        fi
    fi
}

# for each test created, add it to the follow array:
tests=''; testcount=0;

# $1 - test name
add_test () {
    tests="${tests} $1"
}

# $1 - node name
start_virt_viewer () {
    local nodename=$1

    sudo virt-viewer $nodename > /dev/null 2>&1&
}

# $1 - the node's name
# $2 - kernel arguments
# $3 - working directory
boot_with_pxe () {
    local nodename=$1
    local kernel_args=$2
    local workdir=$3

    debug "boot_with_pxe ()"
    debug "-      workdir: ${workdir}"
    debug "-     nodename: ${nodename}"
    debug "-  kernel_args: ${kernel_args}"

    setup_pxeboot $workdir "${kernel_args}"

    sudo virsh start $nodename > /dev/null 2>&1
    if $show_viewer; then
        start_virt_viewer $nodename
    fi
}

# $1 - the node's name
boot_from_hd () {
    local nodename=$1

    debug "boot_from_hd ()"
    debug "::nodename: ${nodename}"

    sudo virsh start $nodename > /dev/null 2>&1
    if $show_viewer; then
        start_virt_viewer $nodename
    fi
}

# $1 - the node name
# $2 - the old boot device
# $3 - the new boot device
substitute_boot_device () {
    local nodename=$1
    local old_device=$2
    local new_device=$3
    local new_node_file=$WORKDIR/$nodename-new.xml

    if [ -n "${nodename}" ]; then
        local xml=$(sudo virsh dumpxml $nodename | sed "s/boot dev='"${old_device}"'/boot dev='"${new_device}"'/")

        sudo printf "${xml}" > $new_node_file

        sudo virsh define $new_node_file
    fi
}

add_test "test_stateless_pxe"
test_stateless_pxe () {
    local nodename="${vm_prefix}-stateless-pxe"
    local workdir=$WORKDIR

    start_networking $nodename $IFACE_NAME false true $workdir

    configure_node "${nodename}" "network" "" "10000" "" "local noapic=true"
    boot_with_pxe "${nodename}" "standalone firstboot=no" "${workdir}"

    expect -c '
set timeout '${timeout_period}'

log_file -noappend stateless-pxe.log

spawn sudo virsh console '"${nodename}"'

expect {
    -exact "Linux version"         { send_log "\n\nMarker 1\n\n"; exp_continue }
    -exact "Starting ovirt-early:" { send_log "\n\nMarker 2\n\n"; exp_continue }
    -exact "Starting ovirt:"       { send_log "\n\nMarker 3\n\n"; exp_continue }
    -exact "Starting ovirt-post:"  { send_log "\n\nMarker 4\n\n"; exp_continue }
    -re    "localhost.*login:"     { send_log "\n\nMarker 5\n\n"; exit }
    timeout {
send_log "\nTimeout waiting for marker..\n\n"
exit 1
    } eof {
send_log "Unexpected end of file."
exit 2
    }
}

send_log "\n\nUnexpected end of interaction.\n\n"
exit 3'
    result=$?

    destroy_node $nodename
    stop_networking $IFACE_NAME true

    return $result
}

add_test "test_stateless_pxe_with_nohd"
test_stateless_pxe_with_nohd () {
    local nodename="${vm_prefix}-stateless-pxe-nohd"
    local workdir=$WORKDIR

    start_networking $nodename $IFACE_NAME false true $workdir

    configure_node "${nodename}" "network" "" "" "" "local noapic=true"
    boot_with_pxe "${nodename}" "firstboot=no" "${workdir}"

    expect -c '
set timeout '${timeout_period}'

log_file -noappend stateless-pxe.log

spawn sudo virsh console '"${nodename}"'

expect {
    -exact "Linux version"         { send_log "\n\nMarker 1\n\n"; exp_continue }
    -exact "Starting ovirt-early:" { send_log "\n\nMarker 2\n\n"; exp_continue }
    -exact "Starting ovirt:"       { send_log "\n\nMarker 3\n\n"; exp_continue }
    -exact "Starting ovirt-post:"  { send_log "\n\nMarker 4\n\n"; exp_continue }
    -re    "localhost.*login:"     { send_log "\n\nMarker 5\n\n"; exit }
    timeout {
       send_log "\nTimeout waiting for marker..\n\n"
       exit 1
    } eof {
       send_log "Unexpected end of file."
       exit 2
    }
}

send_log "\n\nUnexpected end of interaction.\n\n"
exit 3'

    result=$?

    destroy_node $nodename
    stop_networking $IFACE_NAME true

    return $result
}

add_test "test_stateful_pxe"
test_stateful_pxe () {
    local nodename="${vm_prefix}-stateful-pxe"
    local workdir=$WORKDIR
    local ipaddress=${NODE_ADDRESS}

    for var in nodename workdir ipaddress; do
        eval debug "::\$$var: $var"
    done

    start_networking $nodename $IFACE_NAME false true $workdir

    configure_node "${nodename}" "network" "" "10000" "" "local noapic=true"
    boot_with_pxe "${nodename}" "standalone storage_init=/dev/vda local_boot ip=${ipaddress}" ${workdir}

    # verify the booting and installation
    expect -c '
set timeout '${timeout_period}'
log_file -noappend stateful-pxe.log

spawn sudo virsh console '"${nodename}"'

expect {
    -exact "Linux version"                     { send_log "\n\nMarker 1\n\n"; exp_continue }
    -exact "Starting ovirt-early:"             { send_log "\n\nMarker 2\n\n"; exp_continue }
    -exact "Starting ovirt:"                   { send_log "\n\nMarker 3\n\n"; exp_continue }
    -exact "Starting ovirt-post:"              { send_log "\n\nMarker 4\n\n"; exp_continue }
    -exact "Starting ovirt-firstpost:"         { send_log "\n\nMarker 5\n\n"; exp_continue }
    -exact "Starting partitioning of /dev/vda" { send_log "\n\nMarker 6\n\n"; exp_continue }
    -exact "Restarting system"                 { send_log "\n\nMarker 7\n\n"; exit }
    timeout {
send_log "\nTimeout waiting for marker..\n\n"
exit 1
    } eof {
send_log "Unexpected end of file."
exit 2
    }
}

send_log "\n\nUnexpected end of interaction.\n\n"
exit 3'
    result=$?

    # only continue if we're in a good state
    if [ $result -eq 0 ]; then
        destroy_node "${nodename}" false
        substitute_boot_device "${nodename}" "network" "hd"
        boot_from_hd  "${nodename}"

        expect -c '
set timeout '${timeout_period}'
log_file stateful-pxe.log

send_log "Restarted node, booting from hard disk.\n"

spawn sudo virsh console '"${nodename}"'

expect {
    -re "localhost.*login:" { send_log "\n\nLogin marker found\n\n"; exit }

    timeout {
send_log "\nMarker not found.\n\n"
exit 1
    } eof {
send_log "Unexpected end of file."
exit 2
    }
}

send_log "\n\nUnexpected end of interaction.\n\n"

exit 3
'

        expect -c '
set timeout 3
log_file stateful-pxe.log

spawn ping -c 3 '"${ipaddress}"'

expect {
    -exact "64 bytes from '"${ipaddress}"'" { send_log "\n\nGot ping response!\n"; send_log "\n\nNetworking verified!\n"; exit }

    timeout {
send_log "\nMarker not found.\n\n"
exit 1
    } eof {
send_log "Unexpected end of file."
exit 2
    }
}

send_log "\n\nUnexpected end of interaction.\n\n"

exit 3'

result=$?
    fi

    destroy_node $nodename
    stop_networking $IFACE_NAME true

    return $result

}

# configures the environment for testing
setup_for_testing () {
    debug "WORKDIR=${WORKDIR}"
    debug "isofile=${isofile}"
    debug "isoname=${isoname}"
    IFACE_NAME=testbr$$
    debug "IFACE_NAME=${IFACE_NAME}"
    NETWORK=192.168.$(echo "scale=0; print $$ % 255" | bc -l)
    debug "NETWORK=${NETWORK}"
    NODE_ADDRESS=$NETWORK.100
    debug "NODE_ADDRESS=${NODE_ADDRESS}"
    DNSMASQ_PID=0
    debug "preserve_vm=${preserve_vm}"
}

# cleans up any loose ends
cleanup_after_testing () {
    debug "Cleaning up"
    stop_dnsmasq
    stop_networking
    # destroy any running vms
    vm_list=$(sudo virsh list --all | awk '/'${vm_prefix}-'/ { print $2 }')
    test -n "$vm_list" && for vm in $vm_list; do
        destroy_node $vm
    done
    stop_networking "${IFACE_NAME}" true

    # do not delete the work directory if preserve was specified
    if $preserve_vm; then return; fi

    rm -rf $WORKDIR
}

# check commandline options
test=''
debugging=false
isofile="${PWD}/ovirt-node-image.iso"
show_viewer=false
vm_prefix="$$"
preserve_vm=false
timeout_period="120"

while getopts di:n:pt:vwh c; do
    case $c in
        d) debugging=true;;
        i) isofile=($OPTARG);;
        n) tests=($OPTARG);;
        p) preserve_vm=true;;
        t) timeout_period=($OPTARG);;
        v) set -v;;
        w) show_viewer=true;;
        h) usage; exit 0;;
        '?') die "invalid option \`-$OPTARG'";;
        :) die "missing argument to \`-$OPTARG' option";;
        *) die "internal error";;
    esac
done

isoname=$(basename $isofile)
isofile="$(cd `dirname $isofile`; pwd)/${isoname}"

if ! [ -s "${isofile}" ]; then
    die "Missing or invalid file: ${isofile}"
fi

shift $(($OPTIND - 1))

set +u
if [ $# -gt 0 -a -n "$1" ]; then RESULTS=$1; else RESULTS=autotest.log; fi
set -u

result_file=$WORKDIR/results.log
debug "result_file=${result_file}"

log "Logging results to file: ${RESULTS}"
{
    setup_for_testing

    log "Begin Testing: ${isoname}"
    log "Tests: ${tests}"
    log "Timeout: ${timeout_period} ms"

    for test in ${tests}; do
        execute_test $test
        result=$?

        cleanup_after_testing

        if [ $result != 0 ]; then
            echo "${result}" > $result_file
            break
        fi
    done

    log "End Testing: ${isoname}"

} | sudo tee --append $RESULTS

if [ -s "$result_file" ]; then
    exit $(cat $result_file)
fi
