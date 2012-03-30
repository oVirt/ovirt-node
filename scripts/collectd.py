#!/usr/bin/python
#
# collectd.py - Copyright (C) 2011 Red Hat, Inc.
# Written by Alan Pevec <apevec@redhat.com>
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
# Configures the collectd daemon.

import os
import sys
from ovirtnode.ovirtfunctions import *
from subprocess import Popen, PIPE, STDOUT
from snack import *
import _snack

collectd_conf = "/etc/collectd.conf"


def write_collectd_config(server, port):
    if os.path.exists(collectd_conf + ".in"):
        sed_cmd = "sed -e \"s/@COLLECTD_SERVER@/%s/\" \
            -e \"s/@COLLECTD_PORT@/%s/\" %s.in \
            > %s" % (server, port, collectd_conf, collectd_conf)
        sed = subprocess_closefds(sed_cmd, shell=True, stdout=PIPE,
              stderr=STDOUT)
    system_closefds("chkconfig collectd on &> /dev/null")
    system_closefds("service collectd restart &> /dev/null")
    return True


def get_collectd_config():
    collectd_config = open(collectd_conf)
    try:
        for line in collectd_config:
            if "Server" in line:
                start, config = line.split("Server ", 2)
                server, port = config.split()
                server = server.strip('"')
                return (server, port)
    except:
        return
    finally:
        collectd_config.close()


# AUTO for auto-install
def collectd_auto():
    host = ""
    port = ""
    if (("OVIRT_COLLECTD_SERVER" not in OVIRT_VARS)
        or ("OVIRT_COLLECTD_PORT" not in OVIRT_VARS)):
        logger.info("Attempting to locate remote collectd server...")
        try:
            host, port = find_srv("collectd", "udp")
        except:
            pass
        if not host is "" and not port is "":
            logger.info("collectd server found! Using collectd server " +
                        host + ":" + port)
            write_collectd_config(host, port)
            return True
        else:
            logger.error("collectd server not found!")
            return False
    else:
        logger.info("Using default collectd server: " +
                    OVIRT_VARS["OVIRT_COLLECTD_SERVER"] + " : " +
                    OVIRT_VARS["OVIRT_COLLECTD_PORT"])
        write_collectd_config(OVIRT_VARS["OVIRT_COLLECTD_SERVER"],
                              OVIRT_VARS["OVIRT_COLLECTD_PORT"])
        return True


#
# configuration UI plugin interface
#
class Plugin(PluginBase):
    """Plugin for Monitoring configuration option.
    """

    def __init__(self, ncs):
        PluginBase.__init__(self, "Monitoring", ncs)

    def form(self):
        elements = Grid(2, 10)
        elements.setField(Label("Monitoring Configuration"), 0, 0,
                                anchorLeft=1)
        elements.setField(Label(""), 0, 1, anchorLeft=1)
        elements.setField(Label("Collectd"), 0, 2, anchorLeft=1)
        elements.setField(Textbox(45, 3, "Collectd gathers statistics about "
                                       + "the system that\ncan be used to "
                                       + "find performance bottlenecks\nand "
                                       + "predict future system load."),
                          0, 3, anchorLeft=1)
        collectd_grid = Grid(2, 2)
        collectd_grid.setField(Label("Server Address:"), 0, 0, anchorLeft=1)
        self.collectd_server = Entry(20, "")
        self.collectd_server.setCallback(self.valid_collectd_server_callback)
        collectd_grid.setField(self.collectd_server, 1, 0, anchorLeft=1,
                               padding=(2, 0, 0, 1))
        self.collectd_port = Entry(5, "")
        self.collectd_port.setCallback(self.valid_collectd_port_callback)
        collectd_grid.setField(Label("Server Port:"), 0, 1, anchorLeft=1)
        collectd_grid.setField(self.collectd_port, 1, 1, anchorLeft=1,
                               padding=(2, 0, 0, 1))
        elements.setField(collectd_grid, 0, 4, anchorLeft=1,
                          padding=(0, 1, 0, 0))
        collectd_config = get_collectd_config()
        if not collectd_config is None:
            collectd_server, collectd_port = get_collectd_config()
            self.collectd_server.set(collectd_server)
            self.collectd_port.set(collectd_port)
        else:
            self.collectd_port.set("7634")
        return [Label(""), elements]

    def action(self):
        self.ncs.screen.setColor("BUTTON", "black", "red")
        self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
        if ((len(self.collectd_server.value()) > 0)  and
            (len(self.collectd_port.value()) > 0)):
            if write_collectd_config(self.collectd_server.value(),
                                     self.collectd_port.value()):
                ButtonChoiceWindow(self.ncs.screen, "Collectd Configuration",
                                   "Collectd Configuration Successfully " +
                                   "Changed", buttons=['Ok'])
                self.ncs.reset_screen_colors()
                return True
            else:
                ButtonChoiceWindow(self.ncs.screen, "Collectd Configuration",
                                   "Collectd Configuration Failed",
                                   buttons=['Ok'])
                self.ncs.reset_screen_colors()
                return False

    def valid_collectd_server_callback(self):
        if not is_valid_host_or_ip(self.collectd_server.value()):
            self.ncs.screen.setColor("BUTTON", "black", "red")
            self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
            ButtonChoiceWindow(self.ncs.screen, "Configuration Check",
                               "Invalid Hostname or Address", buttons=['Ok'])
            self.ncs.reset_screen_colors()

    def valid_collectd_port_callback(self):
        if not is_valid_port(self.collectd_port.value()):
            self.ncs.screen.setColor("BUTTON", "black", "red")
            self.ncs.screen.setColor("ACTBUTTON", "blue", "white")
            ButtonChoiceWindow(self.ncs.screen, "Configuration Check",
                               "Invalid Port Number", buttons=['Ok'])
            self.ncs.reset_screen_colors()


def get_plugin(ncs):
    return Plugin(ncs)
