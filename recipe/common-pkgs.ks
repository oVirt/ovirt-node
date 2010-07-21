audit
bc
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
python-libs
python-setuptools
db4
vconfig
python-virtinst
#debugging
hdparm
sos
gdb
ltrace
strace
sysstat
tcpdump
pciutils
psmisc
numactl
file
lsof
newt-python
#/usr/bin/kvmtrace
qemu-kvm-tools
#remove
-audit-libs-python
-ustr
-authconfig
-wireless-tools
-setserial
-prelink
-newt-python
-newt
-libselinux-python
-kbd
-usermode
-redhat-release
-redhat-release-notes
-dmraid
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
cpuspeed
acpid
device-mapper-multipath
kpartx
dracut-network
patch
e2fsprogs
sysfsutils
less
#Autotest support rhbz#631795
dosfstools
# VDSM
vdsm-cli
vdsm-reg
# workaround: vdsm-reg dep
traceroute
# host statistics rhbz#588852
vhostmd
# kdump
kexec-tools
# RHN agent
rhn-virtualization-host
rhn-setup
# SNMP support rhbz#614870
net-snmp
# qlogic firmware
ql2100-firmware
ql2200-firmware
ql23xx-firmware
ql2400-firmware
ql2500-firmware
# for building custom selinux module
make
checkpolicy
#
policycoreutils-python
# crypto swap support
cryptsetup-luks
# newt UI deps
#python-augeas not in RHEL-6, import augeas.py in ovirt-node
ethtool
python-devel
PyPAM
cracklib-python
python-gudev
# F15 dracut missing dep, bz# ???
less
# rhbz#641494 RFE - add libguestfs into RHEV-H
libguestfs
python-libguestfs
libguestfs-tools-c
python-hivex
