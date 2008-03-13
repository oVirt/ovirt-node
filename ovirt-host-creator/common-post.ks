cat > /etc/sysconfig/iptables << \EOF
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A FORWARD -m physdev --physdev-is-bridged -j ACCEPT
COMMIT
EOF

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

dhcp_options='subnet-mask
broadcast-address
time-offset
routers
domain-name
domain-name-servers
host-name
nis-domain
nis-servers
ntp-servers
libvirt-auth-method'

        # find all of the ethernet devices in the system
        ETHDEVS=$(cd /sys/class/net && ls -d eth*)
        for eth in $ETHDEVS; do
            BRIDGE=ovirtbr`echo $eth | cut -b4-`
            echo -e "DEVICE=$eth\nONBOOT=yes\nBRIDGE=$BRIDGE" \
	      > /etc/sysconfig/network-scripts/ifcfg-$eth
            echo -e "DEVICE=$BRIDGE\nBOOTPROTO=dhcp\nONBOOT=yes\nTYPE=Bridge" \
	      > /etc/sysconfig/network-scripts/ifcfg-$BRIDGE
	    printf 'DHCLIENTARGS="-R %s"\n' $(printf "$dhcp_options"|tr '\n' ,)\
	      >> /etc/sysconfig/network-scripts/ifcfg-$BRIDGE
        done

        # find all of the partitions on the system

        # get the system pagesize
        PAGESIZE=`getconf PAGESIZE`

        # look first at raw partitions
        BLOCKDEVS=`ls /dev/sd? /dev/hd? 2>/dev/null`

        # now LVM partitions
        LVMDEVS="$DEVICES `/usr/sbin/lvscan | awk '{print $2}' | tr -d \"'\"`"

	SWAPDEVS="$LVMDEVS"
        for dev in $BLOCKDEVS; do
            SWAPDEVS="$SWAPDEVS `/sbin/fdisk -l $dev 2>/dev/null | tr '*' ' ' | awk '$5 ~ /82/ {print $1}' | xargs`"
        done

	# now check if any of these partitions are swap, and activate if so
        for device in $SWAPDEVS; do
            sig=`dd if=$device bs=1 count=10 skip=$(( $PAGESIZE - 10 )) 2>/dev/null`
            if [ "$sig" = "SWAPSPACE2" ]; then
                /sbin/swapon $device
            fi
        done
}

stop() {
        # nothing to do
        return
}

case "$1" in
  start)
        start
        ;;
  stop)
        stop
        ;;
  restart)
        stop
        start
        ;;
  *)
        echo "Usage: ovirt-early {start|stop|restart}"
        exit 2
esac
EOF

chmod +x /etc/init.d/ovirt-early
/sbin/chkconfig ovirt-early on

# just to get a boot warning to shut up
touch /etc/resolv.conf

cat > /etc/dhclient.conf << EOF
option libvirt-auth-method code 202 = text;
EOF

# NOTE that libvirt_auth_method is handled in the exit-hooks
cat > /etc/dhclient-exit-hooks << \EOF
if [ "$interface" = "ovirtbr0" -a -n "$new_libvirt_auth_method" ]; then
    METHOD=`echo $new_libvirt_auth_method | cut -d':' -f1`
    SERVER=`echo $new_libvirt_auth_method | cut -d':' -f2-`
    IP=`echo $new_libvirt_auth_method | cut -d':' -f2 | cut -d'/' -f1`
    if [ $METHOD = "krb5" ]; then
        mkdir -p /etc/libvirt
        # here, we wait for the "host-keyadd" service to finish adding our
        # keytab and returning to us; note that we will try 5 times and
        # then give up
        tries=0
        while [ "$VAL" != "SUCCESS" -a $tries -lt 5 ]; do
            VAL=`echo "KERB" | /usr/bin/nc $IP 6666`
            tries=$(( $tries + 1 ))
            sleep 1
        done
        /usr/bin/wget -q http://$SERVER/$new_ip_address-libvirt.tab -O /etc/libvirt/krb5.tab
        rm -f /etc/krb5.conf ; /usr/bin/wget -q http://$SERVER/krb5.ini -O /etc/krb5.conf
    fi
fi
EOF
chmod +x /etc/dhclient-exit-hooks

# make libvirtd listen on the external interfaces
sed -i -e 's/^#\(LIBVIRTD_ARGS="--listen"\).*/\1/' /etc/sysconfig/libvirtd

cat > /etc/kvm-ifup << \EOF
#!/bin/sh

switch=$(/sbin/ip route list | awk '/^default / { print $NF }')
/sbin/ifconfig $1 0.0.0.0 up
/usr/sbin/brctl addif ${switch} $1
EOF

chmod +x /etc/kvm-ifup

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

# pretty login screen..

g=$(printf '\33[1m\33[32m')    # similar to g=$(tput bold; tput setaf 2)
n=$(printf '\33[m')            # similar to n=$(tput sgr0)
cat <<EOF > /t/i2

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


# setup collectd configuration
cat > /etc/collectd.conf << \EOF
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
        Server "224.0.0.1"
</Plugin>
EOF

# because we aren't installing authconfig, we aren't setting up shadow
# and gshadow properly.  Do it by hand here
/usr/sbin/pwconv
/usr/sbin/grpconv

# here, remove a bunch of files we don't need that are just eating up space.
# it breaks rpm slightly, but it's not too bad

# FIXME: ug, hard-coded paths.  This is going to break if we change to F-9
# or upgrade certain packages.  Not quite sure how to handle it better

# Sigh.  ntp has a silly dependency on perl because of auxiliary scripts which
# we don't need to use.  Forcibly remove it here
rpm -e --nodeps perl perl-libs

# another crappy dependency; rrdtool pulls in dejavu-lgc-fonts for some reason
# remove it here
rpm -e --nodeps dejavu-lgc-fonts

rm -rf /usr/share/omf/fedora-release-notes
rm -rf /usr/share/omf/about-fedora
rm -rf /usr/share/gnome/help/fedora-release-notes
rm -rf /usr/share/gnome/help/about-fedora
rm -rf /usr/share/doc/HTML
rm -rf /usr/share/locale
find /usr/share/i18n/locales -type f ! -iname en_US -exec rm -f {} \;
rm -rf /usr/share/man
rm -rf /usr/lib64/gconv
rm -rf /usr/share/doc
rm -rf /usr/share/X11
rm -f /usr/lib/locale/*
rm -rf /usr/share/terminfo/*
