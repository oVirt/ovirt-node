bootloader --timeout=30 --append="nomodeset check rootflags=ro crashkernel=128M elevator=deadline install quiet rd_NO_LVM stateless=1"
services --enabled=auditd,ntpd,ntpdate,iptables,network,rsyslog,multipathd,snmpd,ovirt-early,ovirt,ovirt-post,anyterm,collectd,libvirtd,cgconfig,archipel,tuned
