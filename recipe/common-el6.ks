# add RHEV-H rwtab locations
mkdir -p /rhev
mkdir -p /var/cache/rhn
mkdir -p /boot-kdump
cat > /etc/rwtab.d/rhev <<EOF_RWTAB
empty	/rhev
files	/root/.ssh
files	/var/cache/rhn
files	/var/vdsm
files	/boot-kdump
EOF_RWTAB

# convenience symlinks
ln -s /usr/libexec/ovirt-config-rhn /sbin/rhn_register
ln -s /usr/sbin/ovirt-config-setup /usr/sbin/setup

# disable SSH password auth by default
augtool <<EOF
set /files/etc/ssh/sshd_config/PasswordAuthentication no
save
EOF

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

# rhbz#502779 restrict certain memory protection operations
# keep allow_execmem on for grub
cat >> /etc/rc.d/rc.local <<\EOF_RC_LOCAL
setsebool allow_execstack off
. /usr/libexec/ovirt-functions

# successfull boot from /dev/HostVG/Root
if grep -q -w root=live:LABEL=Root /proc/cmdline; then
    # set first boot entry as permanent default
    mount_boot
    echo "savedefault --default=0" | grub > /dev/null 2>&1
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
echo RedHatEnterpriseVirtualizationHypervisor
EOF_LSB
chmod +x /usr/bin/lsb_release

# CPE name rhbz#593463
cat > /etc/system-release-cpe <<\EOF_CPE
cpe:/o:redhat:enterprise_virtualization_hypervisor:6
EOF_CPE

# kdump configuration
augtool <<\EOF
set /files/etc/sysconfig/kdump/KDUMP_BOOTDIR /boot-kdump
save
EOF
