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
systemctl enable ovirt-kdump.service >/dev/null 2>&1

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

