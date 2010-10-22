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
    type initrc_tmp_t;
    type mount_t;
    type setfiles_t;
    type shadow_t;
    class file { append mounton };
}
allow mount_t shadow_t:file mounton;
allow setfiles_t initrc_tmp_t:file append;
EOF_OVIRT_TE
make NAME=targeted -f /usr/share/selinux/devel/Makefile
semodule -v -i ovirt.pp
cd /
rm -rf /tmp/SELinux

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
# libvirt
-A INPUT -p tcp --dport 16509 -j ACCEPT
# SSH
-A INPUT -p tcp --dport 22 -j ACCEPT
# anyterm
-A INPUT -p tcp --dport 81 -j ACCEPT
# guest consoles
-A INPUT -p tcp -m multiport --dports 5800:6000 -j ACCEPT
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
-A INPUT -p tcp -m multiport --dports 5800:6000 -j ACCEPT
# migration
-A INPUT -p tcp -m multiport --dports 49152:49216 -j ACCEPT
# snmp
-A INPUT -p udp --dport 161 -j ACCEPT
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
mkdir -p /liveos
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

# chkconfig off unnecessary services
chkconfig ovirt off
chkconfig ovirt-awake off

# mkdumprd wants to write to /initrd.XXXX with TMPDIR empty
# this sets it to a writable directory for kdump to start correctly
patch -d /sbin/ -p0 <<\EOF_mkdumprd
--- mkdumprd.orig	2010-06-25 14:39:54.718863880 +0000
+++ mkdumprd	2010-06-25 14:40:25.110785538 +0000
@@ -92,6 +92,7 @@
     exit $1
 }
 
+TMPDIR=/tmp
 # find a temporary directory which doesn't use tmpfs
 if [ -z "$TMPDIR" ]
 then
EOF_mkdumprd

patch -d /etc/rc.d/init.d/ -p0 <<\EOF_kdump
--- kdump.orig	2010-06-25 16:06:17.019233645 -0400
+++ kdump	2010-06-25 16:06:48.342171474 -0400
@@ -68,7 +68,7 @@
 		# to figure out if anything has changed
 		touch /etc/kdump.conf
 	else
-		MKDUMPRD="/sbin/mkdumprd -d -f"
+		MKDUMPRD="/sbin/mkdumprd -d -f --allow-missing"
 	fi
 
 	if [ -z "$KDUMP_KERNELVER" ]; then
@@ -138,7 +138,7 @@
                         echo -n "  "; echo "$modified_files" | sed 's/\s/\n  /g'
                 fi
                 echo "Rebuilding $kdump_initrd"
-                /sbin/mkdumprd -d -f $kdump_initrd $kdump_kver
+                /sbin/mkdumprd -d -f $kdump_initrd $kdump_kver --allow-missing
                 if [ $? != 0 ]; then
                         echo "Failed to run mkdumprd"
                         $LOGGER "mkdumprd: failed to make kdump initrd"
EOF_kdump

echo 'OPTIONS="-v -Lf /dev/null"' >> /etc/sysconfig/snmpd
cat > /etc/snmp/snmpd.conf <<SNMPCONF_EOF
master agentx
dontLogTCPWrappersConnects yes
rwuser root auth .1
SNMPCONF_EOF

