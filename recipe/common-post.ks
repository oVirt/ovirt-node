# -*-Shell-script-*-
echo "Starting Kickstart Post"
PATH=/sbin:/usr/sbin:/bin:/usr/bin
export PATH

# cleanup rpmdb to allow non-matching host and chroot RPM versions
rm -f /var/lib/rpm/__db*

# Import SELinux Modules
# XXX use targeted, pykickstart selinux directive cannot specify type
# XXX custom module for node specific rules
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
    class file { append mounton open getattr read execute ioctl lock entrypoint };
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
type ovirt_exec_t;
init_daemon_domain(unconfined_t,ovirt_exec_t)
EOF_OVIRT_TE
cat > ovirt.fc << \EOF_OVIRT_FC
/etc/rc\.d/init\.d/ovirt-firstboot             -- gen_context(system_u:object_r:ovirt_exec_t)
EOF_OVIRT_FC
make NAME=targeted -f /usr/share/selinux/devel/Makefile
semodule -v -i ovirt.pp
cd /
rm -rf /tmp/SELinux

# set SELinux booleans
# rhbz#502779 restrict certain memory protection operations
#     keep allow_execmem on for grub
# rhbz#642209 allow virt images on NFS
semanage  boolean -m -S targeted -F /dev/stdin  << EOF_SEMANAGE
allow_execstack=0
virt_use_nfs=1
EOF_SEMANAGE

#echo "Enabling selinux modules"
#SEMODULES="base abrt cgroup consolekit cups dnsmasq guest hal ipsec iscsi \
#kdump kerberos ksmtuned logadm lpd ntp pegasus plymouthd policykit \
#portreserve portmap ppp qpidd rpcbind sasl shutdown snmp sosreport stunnel \
#sysstat unprivuser unconfined unconfineduser usbmodules userhelper \
#vhostmd virt xen qemu"
#lokkit -v --selinuxtype=minimum
#
#tmpdir=$(mktemp -d)
#
#for semodule in $SEMODULES; do
#    found=0
#    pp_file=/usr/share/selinux/minimum/$semodule.pp
#    if [ -f $pp_file.bz2 ]; then
#        bzip2 -dc $pp_file.bz2 > "$tmpdir/$semodule.pp"
#        rm $pp_file.bz2
#        found=1
#    elif [ -f $pp_file ]; then
#        mv $pp_file "$tmpdir"
#        found=1
#    fi
#    # Don't put "base.pp" on the list.
#    test $semodule = base \
#        && continue
#    test $found=1 \
#        && modules="$modules $semodule.pp"
#done
#
#if test -n "$modules"; then
#    (cd "$tmpdir" \
#        && test -f base.pp \
#        && semodule -v -b base.pp -i $modules \
#        && semodule -v -B )
#fi
#rm -rf "$tmpdir"

echo "Running ovirt-install-node-stateless"
/usr/libexec/ovirt-install-node-stateless

echo "Creating shadow files"
# because we aren't installing authconfig, we aren't setting up shadow
# and gshadow properly.  Do it by hand here
pwconv
grpconv

echo "Forcing C locale"
# force logins (via ssh, etc) to use C locale, since we remove locales
cat >> /etc/profile << \EOF
# oVirt: force our locale to C since we don't have locale stuff'
export LC_ALL=C LANG=C
EOF
# unset AUDITD_LANG to prevent boot errors
sed -i '/^AUDITD_LANG*/ s/^/#/' /etc/sysconfig/auditd

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
# libvirt
-A INPUT -p tcp --dport 16509 -j ACCEPT
# SSH
-A INPUT -p tcp --dport 22 -j ACCEPT
# anyterm
-A INPUT -p tcp --dport 81 -j ACCEPT
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
# libvirt
-A INPUT -p tcp --dport 16509 -j ACCEPT
# SSH
-A INPUT -p tcp --dport 22 -j ACCEPT
# anyterm
-A INPUT -p tcp --dport 81 -j ACCEPT
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

if rpm -q --qf '%{release}' ovirt-node | grep -q "^0\." ; then
    echo "Building in developer mode, leaving root account unlocked"
    augtool <<\EOF
set /files/etc/ssh/sshd_config/PermitEmptyPasswords yes
save
EOF
else
    echo "Building in production mode, locking root account"
    passwd -l root
fi

# directories required in the image with the correct perms
# config persistance currently handles only regular files
mkdir -p /root/.ssh
chmod 700 /root/.ssh

# fix iSCSI/LVM startup issue
sed -i 's/node\.session\.initial_login_retry_max.*/node.session.initial_login_retry_max = 60/' /etc/iscsi/iscsid.conf

