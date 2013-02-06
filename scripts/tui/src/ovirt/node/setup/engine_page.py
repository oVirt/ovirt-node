#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# engine_page.py - Copyright (C) 2012 Red Hat, Inc.
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
import sys
from ovirt.node import plugins, valid, ui, utils
from ovirt.node.config.defaults import NodeConfigFileSection
from ovirt.node.plugins import Changeset

"""
Configure Engine
"""


class Plugin(plugins.NodePlugin):
    def name(self):
        return "oVirt Engine"

    def rank(self):
        return 100

    def model(self):
        model = {
            "vdsm_cfg.address": "",
            "vdsm_cfg.port": "443",
            "vdsm_cfg.connect_and_validate": True,
            "vdsm_cfg.password": "",
            "vdsm_cfg.password_confirmation": "",
        }
        return model

    def validators(self):
        same_as_password = plugins.Validator.SameAsIn(self,
                                                      "vdsm_cfg.password",
                                                      "Password")
        return {"vdsm_cfg.address": valid.FQDNOrIPAddress() | valid.Empty(),
                "vdsm_cfg.port": valid.Port(),
                "vdsm_cfg.password": valid.Text(),
                "vdsm_cfg.password_confirmation": same_as_password,
                }

    def ui_content(self):
        ws = [ui.Header("header[0]", "oVirt Engine Configuration"),
              ui.Entry("vdsm_cfg.address", "Management Server:"),
              ui.Entry("vdsm_cfg.port", "Management Server Port:"),
              ui.Divider("divider[0]"),
              ui.Checkbox("vdsm_cfg.connect_and_validate",
                          "Connect to oVirt Engine and Validate Certificate"),
              ui.Divider("divider[1]"),
              ui.Label("vdsm_cfg.password._label",
                       "Optional password for adding Node through oVirt " +
                       "Engine UI"),
              ui.PasswordEntry("vdsm_cfg.password", "Password:"),
              ui.PasswordEntry("vdsm_cfg.password_confirmation",
                               "Confirm Password:"),
              ]
        # Save it "locally" as a dict, for better accessability
        self.widgets.add(ws)

        page = ui.Page("page", ws)
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        self.logger.info("Saving engine stuff")
        changes = Changeset(self.pending_changes(False))
        effective_model = Changeset(self.model())
        effective_model.update(effective_changes)

        self.logger.debug("Changes: %s" % changes)
        self.logger.debug("Effective Model: %s" % effective_model)

        txs = utils.Transaction("Configuring oVirt Engine")

        vdsm_keys = ["vdsm_cfg.address", "vdsm_cfg.port"]
        if changes.contains_any(vdsm_keys):
            values = effective_model.values_for(vdsm_keys)
            self.logger.debug("Setting VDSM server and port (%s)" % values)

            # Use the VDSM class below to build a transaction
            model = VDSM()
            model.update(*values)
            txs += model.transaction()

        if changes.contains_any(["vdsm_cfg.password_confirmation"]):
            self.logger.debug("Setting engine password")
            txs += [SetEnginePassword()]

        if effective_model.contains_any(["vdsm_cfg.connect_and_validate"]):
            self.logger.debug("Connecting to engine")
            txs += [ActivateVDSM(changes["vdsm_cfg.connect_and_validate"])]

        progress_dialog = ui.TransactionProgressDialog("dialog.txs", txs, self)
        progress_dialog.run()

        # Acts like a page reload
        return self.ui_content()


#
#
# Functions and classes to support the UI
#
#

class VDSM(NodeConfigFileSection):
    """Class to handle VDSM configuration in /etc/default/ovirt file

    >>> from ovirt.node.config.defaults import ConfigFile, SimpleProvider
    >>> fn = "/tmp/cfg_dummy"
    >>> cfgfile = ConfigFile(fn, SimpleProvider)
    >>> n = VDSM(cfgfile)
    >>> n.update("engine.example.com", "1234")
    >>> sorted(n.retrieve().items())
    [('port', '1234'), ('server', 'engine.example.com')]
    """
    keys = ("OVIRT_MANAGEMENT_SERVER",
            "OVIRT_MANAGEMENT_PORT")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, server, port):
        (valid.Empty() | valid.FQDNOrIPAddress())(server)
        (valid.Empty() | valid.Port())(port)

    def transaction(self):
        cfg = dict(self.retrieve())
        server, port = (cfg["server"], cfg["port"])

        class ConfigureVDSM(utils.Transaction.Element):
            title = "Setting VDSM server and port"

            def commit(self):
                self.logger.info("Setting: %s:%s" % (server, port))

        tx = utils.Transaction("Configuring VDSM")
        tx.append(ConfigureVDSM())

        return tx


