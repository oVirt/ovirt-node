# add RHEV-H rwtab locations
mkdir -p /rhev
cat > /etc/rwtab.d/rhev << EOF_RWTAB_RHEVH
dirs    /var/db
dirs    /var/lib/rhsm
EOF_RWTAB_RHEVH

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
cat > /etc/system-release-cpe <<\EOF_CPE
cpe:/o:redhat:enterprise_linux:6:update2:hypervisor
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
--- rc.sysinit.orig	2012-08-27 12:59:56.181488153 +0530
+++ rc.sysinit	2012-08-27 13:02:45.554484158 +0530
@@ -43,7 +43,7 @@
 fi
 
 if [ -n "$SELINUX_STATE" -a -x /sbin/restorecon ] && __fgrep " /dev " /proc/mounts >/dev/null 2>&1 ; then
-	/sbin/restorecon -R -F /dev 2>/dev/null
+	/sbin/restorecon -e /dev/.initramfs -R /dev 2>/dev/null
 fi
 
 disable_selinux() {
@@ -503,9 +503,9 @@
 # filesystems are NOT unmounted in single user mode.
 # The 'no' applies to all listed filesystem types. See mount(8).
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