# root's bash profile
cat >> /root/.bashrc <<EOF
# aliases used for the temporary
function mod_vi() {
  /bin/vi \$@
  restorecon -v \$@
}
alias vi="mod_vi"
alias ping='ping -c 3'
export MALLOC_CHECK_=1
EOF

# Remove the default logrotate daily cron job
# since we run it every 10 minutes instead.
rm -f /etc/cron.daily/logrotate

# comment out /etc/* entries in rwtab to prevent overlapping mounts
touch /var/lib/random-seed
mkdir -p /live
mkdir -p /boot
mkdir -p /rhev
mkdir -p /var/cache/multipathd
sed -i '/^files	\/etc*/ s/^/#/' /etc/rwtab
cat > /etc/rwtab.d/ovirt <<EOF
dirs	/var/lib/multipath
dirs	/var/lib/net-snmp
files	/etc
dirs    /var/lib/dnsmasq
dirs	/root/.uml
files	/var/cache/libvirt
files	/var/empty/sshd/etc/localtime
files	/var/lib/libvirt
files   /var/lib/multipath
files   /var/cache/multipathd
empty	/mnt
empty	/live
empty	/boot
EOF


#use all hard-coded defaults for multipath
cat /dev/null > /etc/multipath.conf

#lvm.conf should use /dev/mapper and /dev/sdX devices
# and not /dev/dm-X devices
sed -i 's/preferred_names = \[ "^\/dev\/mpath\/", "^\/dev\/mapper\/mpath", "^\/dev\/\[hs\]d" \]/preferred_names = \[ "^\/dev\/mapper", "^\/dev\/\[hsv\]d" \]/g' /etc/lvm/lvm.conf

# prevent node from hanging on reboot due to /etc mounts
patch -d /etc/init.d/ -p0 <<\EOF
--- halt.orig	2009-12-05 00:44:29.000000000 +0000
+++ halt	2010-03-24 18:12:36.000000000 +0000
@@ -138,7 +138,7 @@
     $"Unmounting pipe file systems (retry): " \
     -f
 
-LANG=C __umount_loop '$2 ~ /^\/$|^\/proc|^\/dev/{next}
+LANG=C __umount_loop '$2 ~ /^\/$|^\/proc|^\/etc|^\/dev/{next}
 	$3 == "tmpfs" || $3 == "proc" {print $2 ; next}
 	/(loopfs|autofs|nfs|cifs|smbfs|ncpfs|sysfs|^none|^\/dev\/ram|^\/dev\/root$)/ {next}
 	{print $2}' /proc/mounts \
EOF


# prepare for STATE_MOUNT in rc.sysinit
augtool <<\EOF
set /files/etc/sysconfig/readonly-root/TEMPORARY_STATE NOT_OVIRT_FIRSTBOOT
set /files/etc/sysconfig/readonly-root/STATE_LABEL CONFIG
set /files/etc/sysconfig/readonly-root/STATE_MOUNT /config
set /files/etc/sysconfig/readonly-root/READONLY yes
save
EOF
# use persistent state unless firstboot is forced
# XXX auges shellvars lens does not accept this value
sed -i 's@NOT_OVIRT_FIRSTBOOT@$(if cat /proc/cmdline|grep -qv ovirt_firstboot; then printf "yes"; else printf "no"; fi)@' /etc/sysconfig/readonly-root
# prepare mount points for local storage
mkdir -p /boot
mkdir -p /config
mkdir -p /data
mkdir -p /data2
mkdir -p /liveos
mkdir -p /root/.uml
echo "/dev/HostVG/Config /config ext4 defaults,noauto,noatime 0 0" >> /etc/fstab

# prevent node from hanging on reboot due to /etc mounts
patch -d /etc/init.d/ -p0 <<\EOF
--- halt.orig	2011-01-06 13:31:37.808149001 -0500
+++ halt	2011-01-06 13:32:02.604149001 -0500
@@ -138,7 +138,7 @@
     $"Unmounting pipe file systems (retry): " \
     -f
 
-LANG=C __umount_loop '$2 ~ /^\/$|^\/proc|^\/cgroup|^\/sys\/fs\/cgroup|^\/dev/{next}
+LANG=C __umount_loop '$2 ~ /^\/$|^\/proc|^\/cgroup|^\/sys\/fs\/cgroup|^((?!\/etc).)*|^\/dev/{next}
 	$3 == "tmpfs" || $3 == "proc" {print $2 ; next}
 	/(loopfs|autofs|nfs|cifs|smbfs|ncpfs|sysfs|^none|^\/dev\/ram|^\/dev\/root$)/ {next}
 	{print $2}' /proc/mounts \
EOF