class SetRootPassword(utils.Transaction.Element):
    title = "Setting root password and starting sshd"

    def __init__(self, password):
        super(SetRootPassword, self).__init__()
        self.password = password

    def commit(self):
        passwd = utils.security.Passwd()
        passwd.set_password("root", self.password)

        sshd = utils.security.Ssh()
        sshd.password_authentication(True)
        sshd.restart()


class ActivateVDSM(utils.Transaction.Element):
    title = "Activating VDSM"

    def __init__(self, verify_engine_cert):
        super(ActivateVDSM, self).__init__()
        self.vdsm_cfg = VDSM()
        self.verify_engine_cert = verify_engine_cert

    def prepare(self):
        """Ping the management server before we try to activate
        the connection to it
        """
        cfg = dict(self.vdsm_cfg.retrieve())
        self.engineServer = cfg["server"]
        self.enginePort = cfg["port"]
        if self.engineServer:
            newPort = self.__prepare_server(self.engineServer, self.enginePort)
            self.enginePort = newPort

    def __prepare_server(self, engineServer, enginePort):
        # pylint: disable-msg=E0611,F0401
        sys.path.append('/usr/share/vdsm-reg')
        import deployUtil  # @UnresolvedImport

        from ovirt_config_setup.engine import \
            isHostReachable  # @UnresolvedImport
        from ovirt_config_setup.engine import \
            TIMEOUT_FIND_HOST_SEC  # @UnresolvedImport
        from ovirt_config_setup.engine import \
            compatiblePort  # @UnresolvedImport
        # pylint: enable-msg=E0611,F0401

        compatPort, sslPort = compatiblePort(self.enginePort)

        deployUtil.nodeCleanup()
        if not isHostReachable(host=engineServer,
                               port=enginePort, ssl=sslPort,
                               timeout=TIMEOUT_FIND_HOST_SEC):
            if compatPort is None:
                # Try one more time with SSL=False
                if not isHostReachable(host=engineServer,
                                       port=enginePort, ssl=False,
                                       timeout=TIMEOUT_FIND_HOST_SEC):
                    msgConn = "Can't connect to @ENGINENAME@ in the " + \
                              "specific port %s" % enginePort
                    raise RuntimeError(msgConn)
            else:
                msgConn = "Can't connect to @ENGINENAME@ port %s," \
                    " trying compatible port %s" % \
                    (enginePort, compatPort)

                #  FIXME self.notice(msgConn)

                if not isHostReachable(host=self.engineServer,
                                       port=compatPort, ssl=sslPort,
                                       timeout=TIMEOUT_FIND_HOST_SEC):
                    msgConn = "Can't connect to @ENGINENAME@ using" \
                        " compatible port %s" % compatPort
                    raise RuntimeError(msgConn)
                else:
                    # compatible port found
                    enginePort = compatPort

        return enginePort

    def commit(self):
        self.logger.info("Connecting to VDSM server")

        from ovirtnode.ovirtfunctions import ovirt_store_config

        # pylint: disable-msg=E0611,F0401
        sys.path.append('/usr/share/vdsm-reg')
        import deployUtil  # @UnresolvedImport

        sys.path.append('/usr/share/vdsm')
        from vdsm import constants  # @UnresolvedImport

        from ovirt_config_setup.engine import \
            write_vdsm_config  # @UnresolvedImport
        # pylint: enable-msg=E0611,F0401

        if self.verify_engine_cert:
            if deployUtil.getRhevmCert(self.engineServer,
                                       self.enginePort):
                _, _, path = deployUtil.certPaths('')
                #fp = deployUtil.generateFingerPrint(path)
                #
                # FIXME
                #
                # a) Allow interactive confirmation of key
                # b) Remind to verify key (with dialog on ui.Page)
                #
                ovirt_store_config(path)
            else:
                msgCert = "Failed downloading @ENGINENAME@ certificate"
                raise RuntimeError(msgCert)
        # Stopping vdsm-reg may fail but its ok - its in the case when the
        # menus are run after installation
        deployUtil._logExec([constants.EXT_SERVICE, 'vdsm-reg', 'stop'])
        if write_vdsm_config(self.engineServer, self.enginePort):
            deployUtil._logExec([constants.EXT_SERVICE, 'vdsm-reg',
                                 'start'])

            msgConf = "@ENGINENAME@ Configuration Successfully Updated"
            self.logger.debug(msgConf)
        else:
            msgConf = "@ENGINENAME@ Configuration Failed"
            raise RuntimeError(msgConf)


class SetEnginePassword(utils.Transaction.Element):
    title = "Setting Engine password"

    def commit(self):
        self.logger.info("Setting Engine password")
