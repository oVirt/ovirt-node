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
After=livesys.service plymouth-quit.service
Before=systemd-user-sessions.service

[Service]
Environment=RUNLEVEL=3
ExecStart=/etc/init.d/ovirt-firstboot start
TimeoutSec=0
RemainAfterExit=yes
Type=oneshot
SysVStartPriority=99
StandardInput=tty

[Install]
WantedBy=multi-user.target
EOF_firstboot

systemctl enable ovirt-firstboot.service >/dev/null 2>&1

# force /dev/root to mount read only or systemd will remount as default options
sed -i "s/defaults,noatime/defaults,ro,noatime/g" /etc/fstab
