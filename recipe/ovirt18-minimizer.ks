# Fedora specific image minimization
drop /usr/sbin/wpa*
drop /usr/sbin/eapol_test
droprpm gsettings-desktop-schemas

# qemu minimization
droprpm qemu-system-alpha
droprpm qemu-system-arm
droprpm qemu-system-cris
droprpm qemu-system-lm32
droprpm qemu-system-m68k
droprpm qemu-system-microblaze
droprpm qemu-system-mips
droprpm qemu-system-or32
droprpm qemu-system-ppc
droprpm qemu-system-s390x
droprpm qemu-system-sh4
droprpm qemu-system-sparc
droprpm qemu-system-unicore
droprpm qemu-system-xtensa
droprpm qemu-user

# libguestfs related minimization
# The following rpms can be dropped and don't harm libguestfs too much
droprpm SLOF
droprpm cups-libs
droprpm ghostscript
droprpm ghostscript-fonts
droprpm fuse
droprpm zfs-fuse
droprpm gfs2-utils
droprpm hfsplus-tools
droprpm lcms2
droprpm libXfont
droprpm libXt
droprpm libfontenc
droprpm xorg-x11-font-utils
droprpm man-db
droprpm zerofree
droprpm firewalld
