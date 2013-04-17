#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# virt.py - Copyright (C) 2012 Red Hat, Inc.
# Written by Fabian Deutsch <fabiand@redhat.com>
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

"""
Some convenience functions related to virtualization
"""

import os.path
import libvirt

from ovirt.node import base


def hardware_is_available():
    """Determins if virtualization hardware is available.
    This does not mean that virtualization is also enabled.

    Returns:
        True if there is hardware virtualization hardware available
    """
    is_available = False

    with open("/proc/cpuinfo") as cpuinfo:
        for line in cpuinfo:
            if line.startswith("flags"):
                if "vmx" in line or "svm" in line:
                    is_available = True
    return is_available


def hardware_is_enabled():
    """Determins if virtualization hardware is available and enabled.

    Returns:
        True if there is hardware virtualization hardware available and enabled
    """
    is_enabled = False

    if hardware_is_available():
        has_module = False
        with open("/proc/modules") as modules:
            for line in modules:
                has_module = (line.startswith("kvm_intel") or
                              line.startswith("kvm_amd"))
                if has_module:
                    break

        if has_module and os.path.exists("/dev/kvm"):
            is_enabled = True

    return is_enabled


def hardware_status():
    """Status of virtualization on this machine.

    Returns:
        Status of hardware virtualization support on this machine as a human
        read-able string
    """
    if hardware_is_enabled():
        return "Virtualization hardware was detected and is enabled"
    if hardware_is_available():
        return "Virtualization hardware was detected but is disabled"
    return "No virtualization hardware was detected on this system"


def number_of_domains():
    # FIXME solve this more general
    num_domains = None
    try:
        with LibvirtConnection() as con:
            num_domains = str(con.numOfDomains())
    except libvirt.libvirtError:
        pass
        #warning("Error while working with libvirt: %s" % e.message)
    return num_domains


class LibvirtConnection(base.Base):
    con = None

    def __init__(self, readonly=True):
        super(LibvirtConnection, self).__init__()
        self.connect(readonly)

    def connect(self, readonly):
        if readonly:
            self.con = libvirt.openReadOnly(None)
        else:
            raise Exception("Not supported")

    def __enter__(self, *args, **kwargs):
        return self.con

    def __exit__(self, *args, **kwargs):
        self.con.close()
