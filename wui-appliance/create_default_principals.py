#!/usr/bin/python

import krbV
import os
import socket
import shutil

def kadmin_local(command):
	ret = os.system("/usr/kerberos/sbin/kadmin.local -q '" + command + "'")
	if ret != 0:
		raise

default_realm = krbV.Context().default_realm

# here, generate the libvirt/ principle for this machine, necessary
# for taskomatic and host-browser
this_libvirt_princ = 'libvirt/' + socket.gethostname() + '@' + default_realm
kadmin_local('addprinc -randkey +requires_preauth ' + this_libvirt_princ)
kadmin_local('ktadd -k /usr/share/ovirt-wui/ovirt.keytab ' + this_libvirt_princ)
