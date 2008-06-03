#!/usr/bin/python -Wall
# 
# Copyright (C) 2008 Red Hat, Inc.
# Written by Darryl L. Pierce <dpierce@redhat.com>
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

import socket
import libvirt
import sys
import os

class IdentifyNode:
    """This class allows the managed node to connect to the WUI host
    and notify it that the node is awake and ready to participate."""

    def __init__(self, server_name, server_port):
        conn = libvirt.openReadOnly(None)
        info = conn.getInfo()
        self.host_info = {
            "UUID"     : "foo",
            "ARCH"     : info[0],
            "MEMSIZE"  : "%d" % info[1],
            "NUMCPUS"  : "%d" % info[2],
            "CPUSPEED" : "%d" % info[3],
            "HOSTNAME" : conn.getHostname()
            }

        print(self.host_info)
        
        self.server_name = server_name
        self.server_port = int(server_port)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.server_name,self.server_port))
        self.input  = self.socket.makefile('rb', 0)
        self.output = self.socket.makefile('wb', 0)

    def start_conversation(self):
        print("Connecting to server")

        response = self.input.readline().strip()
        if response == 'HELLO?':
            self.output.write("HELLO!\n")
        else:
            raise TypeError, "Received invalid conversation starter: %s" % response

    def send_host_info(self):
        print("Starting information exchange...")

        response = self.input.readline().strip()
        if response == 'INFO?':
            for name in self.host_info.keys():
                self.send_host_info_element(name,self.host_info[name])
        else:
            raise TypeError, "Received invalid info marker: %s" % response

        print("Ending information exchange...")
        self.output.write("ENDINFO\n")
        response = self.input.readline().strip()

        if response[0:4] == 'KVNO':
            self.keytab = response[:5]
        else:
            raise TypeError, "Did not receive a keytab response: '%s'" % response

    def send_host_info_element(self,key,value):
        print("Sending: " + key + "=" + value)
        self.output.write(key + "=" + value + "\n")
        response = self.input.readline().strip()

        if response != "ACK " + key:
            raise TypeError, "Received bad acknolwedgement for field: %s" % key

    def get_keytab(self):
        print("Retrieving keytab information: %s" % self.keytab)

    def end_conversation(self):
        print("Disconnecting from server")


if __name__ == '__main__': 
    
    identifier = IdentifyNode(sys.argv[1], sys.argv[2])

    identifier.start_conversation()
    identifier.send_host_info()
    identifier.get_keytab()
    identifier.end_conversation()
