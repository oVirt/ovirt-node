lang C
keyboard us
timezone --utc UTC
auth --useshadow --enablemd5
selinux --enforcing
firewall --disabled
# TODO: the sizing of the image needs to be more dynamic
part / --size 1024 --fstype ext2
services --enabled=auditd,ntpd,ntpdate,collectd,iptables,network,rsyslog,libvirt-qpid,multipathd,snmpd
# This requires a new fixed version of livecd-creator to honor the --append settings.
bootloader --timeout=30 --append="console=tty0 console=ttyS0,115200n8"

# not included by default in Fedora 10 livecd initramfs
device virtio_blk
device virtio_pci
device scsi_wait_scan

# multipath kmods
device dm-multipath
device dm-round-robin
device dm-emc
device dm-rdac
device dm-hp-sw
device scsi_dh_rdac
