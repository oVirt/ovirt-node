
from ovirtnode.ovirtfunctions import *
import os

def enable_snmpd(password):
    conf = "/etc/snmp/snmpd.conf"
    system("service snmpd stop")
    # get old password #
    cmd="cat /etc/snmp/snmpd.conf |grep createUser|awk '{print $4}'"
    oldpwd = subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    oldpwd = oldpwd.stdout.read().strip()
    system("sed -c -ie '/^createUser root/d' %s" % conf)
    f = open(conf, "a")
    # create user account
    f.write("createUser root SHA %s AES\n" % password)
    f.close()
    system("service snmpd start")
    # change existing password
    if oldpwd > 0:
        pwd_change_cmd = "snmpusm -v 3 -u root -n \"\" -l authNoPriv -a SHA -A %s localhost passwd %s %s -x AES" % (oldpwd, oldpwd, password)
        system(pwd_change_cmd)
    ovirt_store_config(conf)

def disable_snmpd():
    system("service snmpd stop")
    remove_config("/etc/snmp/snmpd.conf")

def snmp_auto():
    if OVIRT_VARS.has_key("OVIRT_SNMP_PASSWORD"):
        enable_snmpd(OVIRT_VARS["OVIRT_SNMP_PASSWORD"])
