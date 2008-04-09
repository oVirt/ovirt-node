lang en_US.UTF-8
keyboard us
network --device eth0 --bootproto dhcp
rootpw --iscrypted Xa8QeYfWrtscM
firewall --disabled
authconfig --enableshadow --enablemd5
selinux --disabled
services --disabled=iptables,yum-updatesd,libvirtd,bluetooth,cups,gpm,pcscd --enabled=ntpd,httpd,postgresql,ovirt-wui,tgtd
timezone --utc America/New_York
text

bootloader --location=mbr --driveorder=sda
# The following is the partition information you requested
# Note that any partitions you deleted are not expressed
# here so unless you clear all partitions first, this is
# not guaranteed to work
zerombr
clearpart --all --drives=sda
part /boot --fstype ext3 --size=100 --ondisk=sda
part pv.2 --size=1 --grow --ondisk=sda
volgroup VolGroup00 --pesize=32768 pv.2
logvol swap --fstype swap --name=LogVol01 --vgname=VolGroup00 --size=512
logvol / --fstype ext3 --name=LogVol00 --vgname=VolGroup00 --size=1024 --grow
reboot
