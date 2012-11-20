#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# security.py - Copyright (C) 2012 Red Hat, Inc.
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
Some convenience functions related to security
"""

import os.path

import process


def get_ssh_hostkey(variant="rsa"):
    fn_hostkey = "/etc/ssh/ssh_host_%s_key.pub" % variant
    if not os.path.exists(fn_hostkey):
        raise Exception("SSH hostkey does not yet exist.")

    with open(fn_hostkey) as hkf:
        hostkey = hkf.read()

    hostkey_fp_cmd = "ssh-keygen -l -f '%s'" % fn_hostkey
    stdout = process.pipe(hostkey_fp_cmd, without_retval=True)
    fingerprint = stdout.strip().split(" ")[1]
    return (fingerprint, hostkey)
