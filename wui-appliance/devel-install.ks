network --device=eth1 --bootproto=static --ip=192.168.50.2 --netmask=255.255.255.0 --onboot=on

# Create some fake iSCSI partitions
logvol /iscsi3 --name=iSCSI3 --vgname=VolGroup00 --size=64
logvol /iscsi4 --name=iSCSI4 --vgname=VolGroup00 --size=64
logvol /iscsi5 --name=iSCSI5 --vgname=VolGroup00 --size=64