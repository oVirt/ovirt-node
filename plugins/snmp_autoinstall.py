#!/usr/bin/python
# snmp_autoinstall.py - Copyright (C) 2012 Red Hat, Inc.
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

from ovirt.node.utils.console import TransactionProgress
from ovirt.node.setup.snmp import snmp_model
import ovirtnode.ovirtfunctions as _functions

args = _functions.get_cmdline_args()

snmp_pw = args.get("snmp_password")

if __name__ == "__main__":
    snmp = snmp_model.SNMP()
    if len(snmp_pw) > 0:
        snmp.update(enabled=True)
        tx = snmp.transaction(snmp_password=snmp_pw)
        TransactionProgress(tx, is_dry=False).run()
        # clear ovirt_snmp_passwd from /etc/default/ovirt
        pw_keys = ("OVIRT_SNMP_PASSWORD",)
        snmp.clear(keys=pw_keys)
