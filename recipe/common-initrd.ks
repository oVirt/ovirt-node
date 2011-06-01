%post

# patch dmsquash-live dracut module
# rhbz#683330
# http://article.gmane.org/gmane.linux.kernel.initramfs/1879
patch -d /usr/share/dracut/ -p1 << \EOF_DMSQUASH
--- a/modules.d/90dmsquash-live/dmsquash-live-root
+++ b/modules.d/90dmsquash-live/dmsquash-live-root
@@ -23,18 +23,19 @@
 getarg readonly_overlay && readonly_overlay="--readonly" || readonly_overlay=""
 overlay=$(getarg overlay)
 
-# FIXME: we need to be able to hide the plymouth splash for the check really
-[ -e $livedev ] & fs=$(blkid -s TYPE -o value $livedev)
+[ -e $livedev ] && fs=$(blkid -s TYPE -o value $livedev)
 if [ "$fs" = "iso9660" -o "$fs" = "udf" ]; then
     check="yes"
 fi
 getarg check || check=""
 if [ -n "$check" ]; then
+    [ -x /bin/plymouth ] && /bin/plymouth --hide-splash
     checkisomd5 --verbose $livedev || :
     if [ $? -ne 0 ]; then
 	die "CD check failed!"
 	exit 1
     fi
+    [ -x /bin/plymouth ] && /bin/plymouth --show-splash
 fi
 
 getarg ro && liverw=ro
EOF_DMSQUASH

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
