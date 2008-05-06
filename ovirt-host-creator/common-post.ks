echo "Starting Kickstart Post"
PATH=/sbin:/usr/sbin:/bin:/usr/bin
export PATH

echo "Setting up Networking"
cat > /etc/sysconfig/iptables << \EOF
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A FORWARD -m physdev --physdev-is-bridged -j ACCEPT
COMMIT
EOF

echo "Writing ovirt-functions script"
# common functions
cat > /etc/init.d/ovirt-functions << \EOF
# -*-Shell-script-*-

find_srv() {
        local dnsreply
        dnsreply=$(dig +short -t srv _$1._$2.$(dnsdomainname))
        if [ $? -eq 0 ]; then
            set _ $dnsreply; shift
            SRV_HOST=$4; SRV_PORT=$3
        else
            SRV_HOST=; SRV_PORT=
        fi
}
EOF

echo "Writing ovirt-early init script"
# next the dynamic bridge setup service
cat > /etc/init.d/ovirt-early << \EOF
#!/bin/bash
#
# ovirt-early Start early ovirt services
#
# chkconfig: 3 01 99
# description: ovirt-early services
#

# Source functions library
. /etc/init.d/functions

start() {

        # find all of the ethernet devices in the system
        ETHDEVS=$(cd /sys/class/net && ls -d eth*)
        for eth in $ETHDEVS; do
            BRIDGE=ovirtbr`echo $eth | cut -b4-`
            printf '%s\n' "DEVICE=$eth" ONBOOT=yes "BRIDGE=$BRIDGE" \
	      > /etc/sysconfig/network-scripts/ifcfg-$eth
            printf '%s\n' "DEVICE=$BRIDGE" BOOTPROTO=dhcp \
                ONBOOT=yes TYPE=Bridge PEERNTP=yes \
              > /etc/sysconfig/network-scripts/ifcfg-$BRIDGE
        done

        # find all of the partitions on the system

        # get the system pagesize
        PAGESIZE=`getconf PAGESIZE`

        # look first at raw partitions
        BLOCKDEVS=`ls /dev/sd? /dev/hd? 2>/dev/null`

        # now LVM partitions
        LVMDEVS="$DEVICES `lvscan | awk '{print $2}' | tr -d \"'\"`"

	SWAPDEVS="$LVMDEVS"
        for dev in $BLOCKDEVS; do
            SWAPDEVS="$SWAPDEVS `fdisk -l $dev 2>/dev/null | tr '*' ' ' \
	                         | awk '$5 ~ /82/ {print $1}'`"
        done

	# now check if any of these partitions are swap, and activate if so
        for device in $SWAPDEVS; do
            sig=`dd if=$device bs=1 count=10 skip=$(( $PAGESIZE - 10 )) \
	         2>/dev/null`
            if [ "$sig" = "SWAPSPACE2" ]; then
                swapon $device
            fi
        done
}

case "$1" in
  start)
        start
        ;;
  *)
        echo "Usage: ovirt-early {start}"
        exit 2
esac
EOF

chmod +x /etc/init.d/ovirt-early
chkconfig ovirt-early on

# just to get a boot warning to shut up
touch /etc/resolv.conf

cat > /etc/dhclient-exit-hooks << \EOF
if [ -n "$new_ntp_servers" ]; then
    for ntp_server in $new_ntp_servers; do
        echo "$ntp_server" >> /etc/ntp/step-tickers
    done
fi
EOF
chmod +x /etc/dhclient-exit-hooks

echo "Writing ovirt init script"
# ovirt startup script to do krb init
cat > /etc/init.d/ovirt << \EOF
#!/bin/bash
#
# ovirt Start ovirt services
#
# chkconfig: 3 11 99
# description: ovirt services
#

# Source functions library
. /etc/init.d/functions
. /etc/init.d/ovirt-functions

