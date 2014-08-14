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
from ovirt.node.config.defaults import Netconsole, Syslog

logger = logging.getLogger(__name__)


def ovirt_rsyslog(server, port, protocol):
    s = Syslog()
    s.update(server=server, port=port)
    try:
        s.commit()
    except:
        return False
    return True


def ovirt_netconsole(server, port):
    n = Netconsole()
    n.update(server=server, port=port)
    try:
        n.commit()
    except:
        return False
    return True


def get_rsyslog_config():
    rsyslog_config = open(RSYSLOG_FILE)
    for line in rsyslog_config:
        if "@" in line:
            # strip excess details
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
    if ("OVIRT_SYSLOG_SERVER" not in _functions.OVIRT_VARS and
            "OVIRT_SYSLOG_PORT" not in _functions.OVIRT_VARS):
        logger.info("Attempting to locate remote syslog server...")
        try:
            port, host = _functions.find_srv("syslog", "udp")
        except:
            pass
        if host is not "" and port is not "":
            logger.info("Found! Using syslog server " + host + ":" + port)
            ovirt_rsyslog(host, port, "udp")
            return True
        else:
            logger.warn("Syslog server not found!")
            return False
    elif ("OVIRT_SYSLOG_SERVER" in _functions.OVIRT_VARS and
          "OVIRT_SYSLOG_PORT" not in _functions.OVIRT_VARS):
        logger.info("Using default syslog port 514")
        ovirt_rsyslog(_functions.OVIRT_VARS["OVIRT_SYSLOG_SERVER"],
                      "514", "udp")
        return True
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
    if ("OVIRT_NETCONSOLE_SERVER" not in _functions.OVIRT_VARS and
            "OVIRT_NETCONSOLE_PORT" not in _functions.OVIRT_VARS):
        logger.info("Attempting to locate remote netconsole server...")
        try:
            port, host = _functions.find_srv("netconsole", "udp")
        except:
            pass
        if host is not "" and port is not "":
            logger.info("Found! Using netconsole server " + host + ":" + port)
            ovirt_netconsole(host, port)
            return True
        else:
            logger.warn("Netconsole server not found!")
            return False
    elif ("OVIRT_NETCONSOLE_SERVER" in _functions.OVIRT_VARS and
          "OVIRT_NETCONSOLE_PORT" not in _functions.OVIRT_VARS):
        logger.info("Using default netconsole port 6666.")
        ovirt_netconsole(_functions.OVIRT_VARS["OVIRT_NETCONSOLE_SERVER"],
                         "6666")
        return True
    else:
        logger.info("Using default netconsole server " +
                    _functions.OVIRT_VARS["OVIRT_NETCONSOLE_SERVER"] + ":" +
                    _functions.OVIRT_VARS["OVIRT_NETCONSOLE_PORT"] + ".")
        ovirt_netconsole(_functions.OVIRT_VARS["OVIRT_NETCONSOLE_SERVER"],
                         _functions.OVIRT_VARS["OVIRT_NETCONSOLE_PORT"])
        return True


def logrotate_auto():
    logroate_max_size = _functions.OVIRT_VARS["OVIRT_LOGROTATE_MAX_SIZE"]
    if logroate_max_size is not "":
        logger.info("Found! Using logrotate_max_size " + logroate_max_size)
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
