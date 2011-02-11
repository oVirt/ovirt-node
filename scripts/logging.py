#!/usr/bin/python
#
# Configures the rsyslog daemon.

import os
import sys
from ovirtnode.ovirtfunctions import *

RSYSLOG_FILE="/etc/rsyslog.conf"

RSYSLOG_CONFIG_TEMPLATE = """
#ovirt rsyslog config file

#### MODULES ####
$ModLoad imuxsock.so    # provides support for local system logging (e.g. via logger command)
$ModLoad imklog.so      # provides kernel logging support (previously done by rklogd)

#### GLOBAL DIRECTIVES ####
# Use default timestamp format
$ActionFileDefaultTemplate RSYSLOG_TraditionalFileFormat

#### RULES ####
# Log anything (except mail) of level info or higher.
# Don't log private authentication messages!
*.info;mail.none;authpriv.none;cron.none                /var/log/messages

# The authpriv file has restricted access.
authpriv.*                                              /var/log/secure

# Log all the mail messages in one place.
mail.*                                                  -/var/log/maillog

# Log cron stuff
cron.*                                                  /var/log/cron

# Everybody gets emergency messages
*.emerg                                                 *

# Save news errors of level crit and higher in a special file.
uucp,news.crit                                          /var/log/spooler

# Save boot messages also to boot.log
local7.*                                                /var/log/boot.log

$WorkDirectory /var/spool/rsyslog
$ActionQueueFileName ovirtNode
$ActionQueueMaxDiskSpace 10m
$ActionQueueSaveOnShutdown on
$ActionQueueType LinkedList
$ActionResumeRetryCount -1
*.* %(delim)s%(server)s:%(port)s
"""


def ovirt_rsyslog(server, port, protocol):
    if protocol == "tcp":
        DELIM="@@"
    else:
        DELIM="@"

    rsyslog_dict = {
        "delim" : DELIM,
        "server" : server,
        "port" : port
    }
    rsyslog_config_out = RSYSLOG_CONFIG_TEMPLATE % rsyslog_dict
    rsyslog_config = open(RSYSLOG_FILE, "w")
    rsyslog_config.write(rsyslog_config_out)
    rsyslog_config.close()
    os.system("/sbin/service rsyslog restart &> /dev/null")
    return True

def get_rsyslog_config():
    rsyslog_config = open(RSYSLOG_FILE)
    for line in rsyslog_config:
        if "@" in line:
            #strip excess details
            line = line.replace("*.* ", "")
            line = line.replace("@","")
            try:
                server, port = line.split(":")
                if not server.startswith("#"):
                    return (server,port.strip())
            except:
                log("rsyslog config parsing failed: %s") % line
                return

if len(sys.argv) > 1:
    try:
        if sys.argv[1] == "AUTO":
            if not OVIRT_VARS.has_key("OVIRT_SYSLOG_SERVER") or not OVIRT_VARS.has_key("OVIRT_SYSLOG_PORT"):
                
                log("\nAttempting to locate remote syslog server...")
                host, port = find_srv("syslog", "udp")
                if not host is None and not port is None:
                    log("found! Using syslog server " + host + ":" + port) 
                    ovirt_rsyslog(host, port, udp)
                else:
                    log("not found!\n")
            else:
                log("\nUsing default syslog server " + OVIRT_SYSLOG_SERVER + ":" + OVIRT_SYSLOG_PORT + ".\n")
                ovirt_rsyslog(OVIRT_VARS["OVIRT_SYSLOG_SERVER"], OVIRT_VAR["OVIRT_SYSLOG_PORT"], udp)
    except:
        log("Error configuring rsyslog server")
        sys.exit(1)
