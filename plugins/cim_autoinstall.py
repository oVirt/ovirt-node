#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# cim_autoinstall.py - Copyright (C) 2013 Red Hat, Inc.
# Written by hadong <hadong@redhat.com>
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

from ovirt.node.utils.console import TransactionProgress
from ovirt.node.setup.cim import cim_model
import ovirtnode.ovirtfunctions as _functions

args = _functions.get_cmdline_args()

cim_pw = args.get("cim_passwd")

if __name__ == "__main__":
    cim = cim_model.CIM()
    if len(cim_pw) > 0:
        cim.update(enabled=True)
        tx = cim.transaction(cim_password=cim_pw)
        TransactionProgress(tx, is_dry=False).run()
        # clear ovirt_cim_passwd from /etc/default/ovirt
        pw_keys = ("OVIRT_CIM_PASSWD")
        cim.clear(keys=pw_keys)
