%include version.ks

# add RHEV-H rwtab locations
mkdir -p /rhev
cat > /etc/rwtab.d/rhev << EOF_RWTAB_RHEVH
dirs    /var/db
EOF_RWTAB_RHEVH

# disable lvmetad rhbz#1147217
# Since we can't be sure of what values the LVM developers will use in the
# future or whether they'll comment out configuration and leave it to defaults,
# be as judicious as possible. Current defaults are in the format
# "^\s*#\s*option", so try to match that and strip off the comment if it's
# commented by default
#
# See thin_check_executable in lvm.conf(as of 20140101) for an example of
# possible defaults
#
# Match any whitespace with an optional #, then grab anything after that to
# use as a backreference
sed -ie 's/^\(\s*\)#*\(\s*use_lvmetad\)\s*=\s*[[:digit:]]\+/\1\2 = 0/' \
    /etc/lvm/lvm.conf

enabled=$(grep -q -E '^\s*use_lvmetad = 0$' /etc/lvm/lvm.conf)
if [ -n "$enabled" ]; then
    echo -e "lvmetad not disabled. use_lvmetad appears in lvm.conf at:\n"
    # Grab every instance in the file just in case for for output to see if
    # recommended usage has changed in the comments or the option disappeared
    # or other
    grep -E 'use_lvmetad' /etc/lvm/lvm.conf
    exit 1
fi

systemctl disable lvm2-lvmetad
systemctl disable lvm2-lvmetad.socket

# minimal lsb_release for bz#549147
cat > /usr/bin/lsb_release <<\EOF_LSB
#!/bin/sh
if [ "$1" = "-r" ]; then
    printf "Release:\t$(cat /etc/rhev-hypervisor-release | awk '{print $7}')\n"
else
    echo RedHatEnterpriseVirtualizationHypervisor
fi
EOF_LSB
chmod +x /usr/bin/lsb_release

# CPE name rhbz#593463
MAJORVER=${VERSION%%.*}
MINORVER=${VERSION##*.}
cat > /etc/system-release-cpe <<EOF_CPE
cpe:/o:redhat:enterprise_linux:${MAJORVER}:update${MINORVER}:hypervisor${TYPE}
EOF_CPE

echo "Configuring IPTables"
# here, we need to punch the appropriate holes in the firewall
cat > /etc/sysconfig/iptables << \EOF
# oVirt automatically generated firewall configuration
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
# vdsm
-A INPUT -p tcp --dport 54321 -j ACCEPT
# libvirt tls
-A INPUT -p tcp --dport 16514 -j ACCEPT
# SSH
-A INPUT -p tcp --dport 22 -j ACCEPT
# gluster
-A INPUT -p tcp --dport 24007 -j ACCEPT
-A INPUT -p tcp --dport 24009:24109 -j ACCEPT
# guest consoles
-A INPUT -p tcp -m multiport --dports 5634:6166 -j ACCEPT
# migration
-A INPUT -p tcp -m multiport --dports 49152:49216 -j ACCEPT
# snmp
-A INPUT -p udp --dport 161 -j ACCEPT
#
-A INPUT -j REJECT --reject-with icmp-host-prohibited
-A FORWARD -m physdev ! --physdev-is-bridged -j REJECT --reject-with icmp-host-prohibited
COMMIT
EOF

# configure IPv6 firewall, default is all ACCEPT
cat > /etc/sysconfig/ip6tables << \EOF
# oVirt automatically generated firewall configuration
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p ipv6-icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
# vdsm
-A INPUT -p tcp --dport 54321 -j ACCEPT
# libvirt tls
-A INPUT -p tcp --dport 16514 -j ACCEPT
# SSH
-A INPUT -p tcp --dport 22 -j ACCEPT
# guest consoles
-A INPUT -p tcp -m multiport --dports 5634:6166 -j ACCEPT
# migration
-A INPUT -p tcp -m multiport --dports 49152:49216 -j ACCEPT
# snmp
-A INPUT -p udp --dport 161 -j ACCEPT
# unblock ipv6 dhcp response
-A INPUT -p udp --dport 546 -j ACCEPT
-A INPUT -j REJECT --reject-with icmp6-adm-prohibited
-A FORWARD -m physdev ! --physdev-is-bridged -j REJECT --reject-with icmp6-adm-prohibited
COMMIT
EOF

# remove errors from /sbin/dhclient-script
DHSCRIPT=/sbin/dhclient-script
sed -i 's/mv /cp -p /g'  $DHSCRIPT
sed -i '/rm -f.*${interface}/d' $DHSCRIPT
sed -i '/rm -f \/etc\/localtime/d' $DHSCRIPT
sed -i '/rm -f \/etc\/ntp.conf/d' $DHSCRIPT
sed -i '/rm -f \/etc\/yp.conf/d' $DHSCRIPT

# bz#1128523 - replace dirs with files to keep everything below /var/lib/puppet
sed -ie 's/dirs[ \t]\+\(.*puppet\)//1' /etc/rwtab
echo "files     /var/lib/puppet" >> /etc/rwtab

# bz#1095138 - replace dirs with files to keep everything below /var/lib/nfs
sed -ie '/dirs[ \t].*nfs/ d' /etc/rwtab
echo "files     /var/lib/nfs" >> /etc/rwtab

# rhbz#734478 add virt-who (*.py are removed in rhevh image)
cat > /usr/bin/virt-who <<EOF_virt_who
#!/bin/sh
exec /usr/bin/python /usr/share/virt-who/virt-who.pyc "\$@"
EOF_virt_who

# set maxlogins to 3
echo "*        -       maxlogins      3" >> /etc/security/limits.conf

# dracut config
cat <<_EOF_ > /etc/dracut.conf.d/ovirt-node.conf

add_dracutmodules+="dmsquash-live"

_EOF_
