%include version.ks

# add RHEV-H rwtab locations
mkdir -p /rhev
cat > /etc/rwtab.d/rhev << EOF_RWTAB_RHEVH
dirs    /var/db
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
MAJORVER=${VERSION%%.*}
MINORVER=${VERSION##*.}
cat > /etc/system-release-cpe <<EOF_CPE
cpe:/o:redhat:enterprise_linux:${MAJORVER}:update${MINORVER}:hypervisor${TYPE}
EOF_CPE

echo "Installing libvirtd.upstart file"
# https://bugzilla.redhat.com/show_bug.cgi?id=1233059
# We install the file to /etc/init - now we need to copy it into
# place for vdsm. vdsm retrieves the upstart path by querying rpm
LIBVIRT_UPSTART=$(rpm -ql libvirt | grep upstart)
echo "Using ${LIBVIRT_UPSTART}"
mkdir -vp $(dirname ${LIBVIRT_UPSTART})
cp -v /usr/share/ovirt-node/libvirtd.upstart ${LIBVIRT_UPSTART}

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
--- rc.sysinit.orig	2012-09-11 09:41:22.545431354 +0530
+++ rc.sysinit	2012-09-11 09:52:59.619523468 +0530
@@ -43,7 +43,7 @@
 fi

 if [ -n "$SELINUX_STATE" -a -x /sbin/restorecon ] && __fgrep " /dev " /proc/mounts >/dev/null 2>&1 ; then
-	/sbin/restorecon -R -F /dev 2>/dev/null
+	/sbin/restorecon -e /dev/.initramfs -R /dev 2>/dev/null
 fi

 disable_selinux() {
EOF_rc_sysinit

if grep -q 6.6 /etc/system-release; then
    patch -d /etc/rc.d -p0 << \EOF_rc_sysinit
@@ -513,9 +513,9 @@
 # filesystems are NOT unmounted in single user mode.
 # The 'no' applies to all listed filesystem types. See mount(8).
 if [ "$READONLY" != "yes" ] ; then
-	action $"Mounting local filesystems: " mount -a -t nonfs,nfs4,smbfs,ncpfs,cifs,gfs,gfs2,glusterfs -O no_netdev
+	action $"Mounting local filesystems: " mount -a -t nonfs,nfs4,smbfs,ncpfs,cifs,gfs,gfs2,glusterfs,noproc,nosysfs,nodevpts -O no_netdev
 else
-	action $"Mounting local filesystems: " mount -a -n -t nonfs,nfs4,smbfs,ncpfs,cifs,gfs,gfs2i,glusterfs -O no_netdev
+	action $"Mounting local filesystems: " mount -a -n -t nonfs,nfs4,smbfs,ncpfs,cifs,gfs,gfs2i,glusterfs,noproc,nosysfs,nodevpts -O no_netdev
 fi

 # Update quotas if necessary
EOF_rc_sysinit
else
    patch -d /etc/rc.d -p0 << \EOF_rc_sysinit
@@ -497,9 +497,9 @@
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
fi

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

# rhbz#734478 add virt-who (*.py are removed in rhevh image)
cmd_who=""
if [ -f /usr/share/virt-who/virt-who.pyc ]; then
    cmd_who="virt-who.pyc"
elif [ -f /usr/share/virt-who/virtwho.pyc ]; then
    cmd_who="virtwho.pyc"
else
    echo "Couldn't find a known virt-who executable. Please check"
fi

if [ -z $cmd_who ]; then
    echo "Found no virt-who module"
else
    echo "Found virt-who, creating bin"
    cat > /usr/bin/virt-who <<EOF_virt_who
    #!/bin/sh
    exec /usr/bin/python /usr/share/virt-who/$cmd_who "\$@"
EOF_virt_who
    chmod a+x /usr/bin/virt-who
fi

# rhbz 1209350 virt-who keeps using absolute paths to uncompiled
# python files. Change this to the compiled version as well, and
# persist the generated key file

patch -d /bin -p0 << \EOF_virt_who_password
--- virt-who-password      2015-04-07 12:13:41.992000000 -0400
+++ virt-who-password       2015-04-07 12:14:33.909000000 -0400
@@ -1,10 +1,12 @@
 #!/bin/sh

-if [ -f ./virtwhopassword.py ];
+if [ -f ./virtwhopassword.pyc ];
 then
     # Run it from local directory when available
-    exec /usr/bin/python ./virtwhopassword.py "$@"
+    /usr/bin/python ./virtwhopassword.pyc "$@"
 else
     # Run it from /usr/share/virt-who
-    exec /usr/bin/python /usr/share/virt-who/virtwhopassword.py "$@"
+    /usr/bin/python /usr/share/virt-who/virtwhopassword.pyc "$@"
 fi
+
+persist /var/lib/virt-who/key
EOF_virt_who_password

# set maxlogins to 3
echo "*        -       maxlogins      3" >> /etc/security/limits.conf

patch -d /etc/init.d -p0 << \EOF_functions
--- functions.orig	2014-01-03 21:22:50.061036793 -0500
+++ functions	2014-01-03 21:22:06.169959322 -0500
@@ -91,9 +91,9 @@
	remaining=$(LC_ALL=C awk "/^#/ {next} $1" "$2" | sort -r)
	while [ -n "$remaining" -a "$retry" -gt 0 ]; do
		if [ "$retry" -eq 3 ]; then
-			action "$3" fstab-decode umount $remaining
+			action "$3" fstab-decode umount -n $remaining
		else
-			action "$4" fstab-decode umount $5 $remaining
+			action "$4" fstab-decode umount -n $5 $remaining
		fi
		count=4
		remaining=$(LC_ALL=C awk "/^#/ {next} $1" "$2" | sort -r)
EOF_functions

patch -d /sbin -p0 << \EOF_mkdumprd
--- mkdumprd.orig	2014-01-16 08:57:48.002090191 -0500
+++ mkdumprd	2014-01-16 08:58:29.419306913 -0500
@@ -3634,7 +3634,7 @@
                         #test nfs mount and directory creation
                         rlocation=`echo $DUMP_TARGET | sed 's/.*:/'"$remoteip"':/'`
                         tmnt=`mktemp -dq`
-                        kdump_chk "mount -t $USING_METHOD -o nolock -o tcp $rlocation $tmnt" \
+                        kdump_chk "mount -n -t $USING_METHOD -o nolock -o tcp $rlocation $tmnt" \
                                    "Bad NFS mount $DUMP_TARGET"
                         kdump_chk "mkdir -p $tmnt/$SAVE_PATH" "Read only NFS mount $DUMP_TARGET"
                         kdump_chk "touch $tmnt/$SAVE_PATH/testfile" "Read only NFS mount $DUMP_TARGET"
@@ -3645,7 +3645,7 @@
                         available_size=$(df -P $tdir | tail -1 | tr -s ' ' ':' | cut -d: -f5)

                         rm -rf $tdir
-                        umount -f $tmnt
+                        umount -n -f $tmnt
                         if [ $? != 0 ]; then
                             rmdir $tmnt
                             echo "Cannot unmount the temporary directory"
EOF_mkdumprd

