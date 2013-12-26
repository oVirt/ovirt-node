#!/usr/bin/python
#
# log.py - Copyright (C) 2011 Red Hat, Inc.
# Written by Joey Boggs <jboggs@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.
#
# Configures the rsyslog daemon.

import logging
import ovirtnode.ovirtfunctions as _functions
from ovirt.node.utils import system

logger = logging.getLogger(__name__)


RSYSLOG_FILE = "/etc/rsyslog.conf"

RSYSLOG_CONFIG_TEMPLATE = """
#ovirt rsyslog config file

#### MODULES ####
# provides support for local system logging (e.g. via logger command)
$ModLoad imuxsock.so
# provides kernel logging support (previously done by rklogd)
$ModLoad imklog.so

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
        DELIM = "@@"
    else:
        DELIM = "@"

    if _functions.is_valid_ipv6(server):
        server = "[" + server + "]"

    rsyslog_dict = {
        "disable": disable,
        "delim": DELIM,
        "server": server,
        "port": port
    }
    rsyslog_config_out = RSYSLOG_CONFIG_TEMPLATE % rsyslog_dict
    rsyslog_config = open(RSYSLOG_FILE, "w")
    rsyslog_config.write(rsyslog_config_out)
    rsyslog_config.close()
    _functions.system_closefds("/sbin/service rsyslog restart &> /dev/null")
    if _functions.ovirt_store_config("/etc/rsyslog.conf"):
        logger.info("Syslog Configuration Updated")
    return True


def ovirt_netconsole(server, port):
    _functions.augtool("set", \
                       "/files/etc/sysconfig/netconsole/SYSLOGADDR", server)
    _functions.augtool("set", \
                       "/files/etc/sysconfig/netconsole/SYSLOGPORT", port)
    try:
        system.service("netconsole", "restart")
    except:
        raise RuntimeError("Failed to restart netconsole service. "
                           "Is the host resolvable?")
    if _functions.ovirt_store_config("/etc/sysconfig/netconsole"):
        logger.info("Netconsole Configuration Updated")
    return True


def get_rsyslog_config():
    rsyslog_config = open(RSYSLOG_FILE)
    for line in rsyslog_config:
        if "@" in line:
            #strip excess details
            line = line.replace("*.* ", "")
            line = line.replace("@", "")
            try:
                server, port = line.split(":")
                if not server.startswith("#"):
                    return (server, port.strip())
            except:
                # try ipv6 parsing
                try:
                    ip, port = line.split("]")
                    server = ip.replace("[", "")
                    port = port.replace(":", "")
                    if not server.startswith("#"):
                        return (server, port.strip())
                except:
                    logger.error("rsyslog config parsing failed " + line)
                    return


def syslog_auto():
    host = ""
    port = ""
    if (not "OVIRT_SYSLOG_SERVER" in _functions.OVIRT_VARS or
        not "OVIRT_SYSLOG_PORT" in _functions.OVIRT_VARS):
        logger.info("Attempting to locate remote syslog server...")
        try:
            host, port = _functions.find_srv("syslog", "udp")
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
        logger.info("Using default syslog server " +
                    _functions.OVIRT_VARS["OVIRT_SYSLOG_SERVER"] + ":" +
                    _functions.OVIRT_VARS["OVIRT_SYSLOG_PORT"] + ".")
        ovirt_rsyslog(_functions.OVIRT_VARS["OVIRT_SYSLOG_SERVER"],
                      _functions.OVIRT_VARS["OVIRT_SYSLOG_PORT"], "udp")
        return True


def netconsole_auto():
    host = ""
    port = ""
    if (not "OVIRT_NETCONSOLE_SERVER" in _functions.OVIRT_VARS or not
        "OVIRT_NETCONSOLE_PORT" in _functions.OVIRT_VARS):
        logger.info("Attempting to locate remote netconsole server...")
        try:
            host, port = _functions.find_srv("netconsole", "udp")
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
        logger.info("Using default netconsole server " +
                    _functions.OVIRT_VARS["OVIRT_NETCONSOLE_SERVER"] + ":" +
                    _functions.OVIRT_VARS["OVIRT_NETCONSOLE_PORT"] + ".")
        ovirt_netconsole(_functions.OVIRT_VARS["OVIRT_NETCONSOLE_SERVER"],
                         _functions.OVIRT_VARS["OVIRT_NETCONSOLE_PORT"])
        return True


def logrotate_auto():
    logroate_max_size = _functions.OVIRT_VARS["OVIRT_LOGROTATE_MAX_SIZE"]
    if not logroate_max_size is "":
        logger.info("Found! Using logroate_max_size " + logroate_max_size)
        from ovirt.node.config import defaults
        try:
            model = defaults.Logrotate()
            model.update(max_size=logroate_max_size)
            tx = model.transaction()
            tx()
        except:
            pass
        return True
    else:
        logger.warn("Invalid logrotate max size: %s" % logroate_max_size)
        return False


def logging_auto():
    try:
        logrotate_auto()
        logger.info("Logrotate size Configuration Completed")
    except:
        logger.warn("Logrotate size Configuration Failed")
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
