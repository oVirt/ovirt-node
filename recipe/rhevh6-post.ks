# add RHEV-H rwtab locations
mkdir -p /rhev
mkdir -p /var/cache/rhn
cat > /etc/rwtab.d/rhev << EOF_RWTAB_RHEVH
empty	/rhev
files	/var/cache/rhn
files	/var/lib/vdsm
dirs    /var/db
dirs    /var/lib/rhsm
EOF_RWTAB_RHEVH

# convenience symlinks
ln -s /usr/libexec/ovirt-config-rhn /sbin/rhn_register
ln -s /usr/libexec/ovirt-config-setup /usr/sbin/setup

# in RHEV-H *.py are blacklisted
cat > /etc/cron.d/rhn-virtualization.cron << \EOF_cron-rhn
0-59/2 * * * * root python /usr/share/rhn/virtualization/poller.pyc
EOF_cron-rhn

# minimal lsb_release for vdsm-reg (bz#549147)
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
cat > /etc/system-release-cpe <<\EOF_CPE
cpe:/o:redhat:enterprise_linux:6:update2:hypervisor
EOF_CPE

patch -d /usr/share/rhn/up2date_client -p0 << \EOF_up2date_patch2
--- up2dateErrors.py.orig       2011-07-02 11:06:46.000000000 +0000
+++ up2dateErrors.py    2011-07-02 11:09:19.000000000 +0000
@@ -13,7 +13,20 @@
 _ = t.ugettext
 import OpenSSL
 import config
-from yum.Errors import RepoError
+
+class RepoError(Exception):
+    """
+    Base Yum Error. All other Errors thrown by yum should inherit from
+    this.
+    """
+    def __init__(self, value=None):
+        Exception.__init__(self)
+        self.value = value
+    def __str__(self):
+        return "%s" %(self.value,)
+
+    def __unicode__(self):
+        return '%s' % to_unicode(self.value)
 
 class Error:
     """base class for errors"""
EOF_up2date_patch2
python -m compileall /usr/share/rhn/up2date_client

patch -d /usr/share/rhn/virtualization -p0 << \EOF_rhn_virt
--- poller.py.orig 2011-04-19 15:53:43.000000000 +0000
+++ poller.py 2011-09-08 20:45:49.000000000 +0000
@@ -73,10 +73,9 @@
         return {}

     try:
-        conn = libvirt.open(None)
+        conn = libvirt.openReadOnly(None)
     except libvirt.libvirtError, lve:
         # virConnectOpen() failed
-        sys.stderr.write("Warning: Could not retrieve virtualization information!\n\tlibvirtd service needs to be running.\n")
         conn = None

     if not conn:
@@ -286,10 +285,10 @@
         vdsm_enabled = True

     # Crawl each of the domains on this host and obtain the new state.
-    if vdsm_enabled:
-        domain_list = poll_through_vdsm()
-    elif libvirt:
+    if libvirt:
         domain_list = poll_hypervisor()
+    elif vdsm_enabled:
+        domain_list = poll_through_vdsm()
     else:
         # If no libvirt nor vdsm is present, this program is pretty much
         # useless.  Just exit.
EOF_rhn_virt
python -m compileall /usr/share/rhn/virtualization

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
/etc/rc\.d/init\.d/ovirt-post             -- gen_context(system_u:object_r:ovirt_exec_t)
EOF_OVIRT_FC
make NAME=targeted -f /usr/share/selinux/devel/Makefile
semodule -v -i ovirt.pp
cd /
rm -rf /tmp/SELinux

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

# prevent node from hanging on reboot due to /etc mounts
patch -d /etc/init.d/ -p0 << \EOF_halt
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
EOF_halt

# rhbz#675868
# Modify rc.sysinit
patch -d /etc/rc.d -p0 << \EOF_rc_sysinit
--- rc.sysinit.orig	2011-04-06 09:11:18.126385229 -0400
+++ rc.sysinit	2011-04-06 09:11:04.195923990 -0400
@@ -43,7 +43,7 @@
 fi
 
 if [ -n "$SELINUX_STATE" -a -x /sbin/restorecon ] && __fgrep " /dev " /proc/mounts >/dev/null 2>&1 ; then
-	/sbin/restorecon  -R /dev 2>/dev/null
+	/sbin/restorecon -e /dev/.initramfs -R /dev 2>/dev/null
 fi
 
 disable_selinux() {
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
EOF_rc_sysinit

# rhbz#675868
# Modify start_udev
patch -d /sbin -p0 << \EOF_start_udev
--- start_udev.orig	2011-03-30 12:32:03.000000000 +0000
+++ start_udev	2011-09-02 17:16:57.954610422 +0000
@@ -121,7 +121,7 @@
 	#/bin/chown root:root /dev/fuse
 
 	if [ -x /sbin/restorecon ]; then
-		/sbin/restorecon -R /dev
+		/sbin/restorecon -e /dev/.initramfs -R /dev
 	fi
 
 	if [ -x "$MAKEDEV" ]; then
EOF_start_udev

# semanage is not present in the image and virt_use_nfs is on (see rhbz#642209)
# remove it from vdsmd startup script to avoid error
sed -i 's#/usr/sbin/semanage#/bin/true#' /etc/rc.d/init.d/vdsmd

# libvirtd upstart job is already configured on rhevh
sed -i 's/ && start_libvirtd$//' /etc/rc.d/init.d/vdsmd

# chkconfig results (symlinks) cannnot be peristed
sed -i 's#/sbin/chkconfig \$srv off##' /etc/rc.d/init.d/vdsmd

# reserve vdsm port 54321
augtool << \EOF_sysctl
set /files/etc/sysctl.conf/net.ipv4.ip_local_reserved_ports 54321
save
EOF_sysctl

# rhbz#734478 add virt-who (*.py are removed in rhevh image)
cat > /usr/bin/virt-who <<EOF_virt_who
#!/bin/sh
exec /usr/bin/python /usr/share/virt-who/virt-who.pyc "$@"
EOF_virt_who

# set maxlogins to 3
echo "*        -       maxlogins      3" >> /etc/security/limits.conf

# rhbz#738170
patch -d /sbin -p0 << \EOF_mkdumprd
--- /sbin/mkdumprd.orig	2011-10-06 06:37:49.000000000 +0000
+++ /sbin/mkdumprd	2011-11-01 04:21:19.000000000 +0000
@@ -583,7 +583,7 @@
         eth*.*)
             modalias=8021q
             ;;
-        br*)
+        rhevm|br*)
             modalias=bridge
             ;;
         *)
@@ -756,7 +756,7 @@
             echo >> $MNTIMAGE/etc/ifcfg-$dev
             echo "BUS_ID=\"Bonding\"" >> $MNTIMAGE/etc/ifcfg-$dev
             ;;
-	br*)
+	rhevm|br*)
             for j in `ls /sys/class/net/$dev/brif`
             do
                 handlenetdev $j

EOF_mkdumprd
