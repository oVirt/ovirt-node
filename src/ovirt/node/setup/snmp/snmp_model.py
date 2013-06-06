#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# cim.py - Copyright (C) 2013 Red Hat, Inc.
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
from ovirt.node import utils
from ovirt.node.config.defaults import NodeConfigFileSection
from ovirt.node.utils import process
import os.path


snmp_conf = "/etc/snmp/snmpd.conf"


def enable_snmpd(password):
    from ovirtnode.ovirtfunctions import ovirt_store_config

    process.call("service snmpd stop")

    # get old password #
    if os.path.exists("/tmp/snmpd.conf"):
        conf = "/tmp/snmpd.conf"
    else:
        conf = snmp_conf
    cmd = "cat %s|grep createUser|awk '{print $4}'" % conf
    oldpwd, stderr = process.pipe(cmd)
    oldpwd = oldpwd.stdout.read().strip()
    process.call("sed -c -ie '/^createUser root/d' %s" % snmp_conf)
    f = open(snmp_conf, "a")
    # create user account
    f.write("createUser root SHA %s AES\n" % password)
    f.close()
    process.check_call("service snmpd start")
    # change existing password
    if len(oldpwd) > 0:
        pwd_change_cmd = (("snmpusm -v 3 -u root -n \"\" -l authNoPriv -a " +
                           "SHA -A %s localhost passwd %s %s -x AES") %
                          (oldpwd, oldpwd, password))
        process.check_call(pwd_change_cmd)
        # Only reached when no excepion occurs
        process.call("rm -rf /tmp/snmpd.conf")
    ovirt_store_config(snmp_conf)


def disable_snmpd():
    from ovirtnode.ovirtfunctions import remove_config

    process.check_call("service snmpd stop")
    # copy to /tmp for enable/disable toggles w/o reboot
    process.check_call("cp /etc/snmp/snmpd.conf /tmp")
    process.check_call("sed -c -ie '/^createUser root/d' %s" % snmp_conf)
    remove_config(snmp_conf)


class SNMP(NodeConfigFileSection):
    """Configure SNMP

    >>> from ovirt.node.config.defaults import NodeConfigFile
    >>> n = SNMP("/tmp/cfg_dummy")
    >>> n.update("secret")
    >>> n.retrieve().items()
    [('password', 'secret')]
    """
    keys = ("OVIRT_SNMP_PASSWORD",)

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, password):
        # FIXME add validation
        pass

    def transaction(self):
        cfg = dict(self.retrieve())
        password = cfg["password"]

        class ConfigureSNMP(utils.Transaction.Element):
            title = "Enabling/Disabling SNMP and setting the password"

            def commit(self):
                # FIXME snmp plugin needs to be placed somewhere else (in src)
                # pylint: disable-msg=E0611
                from ovirt_config_setup import snmp  # @UnresolvedImport
                # pylint: enable-msg=E0611
                if password:
                    snmp.enable_snmpd(password)
                else:
                    snmp.disable_snmpd()

        tx = utils.Transaction("Configuring SNMP")
        tx.append(ConfigureSNMP())
        return tx
