
from ovirtnode.ovirtfunctions import *
import os

def enable_snmpd(password):
    conf = "/etc/snmp/snmpd.conf"
    system("service snmpd stop")
    system("sed -c -ie '/^createUser root/d' %s" % conf)
    f = open(conf, "a")
    # create user account
    f.write("createUser root SHA %s AES\n" % password)
    f.close()
    system("service snmpd start")
    ovirt_store_config(conf)

def disable_snmpd():
    system("service snmpd stop")
    remove_config("/etc/snmp/snmpd.conf")

def snmp_auto():
    if OVIRT_VARS.has_key("OVIRT_SNMP_PASSWORD"):
        enable_snmpd(OVIRT_VARS["OVIRT_SNMP_PASSWORD"])
