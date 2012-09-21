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

# systemd configuration
# set default runlevel to multi-user(3)

rm -rf /etc/systemd/system/default.target
ln -sf /lib/systemd/system/multi-user.target /etc/systemd/system/default.target
systemctl enable ovirt-firstboot.service >/dev/null 2>&1

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
#vdsm
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

python -m compileall /usr/share/virt-manager

echo "Configuring SELinux"
# custom module for node specific rules
mkdir /tmp/SELinux
cd /tmp/SELinux
cat > ovirt.te << \EOF_OVIRT_TE
module ovirt 1.0;
require {
    type initrc_t;
    type initrc_tmp_t;
    type mount_t;
    type setfiles_t;
    type shadow_t;
    type unconfined_t;
    type passwd_t;
    type user_tmp_t;
    type var_log_t;
    type consoletype_t;
    type net_conf_t;
    type collectd_t;
    type virt_etc_t;
    type loadkeys_t;
    type initrc_tmp_t;
    class file { append mounton open getattr read execute ioctl lock entrypoint write };
    class fd { use };
    class process { sigchld signull transition noatsecure siginh rlimitinh getattr };
    class fifo_file { getattr open read write append lock ioctl };
    class filesystem getattr;
    class dir { getattr search open read lock ioctl };
    class socket { read write };
    class tcp_socket { read write };
    class udp_socket { read write };
    class rawip_socket { read write };
    class netlink_socket { read write };
    class packet_socket { read write };
    class unix_stream_socket { read write create ioctl getattr lock setattr append bind connect getopt setopt shutdown connectto };
    class unix_dgram_socket { read write };
    class appletalk_socket { read write };
    class netlink_route_socket { read write };
    class netlink_firewall_socket { read write };
    class netlink_tcpdiag_socket { read write };
    class netlink_nflog_socket { read write };
    class netlink_xfrm_socket { read write };
    class netlink_selinux_socket { read write };
    class netlink_audit_socket { read write };
    class netlink_ip6fw_socket { read write };
    class netlink_dnrt_socket { read write };
    class netlink_kobject_uevent_socket { read write };
    class tun_socket { read write };
    class chr_file { getattr read write append ioctl lock open };
    class lnk_file { getattr read };
    class sock_file { getattr write open append };
}
allow mount_t shadow_t:file mounton;
allow setfiles_t initrc_tmp_t:file append;
allow setfiles_t net_conf_t:file read;
allow consoletype_t var_log_t:file append;
allow passwd_t user_tmp_t:file write;
# Unknown on F17 brctl_t:
#allow brctl_t net_conf_t:file read;
# Suppose because of collectd libvirt plugin
allow collectd_t virt_etc_t:file read;
# Suppose because etc is on tmpfs
allow loadkeys_t initrc_tmp_t:file read;

type ovirt_exec_t;
init_daemon_domain(unconfined_t,ovirt_exec_t)
EOF_OVIRT_TE
cat > ovirt.fc << \EOF_OVIRT_FC
/etc/rc\.d/init\.d/ovirt-firstboot             -- gen_context(system_u:object_r:ovirt_exec_t)
/etc/rc\.d/init\.d/ovirt-post             -- gen_context(system_u:object_r:ovirt_exec_t)
EOF_OVIRT_FC
make NAME=targeted -f /usr/share/selinux/devel/Makefile
semodule -v -i ovirt.pp
cd /
rm -rf /tmp/SELinux
echo "-w /etc/shadow -p wa" >> /etc/audit/audit.rules

# Workaround for vdsm needing /etc/ovirt-node-image-release
ln -s /etc/system-release /etc/ovirt-node-image-release
