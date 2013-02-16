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
cat > /usr/lib/firewalld/services/ovirt.xml << \EOF
<?xml version="1.0" encoding="utf-8"?>
<service>
  <short>ovirt-node</short>
  <description>This service opens necessary ports for ovirt-node operations</description>
  <!-- libvirt tls -->
  <port protocol="tcp" port="16514"/>
  <!-- guest consoles -->
  <port protocol="tcp" port="5634-6166"/>
  <!-- migration -->
  <port protocol="tcp" port="49152-49216"/>
  <!-- snmp -->
  <port protocol="udp" port="161"/>
</service>
EOF

# enable required services
firewall-offline-cmd -s ssh
firewall-offline-cmd -s ovirt
firewall-offline-cmd -s dhcpv6-client

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
allow setfiles_t net_conf_t:file read;
# Unknown on F18:
#allow setfiles_t initrc_tmp_t:file append;
#allow consoletype_t var_log_t:file append;
#allow passwd_t user_tmp_t:file write;
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
cat > ovirtmount.te << \EOF_OVIRT_MOUNT_TE
policy_module(ovirtmount, 1.0)
gen_require(`
     type mount_t;
')
unconfined_domain(mount_t)
EOF_OVIRT_MOUNT_TE
make NAME=targeted -f /usr/share/selinux/devel/Makefile
semodule -v -i ovirt.pp
semodule -v -i ovirtmount.pp
cd /
rm -rf /tmp/SELinux
echo "-w /etc/shadow -p wa" >> /etc/audit/audit.rules

# Workaround for packages needing /etc/ovirt-node-image-release
ln -s /etc/system-release /etc/ovirt-node-image-release

#Add some upstream specific rwtab entries
cat >> /etc/rwtab.d/ovirt << \EOF_rwtab_ovirt2
dirs    /root/.virt-manager
dirs    /admin/.virt-manager
EOF_rwtab_ovirt2

# create .virt-manager directories for readonly root
mkdir -p /root/.virt-manager /home/admin/.virt-manager

#symlink virt-manager-tui pointer file to .pyc version
sed -i "s/tui.py/tui.pyc/g" /usr/bin/virt-manager-tui

