#!/usr/bin/python
#
# Configures the collectd daemon.

import os
import sys
from ovirtnode.ovirtfunctions import *
from subprocess import Popen, PIPE, STDOUT

collectd_conf="/etc/collectd.conf"

def write_collectd_config(server, port):
    if os.path.exists(collectd_conf + ".in"):
        sed_cmd = "sed -e \"s/@COLLECTD_SERVER@/%s/\" \
            -e \"s/@COLLECTD_PORT@/%s/\" %s.in \
            > %s" % (server, port, collectd_conf, collectd_conf)
        sed = subprocess.Popen(sed_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    os.system("chkconfig collectd on &> /dev/null")
    os.system("service collectd restart &> /dev/null")
    return True

def get_collectd_config():
    collectd_config = open(collectd_conf)
    try:
        for line in collectd_config:
            if "Server" in line:
              start, config = line.split("Server ", 2)
              server, port = config.split()
              server = server.strip('"')
              return (server,port)
    except:
        return
# AUTO for auto-install
if len(sys.argv) > 1:
    if sys.argv[1] == "AUTO":
        if not OVIRT_VARS.has_key("OVIRT_COLLECTD_SERVER") or not OVIRT_VARS.has_key["OVIRT_COLLECTD_PORT"]:
            log("\nAttempting to locate remote collectd server...")
            host, port = find_srv("collectd", "udp")
            if not host is None and not port is None:
                log("found! Using collectd server " + host + ":" + port)
                ovirt_collectd(host, port)
            else:
                log("collectd server not found!\n")
        else:
            log("\nUsing default collectd server '$OVIRT_COLLECTD_SERVER:$OVIRT_COLLECTD_PORT'.\n")
            ovirt_collectd(OVIRT_VARS["OVIRT_COLLECTD_SERVER"], OVIRT_VARS["OVIRT_COLLECTD_PORT"])
