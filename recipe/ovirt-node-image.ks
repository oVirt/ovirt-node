%include common-install.ks

%include repos.ks

%packages --excludedocs --nobase
%include common-pkgs.ks

%end

%post
# cleanup rpmdb to allow non-matching host and chroot RPM versions
rm -f /var/lib/rpm/__db*
%include common-post.ks

touch /.autorelabel

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
echo "/dev/HostVG/Config /config ext3 defaults,noauto,noatime 0 0" >> /etc/fstab
%end

%post
# Create initial manifests
manifests=/tmp/manifests
mkdir -p $manifests
rpm -qa --qf '%{name}-%{version}-%{release}.%{arch}\n' | sort \
    > $manifests/rpm-manifest.txt
rpm -qa --qf '%{sourcerpm}\n' | sort -u > $manifests/srpm-manifest.txt
du -akx --exclude=/var/cache/yum / > $manifests/file-manifest.txt
du -x --exclude=/var/cache/yum / > $manifests/dir-manifest.txt
%end

%include common-blacklist.ks

%post --nochroot
if [ -f "ovirt-authorized_keys" ]; then
  echo "Adding authorized_keys to Image"
  mkdir -p $INSTALL_ROOT/root/.ssh
  cp -v ovirt-authorized_keys $INSTALL_ROOT/root/.ssh/authorized_keys
  chown -R root:root $INSTALL_ROOT/root/.ssh
  chmod 755 $INSTALL_ROOT/root/.ssh
  chmod 644 $INSTALL_ROOT/root/.ssh/authorized_keys
fi

echo "Fixing boot menu"
# remove quiet from Node bootparams, added by livecd-creator
sed -i -e 's/ quiet//' $LIVE_ROOT/isolinux/isolinux.cfg

# add stand-alone boot entry
awk '
BEGIN {
  # append additional default boot parameters
  add_boot_params="check"
}
/^label linux0/ { linux0=1 }
linux0==1 && $1=="append" {
  $0=$0 " " add_boot_params
  append0=$0
}
linux0==1 && $1=="label" && $2!="linux0" {
  linux0=2
  print "label stand-alone"
  print "  menu label Boot in stand-alone mode"
  print "  kernel vmlinuz0"
  gsub("console=tty0", "", append0)
  print append0" ovirt_standalone console=tty0"
}
{ print }
' $LIVE_ROOT/isolinux/isolinux.cfg > $LIVE_ROOT/isolinux/isolinux.cfg.standalone
mv $LIVE_ROOT/isolinux/isolinux.cfg.standalone $LIVE_ROOT/isolinux/isolinux.cfg

cp $INSTALL_ROOT/usr/share/ovirt-node/syslinux-vesa-splash.jpg $LIVE_ROOT/isolinux/splash.jpg

# overwrite user visible banners with the image versioning info
PACKAGE=ovirt
ln -snf $PACKAGE-release $INSTALL_ROOT/etc/redhat-release
ln -snf $PACKAGE-release $INSTALL_ROOT/etc/system-release
cp $INSTALL_ROOT/etc/$PACKAGE-release $INSTALL_ROOT/etc/issue
echo "Kernel \r on an \m (\l)" >> $INSTALL_ROOT/etc/issue
cp $INSTALL_ROOT/etc/issue $INSTALL_ROOT/etc/issue.net

%end

%post
# Create post-image processing manifests
manifests=/tmp/manifests
mkdir -p $manifests
rpm -qa --qf '%{name}-%{version}-%{release}.%{arch}\n' | sort \
    > $manifests/rpm-manifest-post.txt
rpm -qa --qf '%{sourcerpm}\n' | sort -u > $manifests/srpm-manifest-post.txt
du -akx --exclude=/var/cache/yum / > $manifests/file-manifest-post.txt
du -x --exclude=/var/cache/yum / > $manifests/dir-manifest-post.txt

ver=$(rpm -q --qf '%{version}' ovirt-node)
rel=$(rpm -q --qf '%{release}' ovirt-node)
arch=$(rpm -q --qf '%{arch}' ovirt-node)
echo "oVirt Node release $ver-$rel-$arch" > $manifests/ovirt-release
tar -cvf ovirt-node-image-manifests-$ver-$rel.$arch.tar -C /tmp manifests
ln -nf ovirt-node-image-manifests-$ver-$rel.$arch.tar ovirt-node-image-manifests.tar
rm -Rf $manifests
%end

%post --nochroot
# Move manifest tar to build directory
mv $INSTALL_ROOT/ovirt-node-image-manifests*.tar .

# only works on x86, x86_64
if [ "$(uname -i)" = "i386" -o "$(uname -i)" = "x86_64" ]; then
    if [ ! -d $LIVE_ROOT/LiveOS ]; then mkdir -p $LIVE_ROOT/LiveOS ; fi
    cp /usr/bin/livecd-iso-to-disk $LIVE_ROOT/LiveOS
    cp /usr/bin/livecd-iso-to-pxeboot $LIVE_ROOT/LiveOS
fi
%end

