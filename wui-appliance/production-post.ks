cat > /root/add_host_principal.py << \EOF
#!/usr/bin/python

import krbV
import os
import socket
import shutil
import sys

def kadmin_local(command):
        ret = os.system("/usr/kerberos/sbin/kadmin.local -q '" + command + "'")
        if ret != 0:
                raise

def get_ip(hostname):
        return socket.gethostbyname(hostname)

if len(sys.argv) != 2:
        print "Usage: add_host_principal.py <hostname>"
        sys.exit(1)


default_realm = krbV.Context().default_realm

ipaddr = get_ip(sys.argv[1])

libvirt_princ = 'libvirt/' + sys.argv[1] + '@' + default_realm
outname = '/usr/share/ipa/html/' + ipaddr + '-libvirt.tab'

# here, generate the libvirt/ principle for this machine, necessary
# for taskomatic and host-browser
kadmin_local('addprinc -randkey +requires_preauth ' + libvirt_princ)
kadmin_local('ktadd -k ' + outname + ' ' + libvirt_princ)

# make sure it is readable by apache
os.chmod(outname, 0644)
EOF
chmod +x /root/add_host_principal.py

cat > /etc/init.d/ovirt-app-first-run << \EOF
#!/bin/bash
#
# ovirt-app-first-run First run configuration for Ovirt WUI appliance
#
# chkconfig: 3 99 01
# description: ovirt appliance first run configuration
#

# Source functions library
. /etc/init.d/functions

start() {
	service postgresql initdb
	echo "local all all trust" > /var/lib/pgsql/data/pg_hba.conf
	echo "host all all 127.0.0.1 255.255.255.0 trust" >> /var/lib/pgsql/data/pg_hba.conf
	service postgresql start

	su - postgres -c "/usr/bin/psql -f /usr/share/ovirt-wui/psql.cmds"

	cd /usr/share/ovirt-wui ; rake db:migrate
	/usr/bin/ovirt_grant_admin_privileges.sh admin
}

case "$1" in
  start)
        start
        ;;
  *)
        echo "Usage: ovirt {start}"
        exit 2
esac

chkconfig ovirt-app-first-run off
EOF
chmod +x /etc/init.d/ovirt-app-first-run
/sbin/chkconfig ovirt-app-first-run on