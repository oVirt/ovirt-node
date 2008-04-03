lang C
keyboard us
timezone US/Eastern
auth --useshadow --enablemd5
selinux --disabled
firewall --disabled
part / --size 450
services --enabled=ntpd,collectd,iptables
bootloader --timeout=1
rootpw ovirt

repo --name=f8 --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=fedora-8&arch=$basearch
repo --name=f8-updates --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=updates-released-f8&arch=$basearch
# Not using rawhide currently
#repo --name=rawhide --mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=rawhide&arch=$basearch
repo --name=ovirt-host --baseurl=http://ovirt.et.redhat.com/repos/ovirt-host-repo/$basearch/
