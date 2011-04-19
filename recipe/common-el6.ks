# add RHEV-H rwtab locations
mkdir -p /rhev
mkdir -p /var/cache/rhn
mkdir -p /boot-kdump
cat > /etc/rwtab.d/rhev <<EOF_RWTAB
empty	/rhev
files	/root/.ssh
files	/var/cache/rhn
files	/var/lib/vdsm
files	/boot-kdump
EOF_RWTAB

# convenience symlinks
ln -s /usr/libexec/ovirt-config-rhn /sbin/rhn_register
ln -s /usr/libexec/ovirt-config-setup /usr/sbin/setup

# disable SSH password auth by default
augtool <<EOF_SSHD_CONFIG
set /files/etc/ssh/sshd_config/PasswordAuthentication no
save
EOF_SSHD_CONFIG

# use static RPC ports, to avoid collision with VDSM port
augtool <<EOF_NFS
set /files/etc/sysconfig/nfs/RQUOTAD_PORT 875
set /files/etc/sysconfig/nfs/LOCKD_TCPPORT 32803
set /files/etc/sysconfig/nfs/LOCKD_UDPPORT 32769
set /files/etc/sysconfig/nfs/MOUNTD_PORT 892
set /files/etc/sysconfig/nfs/STATD_PORT 662
set /files/etc/sysconfig/nfs/STATD_OUTGOING_PORT 2020
save
EOF_NFS

cat >> /etc/rc.d/rc.local <<\EOF_RC_LOCAL
. /usr/libexec/ovirt-functions

# successfull boot from /dev/HostVG/Root
if grep -q -w root=live:LABEL=Root /proc/cmdline; then
    # set first boot entry as permanent default
    ln -snf /dev/.initramfs/live/grub /boot/grub
    mount -o rw,remount LABEL=Root /dev/.initramfs/live > /tmp/grub-savedefault.log 2>&1
    echo "savedefault --default=0" | grub >> /tmp/grub-savedefault.log 2>&1
    mount -o ro,remount LABEL=Root /dev/.initramfs/live >> /tmp/grub-savedefault.log 2>&1
fi

# remove old persisted lvm.conf
if is_persisted /etc/lvm/lvm.conf; then
  remove_config /etc/lvm/lvm.conf
  # should be only one, loop just in case
  for rpmnew in /etc/lvm/lvm.conf.rpmnew-*
  do
    cp -pv "$rpmnew" /etc/lvm/lvm.conf
  done
  pvscan
fi
EOF_RC_LOCAL

# rhbz#504907 selinux context for bind-mounted files and directories
# setfiles must not run on bind-mount source,
# to preserve the original selinux context of the mount target
#+FILESYSTEMSRW=`mount | grep -v "context=" | egrep -v '\((|.*,)bind(,.*|)\)' | awk '/(ext[23]| xfs | jfs ).*\(rw/{print $3}' | egrep -v '/data|/config';`

# in RHEV-H *.py are blacklisted
cat > /etc/cron.d/rhn-virtualization.cron <<\EOF_RHN_CRON
0-59/2 * * * * root python /usr/share/rhn/virtualization/poller.pyc
EOF_RHN_CRON

# minimal lsb_release for vdsm-reg (bz#549147)
cat > /usr/bin/lsb_release <<\EOF_LSB
#!/bin/sh
if [ "$1" = "-r" ]; then
    printf "Release:\t$(cat /etc/redhat-release | awk '{print $7}')\n"
else
    echo RedHatEnterpriseVirtualizationHypervisor
fi
EOF_LSB
chmod +x /usr/bin/lsb_release

# CPE name rhbz#593463
cat > /etc/system-release-cpe <<\EOF_CPE
cpe:/o:redhat:enterprise_linux:6:update1:hypervisor
EOF_CPE

# kdump configuration
augtool <<\EOF_KDUMP
set /files/etc/sysconfig/kdump/KDUMP_BOOTDIR /boot-kdump
save
EOF_KDUMP

patch -d /usr/share/rhn/up2date_client -p0 <<\EOF
--- up2dateUtils.py	2010-08-23 13:57:00.761671000 -0400
+++ up2dateUtils.py.new	2010-08-23 14:23:08.836686828 -0400
@@ -19,21 +19,8 @@
 
 
 def _getOSVersionAndRelease():
-    cfg = config.initUp2dateConfig()
-    ts = transaction.initReadOnlyTransaction()
-    for h in ts.dbMatch('Providename', "redhat-release"):
-        if cfg["versionOverride"]:
-            version = cfg["versionOverride"]
-        else:
-            version = h['version']
-
-        osVersionRelease = (h['name'], version, h['release'])
+        osVersionRelease = ("redhat-release", "6Server", "RELEASE" )
         return osVersionRelease
-    else:
-       raise up2dateErrors.RpmError(
-           "Could not determine what version of Red Hat Linux you "\
-           "are running.\nIf you get this error, try running \n\n"\
-           "\t\trpm --rebuilddb\n\n")
 
 
 def getVersion():
EOF

sed -i "s/RELEASE/$RELEASE/g" /usr/share/rhn/up2date_client/up2dateUtils.py
python -m compileall /usr/share/rhn/up2date_client

# rhbz#627661 workaround, remove vdsm customization:
# fixes libvirtd startup on firstboot but migration won't work
sed -i -e '/by vdsm$/d' /etc/sysconfig/libvirtd

# udev: do not create symlinks under /dev/mapper/ rhbz#633222
sed -i -e '/^ENV{DM_UDEV_DISABLE_DM_RULES_FLAG}/d' /lib/udev/rules.d/10-dm.rules

patch -d /usr/share/rhn/up2date_client -p0 <<\EOF
--- up2dateErrors.py.old	2011-04-18 22:20:55.180730000 -0400
+++ up2dateErrors.py	2011-04-18 22:21:17.339730000 -0400
@@ -12,7 +12,20 @@
 _ = gettext.gettext
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
EOF
python -m compileall /usr/share/rhn/up2date_client
