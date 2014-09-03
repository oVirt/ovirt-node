%include fedora-pkgs.ks
grub2-efi
firewalld
selinux-policy-devel
shim
# qlogic firmware
linux-firmware
iptables
net-tools
iproute
bfa-firmware
grubby
glusterfs-server
# Explicitly add these package, to prevent yum from pulling in the debug versions
kernel-modules-extra

# To disable hostonly mode
dracut-config-generic
