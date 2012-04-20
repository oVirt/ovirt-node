audit
dmraid
bc
cracklib-python
ethtool
kernel
hwdata
passwd
policycoreutils
rootfiles
dhclient
openssh-clients
openssh-server
kvm
libmlx4
ovirt-node
selinux-policy-targeted
vim-minimal
sudo
python
python-gudev
python-libs
python-setuptools
PyPAM
db4
vconfig
python-virtinst
# debugging
hdparm
sos
gdb
strace
sysstat
tcpdump
pciutils
usbutils
lsscsi
psmisc
numactl
file
lsof
newt-python
systemtap-runtime
qemu-kvm-tools
setools-console
# remove
-audit-libs-python
-ustr
-authconfig
-wireless-tools
-setserial
-prelink
-newt
-libselinux-python
-kbd
-usermode
-gzip
-less
-which
-parted
-tar
-libuser
-mtools
-cpio
/usr/sbin/lokkit
isomd5sum
irqbalance
acpid
device-mapper-multipath
kpartx
dracut-network
dracut-fips
patch
e2fsprogs
sysfsutils
less
# Autotest support rhbz#631795
dosfstools
# kdump
kexec-tools
# SNMP support rhbz#614870
net-snmp
# qlogic firmware
ql2100-firmware
ql2200-firmware
ql23xx-firmware
ql2400-firmware
ql2500-firmware
# more firmwares
aic94xx-firmware
bfa-firmware

# dracut dmsquash-live module requires eject
eject

# for building custom selinux module
make
checkpolicy
#
policycoreutils-python
# crypto swap support
cryptsetup-luks
# rhbz#641494 RFE - add libguestfs
libguestfs
python-libguestfs
libguestfs-tools-c
python-hivex
febootstrap-supermin-helper
# sosreport soft-dep
rpm-python
# for efi installs
efibootmgr
# libvirt-cim
sblim-sfcb
libvirt-cim