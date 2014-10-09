# -*-Shell-script-*-
echo "Starting Kickstart Post"
PATH=/sbin:/usr/sbin:/bin:/usr/bin
export PATH

# cleanup rpmdb to allow non-matching host and chroot RPM versions
echo "Removing yumdb data"
rm -f /var/lib/rpm/__db*

echo "Creating shadow files"
# because we aren't installing authconfig, we aren't setting up shadow
# and gshadow properly.  Do it by hand here
pwconv
grpconv

echo "Lock root account"
passwd -l root

echo "Relabeling files"
#/usr/sbin/fixfiles -R -a restore
restorecon -R /

echo "Configuring libvirt"
# make sure we don't autostart virbr0 on libvirtd startup
rm -f /etc/libvirt/qemu/networks/autostart/default.xml

# rhevh uses libvirtd upstart job, sysv initscript must not interfere
rm -f /etc/rc.d/init.d/libvirtd

# Remove the default logrotate daily cron job
# since we run it every 10 minutes instead.
rm -f /etc/cron.daily/logrotate

# Logrotate more judiciously so the size of syslog stays under control
sed -i '/^.*sharedscripts/a \    rotate 5\n    size 15M\n    compress' /etc/logrotate.d/syslog

# root's bash profile
cat >> /root/.bashrc << \EOF_bashrc
# aliases used for the temporary
function mod_vi() {
  /bin/vi $@
  restorecon -v $@ >/dev/null 2>&1
}

function mod_yum() {
  if [ "$1" == "--force" ]; then
      echo $@ > /dev/null
      shift
      /usr/bin/yum $@
  else
      printf "\nUsing yum is not supported\n\n"
  fi
}

function mod_less() {
    cat $1 | less
}

alias ping='ping -c 3'
alias yum="mod_yum"
alias less="mod_less"
export MALLOC_CHECK_=1
export LVM_SUPPRESS_FD_WARNINGS=0
EOF_bashrc

# directories required in the image with the correct perms
# config persistance currently handles only regular files
mkdir -p /root/.ssh
chmod 700 /root/.ssh
mkdir -p /boot
mkdir -p /boot-kdump
mkdir -p /config
mkdir -p /data
mkdir -p /data2
mkdir -p /live
mkdir -p /liveos
mkdir -p /root/.uml
mkdir -p /var/cache/multipathd
touch /var/lib/random-seed
echo "/dev/HostVG/Config /config ext4 defaults,noauto,noatime 0 0" >> /etc/fstab

# Create wwids file to prevent an error on boot, rhbz #805570
mkdir -p /etc/multipath
touch /etc/multipath/wwids
chmod 0600 /etc/multipath/wwids

# prepare for STATE_MOUNT in rc.sysinit
augtool << \EOF_readonly-root
set /files/etc/sysconfig/readonly-root/STATE_LABEL CONFIG
set /files/etc/sysconfig/readonly-root/STATE_MOUNT /config
set /files/etc/sysconfig/readonly-root/READONLY yes
save
EOF_readonly-root

# comment out /etc/* entries in rwtab to prevent overlapping mounts
sed -i '/^files	\/etc*/ s/^/#/' /etc/rwtab
cat > /etc/rwtab.d/ovirt << \EOF_rwtab_ovirt
files	/etc
dirs	/var/lib/multipath
files	/var/lib/net-snmp
dirs    /var/lib/dnsmasq
files	/root/.ssh
dirs	/root/.uml
files	/var/cache/libvirt
files	/var/empty/sshd/etc/localtime
files	/var/lib/libvirt
files   /var/lib/multipath
files   /var/cache/multipathd
empty	/mnt
files	/boot
empty	/boot-kdump
empty	/cgroup
files	/var/lib/yum
files	/var/cache/yum
files	/usr/share/snmp/mibs
files   /var/lib/lldpad
dirs	/var/cache/rpcbind
files	/usr/share/snmp/mibs
files   /var/lib/lldpad
dirs	/var/cache/rpcbind
EOF_rwtab_ovirt

# fix iSCSI/LVM startup issue
sed -i 's/node\.session\.initial_login_retry_max.*/node.session.initial_login_retry_max = 60/' /etc/iscsi/iscsid.conf

#lvm.conf should use /dev/mapper and /dev/sdX devices
# and not /dev/dm-X devices
sed -i 's/preferred_names = \[ "^\/dev\/mpath\/", "^\/dev\/mapper\/mpath", "^\/dev\/\[hs\]d" \]/preferred_names = \[ "^\/dev\/mapper", "^\/dev\/\[hsv\]d" \]/g' /etc/lvm/lvm.conf

# unset AUDITD_LANG to prevent boot errors
sed -i '/^AUDITD_LANG*/ s/^/#/' /etc/sysconfig/auditd

# kdump configuration
augtool << \EOF_kdump
set /files/etc/sysconfig/kdump/KDUMP_BOOTDIR /boot-kdump
set /files/etc/sysconfig/kdump/MKDUMPRD_ARGS --allow-missing
save
EOF_kdump

# add admin user for configuration ui
useradd admin
usermod -G wheel admin
usermod -s /usr/libexec/ovirt-admin-shell admin
echo "%wheel	ALL=(ALL)	NOPASSWD: ALL" >> /etc/sudoers

# load modules required by crypto swap
cat > /etc/sysconfig/modules/swap-crypt.modules << \EOF_swap-crypt
#!/bin/sh

modprobe aes >/dev/null 2>&1
modprobe dm_mod >/dev/null 2>&1
modprobe dm_crypt >/dev/null 2>&1
modprobe cryptoloop >/dev/null 2>&1
modprobe cbc >/dev/null 2>&1
modprobe sha256 >/dev/null 2>&1

