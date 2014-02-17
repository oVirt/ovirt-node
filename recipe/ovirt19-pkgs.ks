%include fedora-pkgs.ks
grub2-efi
firewalld
selinux-policy-devel
shim
# qlogic firmware
linux-firmware
iptables
net-tools
vconfig
aic94xx-firmware
bfa-firmware

# Explicitly add these package, to prevent yum from pulling in the debug versions
kernel-modules-extra
