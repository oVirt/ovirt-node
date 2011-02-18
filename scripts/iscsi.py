#!/usr/bin/env python
#
# iscsi.py - Copyright (C) 2011 Red Hat, Inc.
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

import os
from ovirtnode.ovirtfunctions import *

INITIATOR_FILE="/etc/iscsi/initiatorname.iscsi"

def set_iscsi_initiator(initiator_name):
    iscsi_config = open(INITIATOR_FILE, "w")
    iscsi_config.write("InitiatorName=" + initiator_name + "\n")
    iscsi_config.close()
    if ovirt_store_config(INITIATOR_FILE):
        log("Initiator name set as: " + initiator_name)
    else:
        log("Setting initiator name failed\n")
    os.system("service iscsi restart &> /dev/null")

def get_current_iscsi_initiator_name():
    iscsi_config = open(INITIATOR_FILE)
    initiator_name = ""
    for line in iscsi_config:
        if "InitiatorName" in line:
            initiator_name = line.replace("InitiatorName=","")
            return initiator_name.strip()
    
