# ovirt-install-node-stateless
# ovirt_setup_libvirtd()
    # just to get a boot warning to shut up
    touch /etc/resolv.conf

    # make libvirtd listen on the external interfaces
    sed -i -e 's/^#\(LIBVIRTD_ARGS="--listen"\).*/\1/' \
       /etc/sysconfig/libvirtd

    # set up qemu daemon to allow outside VNC connections
    sed -i -e 's/^[[:space:]]*#[[:space:]]*\(vnc_listen = "0.0.0.0"\).*/\1/' \
       /etc/libvirt/qemu.conf
    # set up libvirtd to listen on TCP (for kerberos)
    sed -i -e "s/^[[:space:]]*#[[:space:]]*\(listen_tcp\)\>.*/\1 = 1/" \
       -e "s/^[[:space:]]*#[[:space:]]*\(listen_tls\)\>.*/\1 = 0/" \
       /etc/libvirt/libvirtd.conf

    # with libvirt (0.4.0), make sure we we setup gssapi in the mech_list
    sasl_conf=/etc/sasl2/libvirt.conf
    if ! grep -qE "^mech_list: gssapi" $sasl_conf ; then
       sed -i -e "s/^\([[:space:]]*mech_list.*\)/#\1/" $sasl_conf
       echo "mech_list: gssapi" >> $sasl_conf
    fi

#ovirt_setup_anyterm()
   # configure anyterm
   cat >> /etc/sysconfig/anyterm << \EOF_anyterm
ANYTERM_CMD="sudo /usr/bin/virsh console %p"
ANYTERM_LOCAL_ONLY=false
EOF_anyterm

   # permit it to run the virsh console
   echo "anyterm ALL=NOPASSWD: /usr/bin/virsh console *" >> /etc/sudoers

# rwtab changes from upstream
patch -d /etc/ -p1 << \EOF_PATCH
diff --git a/rwtab b/rwtab
index cfcb814..7dcb846 100644
--- a/rwtab
+++ b/rwtab
@@ -1,9 +1,7 @@
 dirs	/var/cache/man
 dirs	/var/gdm
 dirs	/var/lib/xkb
-dirs	/var/lock
 dirs	/var/log
-dirs	/var/run
 dirs	/var/puppet
 dirs	/var/lib/dbus
 dirs	/var/lib/nfs
@@ -25,7 +23,6 @@ empty /var/lib/pulse
 empty	/var/lib/ups
 empty	/var/tmp
 empty	/var/tux
-empty	/media

 files	/etc/adjtime
 files	/etc/ntp.conf
EOF_PATCH

# systemd configuration
# set default runlevel to multi-user(3)

rm -rf /etc/systemd/system/default.target
ln -sf /lib/systemd/system/multi-user.target /etc/systemd/system/default.target

# setup ovirt-firstboot multi-user dependency
cat >> /lib/systemd/system/ovirt-firstboot.service << \EOF_firstboot
[Unit]
Description=firstboot configuration program (text mode)
After=plymouth-quit.service
Before=getty@tty1.service

[Service]
Environment=RUNLEVEL=3
ExecStartPre=-/bin/plymouth quit
ExecStart=/etc/init.d/ovirt-firstboot start
TimeoutSec=0
RemainAfterExit=yes
Type=oneshot
SysVStartPriority=99
StandardInput=tty-force

[Install]
WantedBy=multi-user.target
EOF_firstboot

systemctl enable ovirt-firstboot.service >/dev/null 2>&1
chkconfig --del ovirt-firstboot

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
