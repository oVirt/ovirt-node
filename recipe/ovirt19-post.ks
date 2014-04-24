# ovirt-install-node-stateless
# ovirt_setup_libvirtd()
    # just to get a boot warning to shut up
    touch /etc/resolv.conf

    # set up qemu daemon to allow outside VNC connections
    sed -i -e 's/^[[:space:]]*#[[:space:]]*\(vnc_listen = "0.0.0.0"\).*/\1/' \
       /etc/libvirt/qemu.conf

    # disable mdns/avahi
    sed -i -e 's/^[[:space:]]*#[[:space:]]*\(mdns_adv = 0\).*/\1/' \
       /etc/libvirt/qemu.conf

#ovirt_setup_anyterm()
   # configure anyterm
   cat >> /etc/sysconfig/anyterm << \EOF_anyterm
ANYTERM_CMD="sudo /usr/bin/virsh console %p"
ANYTERM_LOCAL_ONLY=false
EOF_anyterm

   # permit it to run the virsh console
   echo "anyterm ALL=NOPASSWD: /usr/bin/virsh console *" >> /etc/sudoers

# dracut config
cat <<_EOF_ > /etc/dracut.conf.d/ovirt-node.conf

add_dracutmodules+="dmsquash-live"

_EOF_

# systemd configuration
# set default runlevel to multi-user(3)

rm -rf /etc/systemd/system/default.target
ln -sf /lib/systemd/system/multi-user.target /etc/systemd/system/default.target
systemctl enable ovirt-firstboot.service >/dev/null 2>&1

echo "Configuring IPTables"
# here, we need to punch the appropriate holes in the firewall
# disabled until ovirt-engine supports firewalld

#cat > /usr/lib/firewalld/services/ovirt.xml << \EOF
#<?xml version="1.0" encoding="utf-8"?>
#<service>
#  <short>ovirt-node</short>
#  <description>This service opens necessary ports for ovirt-node operations</description>
#  <!-- libvirt tls -->
#  <port protocol="tcp" port="16514"/>
#  <!-- guest consoles -->
#  <port protocol="tcp" port="5634-6166"/>
#  <!-- migration -->
#  <port protocol="tcp" port="49152-49216"/>
#  <!-- snmp -->
#  <port protocol="udp" port="161"/>
#</service>
#EOF

# enable required services
#firewall-offline-cmd -s ssh
#firewall-offline-cmd -s ovirt
#firewall-offline-cmd -s dhcpv6-client

cat > /etc/sysconfig/iptables << \EOF
# oVirt automatically generated firewall configuration
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
#vdsm
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
echo "-w /etc/shadow -p wa" >> /etc/audit/audit.rules

# Workaround for packages needing /etc/ovirt-node-image-release
ln -s /etc/system-release /etc/ovirt-node-image-release
