
from ovirtnode.ovirtfunctions import *
import os

def enable_snmpd(password):
    CONF="/var/lib/net-snmp/snmpd.conf"
    ovirt_store_config("/etc/sysconfig/snmpd")
    ovirt_store_config("/var/lib/net-snmp")
    system("service snmpd stop")
    # reset snmpd options to defaults, image has "-v" to prevent snmpd start
    system("sed -c -ie '/^OPTIONS/d' /etc/sysconfig/snmpd")
    if os.path.exists(CONF):
        system("sed -c -ie '/^createUser root/d' %s" % CONF)
    f = open("/etc/sysconfig/snmpd", "a")
    f.write("createUser root SHA %s AES" % password)
    f.close()
    system("service snmpd start")

def disable_snmpd():
    system("service snmpd stop")
    system("umount /etc/sysconfig/snmpd")
    remove_config("/etc/sysconfig/snmpd")

def snmp_auto():
    if OVIRT_VARS.has_key("OVIRT_SNMP_PASSWORD"):
        enable_snmpd(OVIRT_VARS["OVIRT_SNMP_PASSWORD"])
