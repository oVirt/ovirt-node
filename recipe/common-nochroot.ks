
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

# Remove Verify and Boot option
sed -i -e '/label check0/{N;N;N;d;}' $LIVE_ROOT/isolinux/isolinux.cfg

# Rename Boot option to Install or Upgrade
sed -i 's/^  menu label Boot$/  menu label Install or Upgrade/' $LIVE_ROOT/isolinux/isolinux.cfg

# add serial console boot entry
menu=$(mktemp)
awk '
/^label linux0/ { linux0=1 }
linux0==1 && $1=="append" {
  append0=$0
}
linux0==1 && $1=="label" && $2!="linux0" {
  linux0=2
  print "label install (basic video)"
  print "  menu label Install (Basic Video)"
  print "  kernel vmlinuz0"
  print append0" nomodeset "
  print "label serial-console"
  print "  menu label Install or Upgrade with serial console"
  print "  kernel vmlinuz0"
  print append0" console=ttyS0,115200n8 "
  print "label reinstall"
  print "  menu label Reinstall"
  print "  kernel vmlinuz0"
  print append0" reinstall "
  print "label reinstall (basic video)"
  print "  menu label Reinstall (Basic Video)"
  print "  kernel vmlinuz0"
  print append0" reinstall nomodeset "
  print "label reinstall-serial"
  print "  menu label Reinstall with serial console"
  print "  kernel vmlinuz0"
  print append0" reinstall console=ttyS0,115200n8 "
  print "label uninstall"
  print "  menu label Uninstall"
  print "  kernel vmlinuz0"
  print append0" uninstall "
}
{ print }
' $LIVE_ROOT/isolinux/isolinux.cfg > $menu
# change the title
sed -i -e '/^menu title/d' $menu
echo "say This is the $PRODUCT $VERSION ($RELEASE)" > $LIVE_ROOT/isolinux/isolinux.cfg
echo "menu title ${PRODUCT_SHORT} $VERSION ($RELEASE)" >> $LIVE_ROOT/isolinux/isolinux.cfg
cat $menu >> $LIVE_ROOT/isolinux/isolinux.cfg
rm $menu
# remove extra boot args add by updated livecd-tools
sed -i -e 's/xdriver=vesa nomodeset//g' $LIVE_ROOT/isolinux/isolinux.cfg
cp $INSTALL_ROOT/usr/share/ovirt-node/syslinux-vesa-splash.jpg $LIVE_ROOT/isolinux/splash.jpg

# store image version info in the ISO and rootfs
cat > $LIVE_ROOT/isolinux/version <<EOF
PRODUCT='$PRODUCT'
PRODUCT_SHORT='${PRODUCT_SHORT}'
PRODUCT_CODE=$PRODUCT_CODE
RECIPE_SHA256=$RECIPE_SHA256
RECIPE_RPM=$RECIPE_RPM
PACKAGE=$PACKAGE
VERSION=$VERSION
RELEASE=$RELEASE
EOF
cp $LIVE_ROOT/isolinux/version $INSTALL_ROOT/etc/default/

# overwrite user visible banners with the image versioning info
# system-release in rootfs get's updated, but now it's out of sync with initrd
# The only bit which is missing in the initrd system-release file is VERSION
# /(which is not shown in ply anyway)
# The initrd can not be regeneated in a non-chroot env (here)
cat > $INSTALL_ROOT/etc/$PACKAGE-release <<EOF
$PRODUCT release $VERSION ($RELEASE)
EOF
ln -snf $PACKAGE-release $INSTALL_ROOT/etc/redhat-release
ln -snf $PACKAGE-release $INSTALL_ROOT/etc/system-release
cp $INSTALL_ROOT/etc/$PACKAGE-release $INSTALL_ROOT/etc/issue
echo "Kernel \r on an \m (\l)" >> $INSTALL_ROOT/etc/issue
cp $INSTALL_ROOT/etc/issue $INSTALL_ROOT/etc/issue.net

NAME=$(grep CDLABEL $LIVE_ROOT/isolinux/isolinux.cfg |head -n1|sed -r 's/^.*CDLABEL\=([a-zA-Z0-9_\.-]+) .*$/\1/g')

%include common-efi.ks
