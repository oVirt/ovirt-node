bootloader --timeout=30 --append="nomodeset check rootflags=ro crashkernel=512M-2G:64M,2G-:128M elevator=deadline install quiet rd_NO_LVM stateless=1"
services --enabled=auditd,ntpd,ntpdate,iptables,network,rsyslog,multipathd,snmpd,ovirt-early,ovirt,ovirt-post,anyterm,collectd,libvirt-qmf,matahari-host,libvirtd,cgconfig,archipel --disabled=vdsmd,vdsm-reg
