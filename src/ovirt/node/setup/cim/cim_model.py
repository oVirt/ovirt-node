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
from ovirt.node.exceptions import TransactionError
from ovirt.node.utils import process, system
import pwd
# pylint: disable-msg=E0611
import grp  # @UnresolvedImport
# pylint: enable-msg=E0611


class CIM(NodeConfigFileSection):
    """Configure CIM

    >>> from ovirt.node.utils import fs
    >>> n = CIM(fs.FakeFs.File("dst"))
    >>> n.update(True)
    >>> n.retrieve()
    {'enabled': True}
    """
    keys = ("OVIRT_CIM_ENABLED",)

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, enabled):
        return {"OVIRT_CIM_ENABLED":
                "1" if utils.parse_bool(enabled) else None}

    def retrieve(self):
        cfg = dict(NodeConfigFileSection.retrieve(self))
        cfg.update({"enabled":
                    True if cfg["enabled"] == "1" else None})
        return cfg

    def transaction(self, cim_password):
        cfg = self.retrieve()
        enabled = cfg["enabled"]

        tx = utils.Transaction("Configuring CIM")

        class ConfigureCIM(utils.Transaction.Element):
            title = "Enabling CIM" if enabled else "Disabling CIM"

            def commit(self):
                action = "restart" if enabled else "stop"
                try:
                    system.service("ovirt-cim", action)
                    self.logger.debug("Configured CIM successfully")
                except RuntimeError:
                    raise TransactionError("CIM configuration failed")

        class SetCIMPassword(utils.Transaction.Element):
            title = "Setting CIM password"

            def commit(self):
                create_cim_user()

                if not cim_password:
                    raise RuntimeError("CIM password is missing.")

                from ovirtnode.password import set_password
                if not set_password(cim_password, "cim"):
                    raise RuntimeError("Setting CIM Password Failed")

        tx.append(ConfigureCIM())
        if enabled:
            tx.append(SetCIMPassword())

        return tx


def create_cim_user(username="cim",
                    shell="/sbin/nologin",
                    main_group="cim",
                    group_list=["sfcb"]):
    from ovirtnode.ovirtfunctions import check_user_exists, add_user
    if not check_user_exists(username):
        add_user(username, shell, main_group, group_list)
    else:
        userinfo = pwd.getpwnam(username)
        if not userinfo.pw_gid == grp.getgrnam(main_group).gr_gid:
            process.check_call("usermod -g %s %s" %
                               (main_group, username), shell=True)
        if not userinfo.pw_shell == shell:
            process.check_call("usermod -s %s %s" %
                               (shell, username), shell=True)
        for group in group_list:
            if username not in grp.getgrnam(group).gr_mem:
                process.check_call("usermod -G %s %s" %
                                   (",".join(group_list), username),
                                   shell=True)
                break
