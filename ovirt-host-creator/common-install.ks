lang C
keyboard us
timezone --utc UTC
auth --useshadow --enablemd5
selinux --disabled
firewall --disabled
part / --size 550
services --enabled=ntpd,ntpdate,collectd,iptables,network
bootloader --timeout=1
rootpw --iscrypted Xa8QeYfWrtscM