EOF_swap-crypt
chmod +x /etc/sysconfig/modules/swap-crypt.modules

#strip out all unncesssary locales
localedef --list-archive | grep -v -i -E 'en_US.utf8' |xargs localedef --delete-from-archive
mv /usr/lib/locale/locale-archive /usr/lib/locale/locale-archive.tmpl
/usr/sbin/build-locale-archive

# use static RPC ports, to avoid collisions
augtool << \EOF_nfs
set /files/etc/sysconfig/nfs/RQUOTAD_PORT 875
set /files/etc/sysconfig/nfs/LOCKD_TCPPORT 32803
set /files/etc/sysconfig/nfs/LOCKD_UDPPORT 32769
set /files/etc/sysconfig/nfs/MOUNTD_PORT 892
set /files/etc/sysconfig/nfs/STATD_PORT 662
set /files/etc/sysconfig/nfs/STATD_OUTGOING_PORT 2020
save
EOF_nfs

python -m compileall /usr/lib/python2.*/site-packages/sos

# XXX someting is wrong with readonly-root and dracut
# see modules.d/95rootfs-block/mount-root.sh
sed -i "s/defaults,noatime/defaults,ro,noatime/g" /etc/fstab

echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config

#mount kernel debugfs
echo "debugfs /sys/kernel/debug debugfs auto 0 0" >> /etc/fstab

#symlink ovirt-node-setup into $PATH
ln -s /usr/bin/ovirt-node-setup /usr/sbin/setup


#set NETWORKING off by default
augtool << \EOF_NETWORKING
set /files/etc/sysconfig/network/NETWORKING no
save
EOF_NETWORKING

# disable SSH password auth by default
# set ssh timeouts for increased security
augtool << \EOF_sshd_config
set /files/etc/ssh/sshd_config/PasswordAuthentication no
set /files/etc/ssh/sshd_config/ClientAliveInterval 900
set /files/etc/ssh/sshd_config/ClientAliveCountMax 0
save
EOF_sshd_config

echo "
disable yum repos by default"
rm -f /tmp/yum.aug
for i in $(augtool match /files/etc/yum.repos.d/*/*/enabled 1); do
    echo "set $i 0" >> /tmp/yum.aug
done
if [ -f /tmp/yum.aug ]; then
    echo "save" >> /tmp/yum.aug
    augtool < /tmp/yum.aug
    rm -f /tmp/yum.aug
fi

echo "cleanup yum directories"
rm -rf /var/lib/yum/*

echo "enable strong random number generation"
sed -i '/SSH_USE_STRONG_RNG/d' /etc/sysconfig/sshd



# sosreport fixups for node image:
echo "use .pyc for plugins enumeration, .py is blacklisted"
# include *-release
if [[ $(rpm -E "%{?fedora}") = 20 ]] ||
    [[ $(rpm -E "%{?rhel}") = 7 ]] ||
    [[ $(rpm -E "%{?centos}") = 7 ]]; then
patch --fuzz 3 -d /usr/lib/python2.7/site-packages/sos -p0 <<  \EOF_sos_patch
--- utilities.py.orig    2013-08-04 08:36:51.000000000 -0700
+++ utilities.py   2014-03-18 15:25:02.675059445 -0700
@@ -296,13 +296,13 @@
         plugins = [self._plugin_name(plugin)
                 for plugin in list_
                 if "__init__" not in plugin
-                and plugin.endswith(".py")]
+                and plugin.endswith(".pyc")]
         plugins.sort()
         return plugins

     def _find_plugins_in_dir(self, path):
         if os.path.exists(path):
-            py_files = list(find("*.py", path))
+            py_files = list(find("*.pyc", path))
             pnames = self._get_plugins_from_list(py_files)
             if pnames:
                 return pnames
--- plugins/general.py.orig  2014-03-18 15:07:20.570811354 -0700
+++ plugins/general.py  2014-03-18 15:28:49.371866760 -0700
@@ -51,8 +51,7 @@
         super(RedHatGeneral, self).setup()

         self.add_copy_specs([
-            "/etc/redhat-release",
-            "/etc/fedora-release",
+            "/etc/*-release",
         ])
EOF_sos_patch

else
patch --fuzz 3 -d /usr/lib/python2.*/site-packages/sos -p0 << \EOF_sos_patch
--- sosreport.py.orig	2011-04-07 11:51:40.000000000 +0000
+++ sosreport.py	2011-07-06 13:26:44.000000000 +0000
@@ -428,8 +428,8 @@
 
     # validate and load plugins
     for plug in plugins:
-        plugbase =  plug[:-3]
-        if not plug[-3:] == '.py' or plugbase == "__init__":
+        plugbase =  plug[:-4]
+        if not plug[-4:] == '.pyc' or plugbase == "__init__":
             continue
         try:
             if GlobalVars.policy.validatePlugin(pluginpath + plug):
--- plugins/general.py.orig     2011-02-09 15:25:48.000000000 +0000
+++ plugins/general.py  2011-07-06 23:13:32.000000000 +0000
@@ -25,8 +25,7 @@
                   ("all_logs", "collect all log files defined in syslog.conf", "", False)]
 
     def setup(self):
-        self.addCopySpec("/etc/redhat-release")
-        self.addCopySpec("/etc/fedora-release")
+        self.addCopySpec("/etc/*-release")
         self.addCopySpec("/etc/inittab")
         self.addCopySpec("/etc/sos.conf")
         self.addCopySpec("/etc/sysconfig")
EOF_sos_patch
fi

echo "Regenerating initramfs"
dracut -f || :
