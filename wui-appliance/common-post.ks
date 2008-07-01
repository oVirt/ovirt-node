# -*-Shell-script-*-
PATH=/sbin:/usr/sbin:/bin:/usr/bin
export PATH

# pretty login screen..
g=$(printf '\33[1m\33[32m')    # similar to g=$(tput bold; tput setaf 2)
n=$(printf '\33[m')            # similar to n=$(tput sgr0)
cat <<EOF > /etc/issue

           888     888 ${g}d8b$n         888
           888     888 ${g}Y8P$n         888
           888     888             888
   .d88b.  Y88b   d88P 888 888d888 888888
  d88''88b  Y88b d88P  888 888P'   888
  888  888   Y88o88P   888 888     888
  Y88..88P    Y888P    888 888     Y88b.
   'Y88P'      Y8P     888 888      'Y888

  Admin Node

  Virtualization just got the ${g}Green Light$n

EOF
cp /etc/issue /etc/issue.net

cat > /etc/init.d/ovirt-wui-first-run << \EOF
#!/bin/bash
#
# ovirt-wui-first-run First run configuration for oVirt WUI appliance
#
# chkconfig: 3 96 01
# description: ovirt wui appliance first run configuration
#

# Source functions library
. /etc/init.d/functions

start() {
	echo -n "Starting ovirt-wui-first-run: "

	ovirt-wui-install > /var/log/ovirt-wui-first-run.log 2>&1

	RETVAL=$?
	if [ $RETVAL -eq 0 ]; then
		echo_success
	else
		echo_failure
	fi
	echo
}

case "$1" in
  start)
        start
        ;;
  *)
        echo "Usage: ovirt-wui-first-run {start}"
        exit 2
esac

chkconfig ovirt-wui-first-run off
EOF
chmod +x /etc/init.d/ovirt-wui-first-run
chkconfig ovirt-wui-first-run on

cat > /etc/yum.repos.d/ovirt.repo << \EOF
[ovirt]
name=ovirt
baseurl=http://ovirt.org/repos/ovirt/9/$basearch/
enabled=1
gpgcheck=0
EOF

# XXX default configuration db
cat > /var/www/html/ovirt-cfgdb << \EOF
rm /files/etc/sysconfig/network-scripts/ifcfg-eth0
set /files/etc/sysconfig/network-scripts/ifcfg-eth0/DEVICE eth0
set /files/etc/sysconfig/network-scripts/ifcfg-eth0/ONBOOT yes
set /files/etc/sysconfig/network-scripts/ifcfg-eth0/BRIDGE ovirtbr0
rm /files/etc/sysconfig/network-scripts/ifcfg-ovirtbr0
set /files/etc/sysconfig/network-scripts/ifcfg-ovirtbr0/DEVICE ovirtbr0
set /files/etc/sysconfig/network-scripts/ifcfg-ovirtbr0/BOOTPROTO dhcp
set /files/etc/sysconfig/network-scripts/ifcfg-ovirtbr0/ONBOOT y
set /files/etc/sysconfig/network-scripts/ifcfg-ovirtbr0/TYPE Bridge
set /files/etc/sysconfig/network-scripts/ifcfg-ovirtbr0/PEERNTP yes
save
EOF

