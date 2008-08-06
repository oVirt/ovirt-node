lang C
keyboard us
timezone --utc UTC
auth --useshadow --enablemd5
selinux --disabled
firewall --disabled
part / --size 550 --fstype ext2
services --enabled=ntpd,ntpdate,collectd,iptables,network
# This requires a new fixed version of livecd-creator to honor the --append settings.
bootloader --timeout=1 --append="console=tty0 console=ttyS0,115200n8"
rootpw --iscrypted Xa8QeYfWrtscM