patch -d /etc/init.d/ -p0 <<\EOF
--- netfs.orig	2011-02-01 16:41:03.448897000 -0500
+++ netfs	2011-02-01 16:41:51.616897001 -0500
@@ -98,7 +98,8 @@
 	   fi
 	  }
 	touch /var/lock/subsys/netfs
-	action $"Mounting other filesystems: " mount -a -t nonfs,nfs4,cifs,ncpfs,gfs
+	echo "Mounting other filesystems: "
+	mount -a -t nonfs,nfs4,cifs,ncpfs,gfs &> /dev/null
 	;;
   stop)
         # Unmount loopback stuff first
EOF

patch -d /etc/rc.d -p0 <<\EOF
--- rc.sysinit.orig	2011-02-01 12:29:07.208897000 -0500
+++ rc.sysinit	2011-02-02 09:33:06.991739018 -0500
@@ -495,9 +495,11 @@
 # mounted). Contrary to standard usage,
 # filesystems are NOT unmounted in single user mode.
 if [ "$READONLY" != "yes" ] ; then
-	action $"Mounting local filesystems: " mount -a -t nonfs,nfs4,smbfs,ncpfs,cifs,gfs,gfs2 -O no_netdev
+	echo "Mounting local filesystems: "
+	mount -a -t nonfs,nfs4,smbfs,ncpfs,cifs,gfs,gfs2 -O no_netdev &> /dev/null
 else
-	action $"Mounting local filesystems: " mount -a -n -t nonfs,nfs4,smbfs,ncpfs,cifs,gfs,gfs2 -O no_netdev
+	echo "Mounting local filesystems: "
+	mount -a -n -t nonfs,nfs4,smbfs,ncpfs,cifs,gfs,gfs2 -O no_netdev &>/dev/null
 fi
 
 # Update quotas if necessary
EOF

# add admin user for configuration ui
useradd admin
usermod -G wheel admin
usermod -s /usr/libexec/ovirt-admin-shell admin
echo "%wheel	ALL=(ALL)	NOPASSWD: ALL" >> /etc/sudoers

# chkconfig off unnecessary services
chkconfig ovirt off
chkconfig ovirt-awake off

augtool <<\EOF_kdump
set /files/etc/sysconfig/kdump/MKDUMPRD_ARGS --allow-missing
save
EOF

echo 'OPTIONS="-v -Lf /dev/null"' >> /etc/sysconfig/snmpd
cat > /etc/snmp/snmpd.conf <<SNMPCONF_EOF
master agentx
dontLogTCPWrappersConnects yes
rwuser root auth .1
SNMPCONF_EOF

# load modules required by crypto swap
cat > /etc/sysconfig/modules/swap-crypt.modules <<EOF
#!/bin/sh

modprobe aes >/dev/null 2>&1
modprobe dm_mod >/dev/null 2>&1
modprobe dm_crypt >/dev/null 2>&1
modprobe cryptoloop >/dev/null 2>&1
modprobe cbc >/dev/null 2>&1
modprobe sha256 >/dev/null 2>&1

EOF
chmod +x /etc/sysconfig/modules/swap-crypt.modules
#strip out all unncesssary locales
localedef --list-archive | grep -v -i -E 'en_US.utf8' |xargs localedef --delete-from-archive
mv /usr/lib/locale/locale-archive /usr/lib/locale/locale-archive.tmpl
/usr/sbin/build-locale-archive

# rhbz#675868
# Modify rc.sysinit
patch -d /etc/rc.d -p0 <<\EOF
--- rc.sysinit.orig	2011-04-06 09:11:18.126385229 -0400
+++ rc.sysinit	2011-04-06 09:11:04.195923990 -0400
@@ -495,9 +495,9 @@
 # mounted). Contrary to standard usage,
 # filesystems are NOT unmounted in single user mode.
 if [ "$READONLY" != "yes" ] ; then
-	action $"Mounting local filesystems: " mount -a -t nonfs,nfs4,smbfs,ncpfs,cifs,gfs,gfs2 -O no_netdev
+	action $"Mounting local filesystems: " mount -a -t nonfs,nfs4,smbfs,ncpfs,cifs,gfs,gfs2,noproc,nosysfs,nodevpts -O no_netdev
 else
-	action $"Mounting local filesystems: " mount -a -n -t nonfs,nfs4,smbfs,ncpfs,cifs,gfs,gfs2 -O no_netdev
+	action $"Mounting local filesystems: " mount -a -n -t nonfs,nfs4,smbfs,ncpfs,cifs,gfs,gfs2,noproc,nosysfs,nodevpts -O no_netdev
 fi

 # Update quotas if necessary
EOF
