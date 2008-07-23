lang en_US.UTF-8
keyboard us
network --device eth0 --bootproto dhcp
rootpw --iscrypted Xa8QeYfWrtscM
firewall --disabled
authconfig --enableshadow --enablemd5
selinux --disabled
services --disabled=libvirtd,postgresql,yum-updatesd,bluetooth,cups,gpm,pcscd,NetworkManager,NetworkManagerDispatcher --enabled=network,tgtd,nfs,iptables
timezone --utc UTC
text

bootloader --location=mbr --driveorder=sda
# The following is the partition information you requested
# Note that any partitions you deleted are not expressed
# here so unless you clear all partitions first, this is
# not guaranteed to work
zerombr
clearpart --all --drives=sda
part /boot  --ondisk=sda --fstype=ext3 --size=100
part /      --ondisk=sda --fstype=ext3 --size=5000
part swap   --ondisk=sda --fstype=swap --size=512
reboot
