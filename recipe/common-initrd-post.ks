%post

# rebuild initramfs to include multipath rhbz#627647
echo -n "Rebuilding initramfs for multipath and disk cleanup..."
kernel="$(rpm -q --qf '%{VERSION}-%{RELEASE}.%{ARCH}\n' kernel)"
/sbin/dracut -f -a "ovirtnode" -a "multipath" /initrd0.img "$kernel"
echo "done."

%end

%post --nochroot

# replace initramfs if regenerated
if [ -f "$INSTALL_ROOT/initrd0.img" ]; then
  mv -v "$INSTALL_ROOT/initrd0.img" "$LIVE_ROOT/isolinux/initrd0.img"
fi

%end
