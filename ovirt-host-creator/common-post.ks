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

die()
{
  echo "$@" 1>&2; failure; echo 1>&2; exit 1
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
. /etc/init.d/ovirt-functions

configure_from_network() {
    DEVICE=$1
    if [ -n "$DEVICE" ]; then
        printf .
        # setup temporary interface to retrieve configuration
        echo "network --device $DEVICE --bootproto dhcp" | nash
        if [ $? -eq 0 ]; then
            printf .
            # from network-scripts/ifup-post
            IPADDR=$(LC_ALL=C ip -o -4 addr ls dev ${DEVICE} | awk '{ print $4 ; exit }')
            eval $(ipcalc --silent --hostname ${IPADDR} ; echo "status=$?")
            if [ "$status" = "0" ]; then
                hostname $HOSTNAME
                # retrieve remote config
                find_srv ovirt tcp
                printf .
                if [ -n "$SRV_HOST" -a -n "$SRV_PORT" ]; then
                    wget --quiet -O - "http://$SRV_HOST:$SRV_PORT/ovirt/cfgdb/$(hostname)" \
                        | augtool > /dev/null 2>&1
                    if [ $? -eq 0 ]; then
                        printf "remote config applied."
                        return
                    fi
                fi
            fi
        fi
    fi
    # default oVirt network configuration:
    # bridge each ethernet device in the system
    ETHDEVS=$(cd /sys/class/net && ls -d eth*)
    for eth in $ETHDEVS; do
        BRIDGE=ovirtbr`echo $eth | cut -b4-`
        printf '%s\n' "DEVICE=$eth" ONBOOT=yes "BRIDGE=$BRIDGE" \
          > /etc/sysconfig/network-scripts/ifcfg-$eth
        printf '%s\n' "DEVICE=$BRIDGE" BOOTPROTO=dhcp \
            ONBOOT=yes TYPE=Bridge PEERNTP=yes \
          > /etc/sysconfig/network-scripts/ifcfg-$BRIDGE
    done
    printf "default config applied."
}

start() {
        # find boot interface from cmdline
        # IPAPPEND 2 in pxelinux.cfg appends e.g. BOOTIF=01-00-16-3e-12-34-57
        BOOTIF=
        for i in $(cat /proc/cmdline); do
            case $i in
                BOOTIF=??-??-??-??-??-??-??)
                    i=${i/#BOOTIF=??-/}
                    BOOTMAC=${i//-/:}
                    BOOTIF=$(grep -l $BOOTMAC /sys/class/net/eth*/address|rev|cut -d/ -f2|rev)
                    ;;
            esac
        done
        configure_from_network $BOOTIF

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
    krb5_conf=/etc/krb5.conf
    if [ ! -s $krb5_conf ]; then
        rm -f $krb5_conf
        # FIXME this is IPA specific
        wget -q http://$SRV_HOST:$SRV_PORT/ipa/config/krb5.ini -O $krb5_conf \
          || die "Failed to get $krb5_conf"
    fi
    IPA_HOST=$SRV_HOST
    IPA_PORT=$SRV_PORT

    find_srv identify tcp
    krb5_tab=/etc/libvirt/krb5.tab
    ovirt-awake start $krb5_tab $SRV_HOST $SRV_PORT

    find_srv collectd tcp
    collectd_conf=/etc/collectd.conf
    if [ -f $collectd_conf.in -a $SRV_HOST -a $SRV_PORT ]; then
        sed -e "s/@COLLECTD_SERVER@/$SRV_HOST/" \
            -e "s/@COLLECTD_PORT@/$SRV_PORT/" $collectd_conf.in \
            > $collectd_conf \
          || die "Failed to write $collectd_conf"
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

echo "Writing ovirt-post init script"
# ovirt startup script to finish init, started after libvirt
cat > /etc/init.d/ovirt-post << \EOF
#!/bin/bash
#
# ovirt Start ovirt services
#
# chkconfig: 3 98 02
# description: ovirt-post services
#

# Source functions library
. /etc/init.d/functions
. /etc/init.d/ovirt-functions

start() {
    echo -n $"Starting ovirt-post: "

    find_srv identify tcp
    ovirt-identify-node -s $SRV_HOST -p $SRV_PORT

    success
    echo
}

case "$1" in
  start)
    start
    ;;
  *)
    echo "Usage: ovirt-post {start}"
    exit 2
esac
EOF

chmod +x /etc/init.d/ovirt-post
chkconfig ovirt-post on

mkdir -p /etc/chkconfig.d
echo "# chkconfig: 345 98 02" > /etc/chkconfig.d/collectd
chkconfig collectd on

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
LoadPlugin load
LoadPlugin interface
LoadPlugin disk

<Plugin libvirt>
        Connection "qemu:///system"
        RefreshInterval "10"
        HostnameFormat "hostname"
</Plugin>

<Plugin network>
        Server "@COLLECTD_SERVER@" @COLLECTD_PORT@
</Plugin>

<Plugin interface>
	Interface "eth0"
	IgnoreSelected false
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

echo "Removing excess RPMs"

# kernel pulls in mkinitrd which pulls in isomd5sum which pulls in python,
# and livecd-tools needs lokkit to disable SELinux.
# However, this is just an install-time dependency; we can remove
# it afterwards, which we do here
rpm -e system-config-firewall-tui system-config-network-tui rhpl \
    rpm-python dbus-python kudzu newt-python newt
rpm -e qemu kpartx mkinitrd isomd5sum dmraid python python-libs

# Sigh.  ntp has a silly dependency on perl because of auxiliary scripts which
# we don't need to use.  Forcibly remove it here
rpm -e --nodeps perl perl-libs perl-Module-Pluggable perl-version \
    perl-Pod-Simple perl-Pod-Escapes

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
  ! -regex ".*/UTC" -exec $RM {} \;
# XXX anaconda/timezone.py does it, missing in imgcreate/kickstart.py
cp /usr/share/zoneinfo/UTC /etc/localtime

$RM /usr/lib/locale
$RM /usr/lib/syslinux
$RM /usr/lib64/gconv
$RM /usr/lib64/pango
$RM /usr/lib64/libpango*
$RM /etc/pango
$RM /usr/bin/pango*

echo "Removing excess kernel modules"
MODULES="/lib/modules/*/kernel"

# the following are lists of kernel modules we are pretty sure we won't need;
# note that these can be single files or whole directories.  They are specified
# starting at $MODULES above; so if you want to remove the NLS stuff from the
# fs subdir, your mods entry would be "fs/nls"
fs_mods="fs/nls fs/9p fs/affs fs/autofs fs/autofs4 fs/befs fs/bfs fs/cifs \
       fs/coda fs/cramfs fs/dlm fs/ecryptfs fs/efs fs/exportfs fs/ext4 \
       fs/freevxfs fs/fuse fs/gfs2 fs/hfs fs/hfsplus fs/jbd fs/jbd2 fs/jffs \
       fs/jffs2 fs/jfs fs/minix fs/ncpfs fs/ocfs2 fs/qnx4 fs/reiserfs \
       fs/romfs fs/sysv fs/udf fs/ufs fs/xfs"

net_mods="net/802 net/8021q net/9p net/appletalk net/atm net/ax25 \
       net/bluetooth net/dccp net/decnet net/ieee80211 net/ipx net/irda \
       net/mac80211 net/netrom net/rfkill net/rose net/sched net/tipc \
       net/wanrouter net/wireless drivers/auxdisplay drivers/net/appletalk \
       drivers/net/hamradio drivers/net/pcmcia drivers/net/tokenring \
       drivers/net/wireless drivers/net/irda drivers/atm drivers/usb/atm"

misc_mods="drivers/bluetooth drivers/firewire drivers/i2c drivers/isdn \
       drivers/media drivers/misc drivers/leds drivers/mtd drivers/w1 sound \
       drivers/input drivers/pcmcia drivers/scsi/pcmcia"

for mods in $fs_mods $net_mods $misc_mods ; do
    $RM $MODULES/$mods
done

echo "Finished Kickstart Post"
