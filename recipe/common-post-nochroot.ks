
%include version.ks

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
menu=$(mktemp)
awk '
BEGIN {
  # append additional default boot parameters
  add_boot_params="check rootflags=ro crashkernel=128M"
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
' $LIVE_ROOT/isolinux/isolinux.cfg > $menu
# change the title
sed -i -e '/^menu title/d' $menu
echo "say This is the $PRODUCT $VERSION ($RELEASE)" > $LIVE_ROOT/isolinux/isolinux.cfg
echo "menu title Welcome to $PRODUCT $VERSION ($RELEASE)" >> $LIVE_ROOT/isolinux/isolinux.cfg
cat $menu >> $LIVE_ROOT/isolinux/isolinux.cfg
rm $menu
cp $INSTALL_ROOT/usr/share/ovirt-node/syslinux-vesa-splash.jpg $LIVE_ROOT/isolinux/splash.jpg

# store image version info in the ISO and rootfs
cat > $LIVE_ROOT/isolinux/version <<EOF
PRODUCT='$PRODUCT'
PACKAGE=$PACKAGE
VERSION=$VERSION
RELEASE=$RELEASE
EOF
cp $LIVE_ROOT/isolinux/version $INSTALL_ROOT/etc/default/

# overwrite user visible banners with the image versioning info
cat > $INSTALL_ROOT/etc/$PACKAGE-release <<EOF
$PRODUCT release $VERSION ($RELEASE)
EOF
ln -snf $PACKAGE-release $INSTALL_ROOT/etc/redhat-release
ln -snf $PACKAGE-release $INSTALL_ROOT/etc/system-release
cp $INSTALL_ROOT/etc/$PACKAGE-release $INSTALL_ROOT/etc/issue
echo "Kernel \r on an \m (\l)" >> $INSTALL_ROOT/etc/issue
cp $INSTALL_ROOT/etc/issue $INSTALL_ROOT/etc/issue.net
