# create grub/grub2 efi boot configuation

if [ ! -e $INSTALL_ROOT/sbin/grub2-install ]; then
    cat > $LIVE_ROOT/EFI/BOOT/BOOTX64.conf <<EOF
default=0
splashimage=/EFI/BOOT/splash.xpm.gz
timeout 30
hiddenmenu
title Install / Upgrade ${PRODUCT_SHORT}-$VERSION-$RELEASE
  kernel /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0
  initrd /isolinux/initrd0.img
title Install / Upgrade (Basic Video) ${PRODUCT_SHORT}-$VERSION-$RELEASE
  kernel /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0 nomodeset
  initrd /isolinux/initrd0.img
title Install / Upgrade with serial console ${PRODUCT_SHORT}-$VERSION-$RELEASE
  kernel /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0  console=ttyS0,115200n8
  initrd /isolinux/initrd0.img
title Reinstall ${PRODUCT_SHORT}-$VERSION-$RELEASE
  kernel /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0  reinstall
  initrd /isolinux/initrd0.img
title Reinstall (Basic Video) ${PRODUCT_SHORT}-$VERSION-$RELEASE
  kernel /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0  reinstall nomodeset
  initrd /isolinux/initrd0.img
title Reinstall with serial console ${PRODUCT_SHORT}-$VERSION-$RELEASE
  kernel /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0  reinstall console=ttyS0,115200n8
  initrd /isolinux/initrd0.img
title Uninstall
  kernel /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0  uninstall
  initrd /isolinux/initrd0.img
EOF
else
    cat > $LIVE_ROOT/EFI/BOOT/BOOTX64.conf <<EOF
set default="0"

function load_video {
  insmod efi_gop
  insmod efi_uga
  insmod video_bochs
  insmod video_cirrus
  insmod all_video
}

load_video
set gfxpayload=keep
insmod gzio
insmod part_gpt
insmod ext2

set timeout=30

menuentry 'Install or Upgrade ${PRODUCT_SHORT}-$VERSION-$RELEASE' --class fedora --class gnu-linux --class gnu --class os {
        linuxefi /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0
        initrdefi /isolinux/initrd0.img
}
menuentry 'Install or Upgrade (Basic Video) ${PRODUCT_SHORT}-$VERSION-$RELEASE' --class fedora --class gnu-linux --class gnu --class os {
        linuxefi /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0 nomodeset
        initrdefi /isolinux/initrd0.img
}
menuentry 'Install or Upgrade with serial console ${PRODUCT_SHORT}-$VERSION-$RELEASE' --class fedora --class gnu-linux --class gnu --class os {
        linuxefi /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0  console=ttyS0,115200n8
        initrdefi /isolinux/initrd0.img
}
menuentry 'Reinstall ${PRODUCT_SHORT}-$VERSION-$RELEASE' --class fedora --class gnu-linux --class gnu --class os {
        linuxefi /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0  reinstall
        initrdefi /isolinux/initrd0.img
}
menuentry 'Reinstall (Basic Video) ${PRODUCT_SHORT}-$VERSION-$RELEASE' --class fedora --class gnu-linux --class gnu --class os {
        linuxefi /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0  reinstall nomodeset
        initrdefi /isolinux/initrd0.img
}
menuentry 'Reinstall with serial console ${PRODUCT_SHORT}-$VERSION-$RELEASE' --class fedora --class gnu-linux --class gnu --class os {
        linuxefi /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0  reinstall console=ttyS0,115200n8
        initrdefi /isolinux/initrd0.img
}
menuentry 'Uninstall' --class fedora --class gnu-linux --class gnu --class os {
        linuxefi /isolinux/vmlinuz0 root=live:CDLABEL=$NAME rootfstype=auto ro liveimg check rootflags=ro crashkernel=128M elevator=deadline install rhgb quiet rd_NO_MULTIPATH rd_NO_LVM rd.luks=0 rd.md=0 rd.dm=0  uninstall
        initrdefi /isolinux/initrd0.img
}
EOF
fi
cp $LIVE_ROOT/EFI/BOOT/BOOTX64.conf $LIVE_ROOT/EFI/BOOT/grub.cfg
