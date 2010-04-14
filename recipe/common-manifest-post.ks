%post
# Create post-image processing manifests
rpm -qa --qf '%{name}-%{version}-%{release}.%{arch} (%{SIGGPG:pgpsig})\n' | \
    sort > /manifest-rpm.txt
rpm -qa --qf '%{sourcerpm}\n' | sort -u > /manifest-srpm.txt
du -akx --exclude=/var/cache/yum / > /manifest-file.txt
du -x --exclude=/var/cache/yum / > /manifest-dir.txt

%end

%post --nochroot
# Move manifests to ISO
mv $INSTALL_ROOT/manifest-*.txt $LIVE_ROOT/isolinux

# only works on x86, x86_64
if [ "$(uname -i)" = "i386" -o "$(uname -i)" = "x86_64" ]; then
    if [ ! -d $LIVE_ROOT/LiveOS ]; then mkdir -p $LIVE_ROOT/LiveOS ; fi
    cp /usr/bin/livecd-iso-to-disk $LIVE_ROOT/LiveOS
    cp /usr/bin/livecd-iso-to-pxeboot $LIVE_ROOT/LiveOS
fi
%end
