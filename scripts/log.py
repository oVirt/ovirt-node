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
%(disable)s*.* %(delim)s%(server)s:%(port)s
"""


def ovirt_rsyslog(server, port, protocol):
    if server == "":
        disable = "#"
    else:
        disable = ""
    if protocol == "tcp":
        DELIM="@@"
    else:
        DELIM="@"

    if is_valid_ipv6(server):
        server = "[" + server + "]"

    rsyslog_dict = {
        "disable" : disable,
        "delim" : DELIM,
        "server" : server,
        "port" : port
    }
    rsyslog_config_out = RSYSLOG_CONFIG_TEMPLATE % rsyslog_dict
    rsyslog_config = open(RSYSLOG_FILE, "w")
    rsyslog_config.write(rsyslog_config_out)
    rsyslog_config.close()
    os.system("/sbin/service rsyslog restart &> /dev/null")
    if ovirt_store_config("/etc/rsyslog.conf"):
        logger.info("Syslog Configuration Updated")
    return True

def ovirt_netconsole(server, port):
    augtool("set","/files/etc/sysconfig/netconsole/SYSLOGADDR", server)
    augtool("set","/files/etc/sysconfig/netconsole/SYSLOGPORT", port)
    os.system("/sbin/service netconsole restart &> /dev/null")
    if ovirt_store_config("/etc/sysconfig/netconsole"):
        logger.info("Netconsole Configuration Updated")
    return True


def set_logrotate_size(size):
     try:
         augtool("set", "/files/etc/logrotate.d/ovirt-node/rule/size", size)
         ovirt_store_config("/etc/logrotate.d/ovirt-node")
         return True
     except:
        return False

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
                # try ipv6 parsing
                try:
                    ip, port = line.split("]")
                    server = ip.replace("[","")
                    port = port.replace(":","")
                    if not server.startswith("#"):
                        return (server,port.strip())
                except:
                    logger.error("rsyslog config parsing failed " + line)
                    return

def syslog_auto():
    host = ""
    port = ""
    if not OVIRT_VARS.has_key("OVIRT_SYSLOG_SERVER") or not OVIRT_VARS.has_key("OVIRT_SYSLOG_PORT"):
        logger.info("Attempting to locate remote syslog server...")
        try:
            host, port = find_srv("syslog", "udp")
        except:
            pass
        if not host is "" and not port is "":
            logger.info("Found! Using syslog server " + host + ":" + port)
            ovirt_rsyslog(host, port, "udp")
            return True
        else:
            logger.warn("Syslog server not found!")
            return False
    else:
        logger.info("Using default syslog server " + OVIRT_VARS["OVIRT_SYSLOG_SERVER"] + ":" + OVIRT_VARS["OVIRT_SYSLOG_PORT"] + ".")
        ovirt_rsyslog(OVIRT_VARS["OVIRT_SYSLOG_SERVER"], OVIRT_VARS["OVIRT_SYSLOG_PORT"], "udp")
        return True

def netconsole_auto():
    host = ""
    port = ""
    if not OVIRT_VARS.has_key("OVIRT_NETCONSOLE_SERVER") or not OVIRT_VARS.has_key("OVIRT_NETCONSOLE_PORT"):
        logger.info("Attempting to locate remote netconsole server...")
        try:
            host, port = find_srv("netconsole", "udp")
        except:
            pass
        if not host is "" and not port is "":
            logger.info("Found! Using netconsole server " + host + ":" + port)
            ovirt_netconsole(host, port)
            return True
        else:
            logger.warn("Netconsole server not found!")
            return False
    else:
        logger.info("Using default netconsole server " + OVIRT_VARS["OVIRT_NETCONSOLE_SERVER"] + ":" + OVIRT_VARS["OVIRT_NETCONSOLE_PORT"] + ".")
        ovirt_netconsole(OVIRT_VARS["OVIRT_NETCONSOLE_SERVER"], OVIRT_VARS["OVIRT_NETCONSOLE_PORT"])
        return True

def logging_auto():
    try:
        syslog_auto()
        logger.info("Syslog Configuration Completed")
    except:
        logger.warn("Syslog Configuration Failed")
    try:
        netconsole_auto()
        logger.info("Syslog Configuration Completed")
    except:
        logger.warn("Netconsole Configuration Failed")