start() {
    echo -n $"Starting ovirt: "
    find_srv ipa tcp

    mkdir -p /etc/libvirt
    # here, we wait for the "host-keyadd" service to finish adding our
    # keytab and returning to us; note that we will try 5 times and
    # then give up
    tries=0
    while [ "$VAL" != "SUCCESS" -a $tries -lt 5 ]; do
        VAL=`echo "KERB" | nc $SRV_HOST 6666`
        if [ "$VAL" == "SUCCESS" ]; then
            break
        fi
        tries=$(( $tries + 1 ))
        sleep 1
        echo -n "."
    done

    if [ "$VAL" != "SUCCESS" ]; then
        echo -n "Failed generating keytab" ; failure ; echo ; exit 1
    fi

    if [ ! -s /etc/libvirt/krb5.tab ]; then
        wget -q http://$SRV_HOST:$SRV_PORT/config/$(hostname -i)-libvirt.tab \
	  -O /etc/libvirt/krb5.tab
        if [ $? -ne 0 ]; then
            echo -n "Failed getting keytab" ; failure ; echo ; exit 1
        fi
    fi

    if [ ! -s /etc/krb5.conf ]; then
        rm -f /etc/krb5.conf
        wget -q http://$SRV_HOST:$SRV_PORT/config/krb5.ini -O /etc/krb5.conf
        if [ "$?" -ne 0 ]; then
            echo "Failed getting krb5.conf" ; failure ; echo ; exit 1
        fi
    fi

    find_srv collectd tcp
    if [ -f /etc/collectd.conf.in -a $SRV_HOST -a $SRV_PORT ]; then
        sed -e "s/@COLLECTD_SERVER@/$SRV_HOST/" \
            -e "s/@COLLECTD_PORT@/$SRV_PORT/" /etc/collectd.conf.in \
          > /etc/collectd.conf
        service collectd restart
    fi

    success
    echo
}

case "$1" in
  start)
    start
    ;;
  *)
    echo "Usage: ovirt {start}"
    exit 2
esac
EOF

chmod +x /etc/init.d/ovirt
chkconfig ovirt on

echo "Setting up libvirt interfaces"
# make libvirtd listen on the external interfaces
sed -i -e 's/^#\(LIBVIRTD_ARGS="--listen"\).*/\1/' /etc/sysconfig/libvirtd

echo "Setting up bridged networking"
cat > /etc/kvm-ifup << \EOF
#!/bin/sh

switch=$(ip route list | awk '/^default / { print $NF }')
ifconfig $1 0.0.0.0 up
brctl addif ${switch} $1
EOF

chmod +x /etc/kvm-ifup

echo "Setting up libvirt VNC and networking"
# set up qemu daemon to allow outside VNC connections
sed -i -e 's/^[[:space:]]*#[[:space:]]*\(vnc_listen = "0.0.0.0"\).*/\1/' \
  /etc/libvirt/qemu.conf

# set up libvirtd to listen on TCP (for kerberos)
sed -i -e 's/^[[:space:]]*#[[:space:]]*\(listen_tcp\)\>.*/\1 = 1/' \
       -e 's/^[[:space:]]*#[[:space:]]*\(listen_tls\)\>.*/\1 = 0/' \
  /etc/libvirt/libvirtd.conf

# make sure we don't autostart virbr0 on libvirtd startup
rm -f /etc/libvirt/qemu/networks/autostart/default.xml

# with the new libvirt (0.4.0), make sure we we setup gssapi in the mech_list
if [ `egrep -c '^mech_list: gssapi' /etc/sasl2/libvirt.conf` -eq 0 ]; then
   sed -i -e 's/^\([[:space:]]*mech_list.*\)/#\1/' /etc/sasl2/libvirt.conf
   echo "mech_list: gssapi" >> /etc/sasl2/libvirt.conf
fi

echo "Setting up login screen"
# pretty login screen..

g=$(printf '\33[1m\33[32m')    # similar to g=$(tput bold; tput setaf 2)
n=$(printf '\33[m')            # similar to n=$(tput sgr0)
cat <<EOF > /etc/issue

           888     888 ${g}d8b$n         888
           888     888 ${g}Y8P$n         888
           888     888             888
   .d88b.  Y88b   d88P 888 888d888 888888
  d88''88b  Y88b d88P  888 888P'   888
  888  888   Y88o88P   888 888     888
  Y88..88P    Y888P    888 888     Y88b.
   'Y88P'      Y8P     888 888      'Y888

  Managed node

  Virtualization just got the ${g}Green Light$n

