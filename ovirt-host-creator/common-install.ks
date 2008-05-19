lang C
keyboard us
timezone --utc UTC
auth --useshadow --enablemd5
selinux --disabled
firewall --disabled
part / --size 550
services --enabled=ntpd,collectd,iptables,network
bootloader --timeout=1
rootpw --iscrypted Xa8QeYfWrtscM

repo --name=f9 --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=fedora-9&arch=$basearch
repo --name=f9-updates --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=updates-released-f9&arch=$basearch