EOF

cp /etc/issue /etc/issue.net

echo "Setting up collectd configuration"
# setup collectd configuration
cat > /etc/collectd.conf.in << \EOF
LoadPlugin logfile
LoadPlugin network
LoadPlugin libvirt
LoadPlugin memory
LoadPlugin cpu

<Plugin libvirt>
        Connection "qemu:///system"
        RefreshInterval "10"
        HostnameFormat "hostname"
</Plugin>

<Plugin network>
        Server "@COLLECTD_SERVER@" @COLLECTD_PORT@
</Plugin>
EOF

echo "Clearing kerberos config"
# remove the /etc/krb5.conf file; it will be fetched on bootup
rm -f /etc/krb5.conf

echo "Creating shadow files"
# because we aren't installing authconfig, we aren't setting up shadow
# and gshadow properly.  Do it by hand here
pwconv
grpconv

echo "Re-creating cracklib dicts"
# cracklib-dicts is 8MB.  We probably don't need to have strict password
# checking on the ovirt host
# unfortunately we can't create an empty cracklib dict, so we create it
# with a single entry "1"
echo 1 | packer >& /dev/null

echo "Forcing C locale"
# force logins (via ssh, etc) to use C locale, since we remove locales
cat >> /etc/profile << \EOF
# oVirt: force our locale to C since we don't have locale stuff'
export LC_ALL=C LANG=C
EOF

# here, remove a bunch of files we don't need that are just eating up space.
# it breaks rpm slightly, but it's not too bad

# FIXME: ug, hard-coded paths.  This is going to break if we change to F-9
# or upgrade certain packages.  Not quite sure how to handle it better

echo "Removing excess RPMs"
# Sigh.  ntp has a silly dependency on perl because of auxiliary scripts which
# we don't need to use.  Forcibly remove it here
rpm -e --nodeps perl perl-libs

# another crappy dependency; rrdtool pulls in dejavu-lgc-fonts for some reason
# remove it here
rpm -e --nodeps dejavu-lgc-fonts

RM="rm -rf"

echo "Removing docs and internationalization"
$RM /usr/share/omf
$RM /usr/share/gnome
$RM /usr/share/doc
$RM /usr/share/locale
$RM /usr/share/libthai
$RM /usr/share/man
$RM /usr/share/terminfo
$RM /usr/share/X11
$RM /usr/share/i18n

find /usr/share/zoneinfo -regextype egrep -type f \
  ! -regex ".*/EST.*|.*/GMT" -exec $RM {} \;

$RM /usr/lib/locale
$RM /usr/lib/syslinux
$RM /usr/lib64/gconv
$RM /usr/lib64/pango
$RM /usr/lib64/libpango*
$RM /etc/pango
$RM /usr/bin/pango*

echo "Removing excess kernel modules"
MODULES="/lib/modules/*/kernel"

$RM $MODULES/sound

fs_mods="9p affs autofs autofs4 befs bfs cifs coda cramfs dlm \
         ecryptfs efs exportfs freevxfs fuse gfs2 hfs hfsplus jbd jbd2 \
         jffs jfs minix ncpfs ocfs2 qnx4 reiserfs romfs sysv udf ufs xfs"
for dir in $fs_mods ; do
   $RM $MODULES/fs/$dir
done

net_mods="802 8021q 9p appletalk atm ax25 bluetooth dccp decnet \
          ieee80211 ipx irda mac80211 netrom rfkill rose sched \
          tipc wanrouter wireless"
for dir in $net_mods ; do
   $RM $MODULES/net/$dir
done

driver_mods="bluetooth firewire i2c isdn media"
for dir in $driver_mods ; do
   $RM $MODULES/drivers/$dir
done

echo "Finished Kickstart Post"
