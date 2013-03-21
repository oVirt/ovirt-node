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
from ovirt.node import plugins, valid, ui, utils, app
from ovirt.node.config.defaults import NodeConfigFileSection
from ovirt.node.plugins import Changeset
import logging
import os
import sys
import traceback
import httplib

"""
Configure Engine
"""


LOGGER = logging.getLogger(__name__)


class Plugin(plugins.NodePlugin):
    _cert_path = None
    _server = None
    _port = None

    def name(self):
        return "oVirt Engine"

    def rank(self):
        return 100

    def model(self):
        cfg = VDSM().retrieve()
        model = {
            "vdsm_cfg.address": cfg["server"] or "",
            "vdsm_cfg.port": cfg["port"] or "443",
            "vdsm_cfg.cert": "Verified"
            if utils.fs.Config().exists(cfg["cert_path"]) else "N/A",
            "vdsm_cfg.password": "",
            "vdsm_cfg.password_confirmation": ""
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
              ui.SaveButton("action.fetch_cert", "Retrieve Certificate"),
              ui.KeywordLabel("vdsm_cfg.cert", "Certificate Status: "),
              ui.Divider("divider[1]"),
              ui.Label("vdsm_cfg.password._label",
                       "Optional password for adding Node through oVirt " +
                       "Engine UI"),
              ui.PasswordEntry("vdsm_cfg.password", "Password:"),
              ui.PasswordEntry("vdsm_cfg.password_confirmation",
                               "Confirm Password:"),
              ]

        page = ui.Page("page", ws)
        page.buttons = [ui.SaveButton("action.register", "Save & Register")]

        self.widgets.add(page)
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

        if changes.contains_any(["action.fetch_cert"]):
            buttons = [ui.Button("action.cert.accept", "Accept"),
                       ui.Button("action.cert.reject", "Reject & Remove")]

            try:
                server = effective_model["vdsm_cfg.address"]
                port = findPort(server, effective_model["vdsm_cfg.port"])
                self._cert_path, fingerprint = retrieveCetrificate(server,
                                                                   port)
                self._server, self._port = server, port
            except Exception as e:
                fingerprint = str(e)
                buttons = [ui.Button("action.cert.reject", "Close")]

            self._fp_dialog = ui.Dialog("dialog.engine.fp",
                                        "@ENGINENAME@ Fingerprint",
                                        [ui.Label("dialog.label[0]", "TBD"),
                                         ui.Label("dialog.fp", fingerprint)])
            self._fp_dialog.buttons = buttons
            return self._fp_dialog

        elif changes.contains_any(["action.cert.accept"]):
            self._fp_dialog.close()
            model = VDSM()
            model.update(self._server, self._port, self._cert_path)
            utils.fs.Config().persist(self._cert_path)
            self._server, self._port, self._cert_path = None, None, None

        elif changes.contains_any(["action.cert.reject"]):
            model = VDSM()
            model.update(cert_path=None)
            utils.fs.Config().unpersist(self._cert_path)
            os.unlink(self._cert_path)
            self._fp_dialog.close()
            self._server, self._port, self._cert_path = None, None, None

        txs = utils.Transaction("Configuring oVirt Engine")

        if changes.contains_any(["vdsm_cfg.password_confirmation"]):
            self.logger.debug("Setting engine password")
            txs += [SetEnginePassword()]

        if effective_changes.contains_any(["action.register"]) and \
                changes.contains_any(["vdsm_cfg.address"]):
            self.logger.debug("Connecting to engine")
            txs += [ActivateVDSM()]

        if len(txs) > 0:
            progress_dialog = ui.TransactionProgressDialog("dialog.txs", txs,
                                                           self)
            progress_dialog.run()

            # VDSM messes with logging, and we just reset it
            app.configure_logging()

        # Acts like a page reload
        return self.ui_content()


def findPort(engineServer, enginePort):
    """Function to find the correct port for a given server
    """
    # pylint: disable-msg=E0611,F0401
    sys.path.append('/usr/share/vdsm-reg')
    import deployUtil  # @UnresolvedImport

    from ovirt_config_setup.engine import \
        TIMEOUT_FIND_HOST_SEC  # @UnresolvedImport
    from ovirt_config_setup.engine import \
        compatiblePort  # @UnresolvedImport
    # pylint: enable-msg=E0611,F0401

    compatPort, sslPort = compatiblePort(enginePort)

    LOGGER.debug("Finding port %s:%s with compat %s ssl %s" %
                 (engineServer, enginePort, compatPort, sslPort))

    deployUtil.nodeCleanup()

    # Build port list to try
    port_cfgs = [(enginePort, sslPort)]
    if compatPort:
        port_cfgs += [(compatPort, sslPort)]
    else:
        port_cfgs += [(enginePort, False)]

    LOGGER.debug("Port configuratoins for engine: %s" % port_cfgs)

    for try_port, use_ssl in port_cfgs:
        LOGGER.debug("Trying to reach engine %s via %s %s" %
                     (engineServer, try_port, "SSL" if use_ssl else ""))

        is_reachable = False

        try:
            is_reachable = isHostReachable(host=engineServer,
                                           port=try_port, ssl=use_ssl,
                                           timeout=TIMEOUT_FIND_HOST_SEC)
        except Exception:
            LOGGER.debug("Failed to reach engine: %s" % traceback.format_exc())

        if is_reachable:
            LOGGER.debug("Reached engine")
            enginePort = try_port
            break

    if not is_reachable:
        raise RuntimeError("Can't connect to @ENGINENAME@")

    return enginePort


def isHostReachable(host, port, ssl, timeout):
    """Check if a host is reachable on a given port via HTTP/HTTPS
    """
    if ssl:
        Connection = httplib.HTTPSConnection
    else:
        Connection = httplib.HTTPConnection
    Connection(str(host), port=int(port), timeout=timeout).request("HEAD", "/")
    return True


def retrieveCetrificate(engineServer, enginePort):
    """Function to retrieve and store the certificate from an Engine
    """
    fingerprint = None

    # pylint: disable-msg=E0611,F0401
    sys.path.append('/usr/share/vdsm-reg')
    import deployUtil  # @UnresolvedImport
    # pylint: enable-msg=E0611,F0401

    if deployUtil.getRhevmCert(engineServer, enginePort):
        _, _, path = deployUtil.certPaths('')
        fingerprint = deployUtil.generateFingerPrint(path)
    else:
        msgCert = "Failed downloading @ENGINENAME@ certificate"
        raise RuntimeError(msgCert)

    return path, fingerprint


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
    >>> n.update("engine.example.com", "1234", "p")
    >>> sorted(n.retrieve().items())
    [('cert_path', 'p'), ('port', '1234'), ('server', 'engine.example.com')]
    """
    keys = ("OVIRT_MANAGEMENT_SERVER",
            "OVIRT_MANAGEMENT_PORT",
            "OVIRT_MANAGEMENT_CERTIFICATE")

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, server, port, cert_path):
        (valid.Empty() | valid.FQDNOrIPAddress())(server)
        (valid.Empty() | valid.Port())(port)


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

    def cert_validator(self):
        cert_path = VDSM().retrieve()["cert_path"]
        cert_exists = cert_path and os.path.exists(cert_path)

        return cert_exists

    def commit(self):
        self.logger.info("Connecting to VDSM server")

        if not self.cert_validator():
            return False

        # pylint: disable-msg=E0611,F0401
        sys.path.append('/usr/share/vdsm-reg')
        import deployUtil  # @UnresolvedImport

        sys.path.append('/usr/share/vdsm')
        from vdsm import constants  # @UnresolvedImport

        from ovirt_config_setup.engine import \
            write_vdsm_config  # @UnresolvedImport
        # pylint: enable-msg=E0611,F0401

        cfg = VDSM().retrieve()

        # Stopping vdsm-reg may fail but its ok - its in the case when the
        # menus are run after installation
        deployUtil._logExec([constants.EXT_SERVICE, 'vdsm-reg', 'stop'])
        if write_vdsm_config(cfg["server"], cfg["port"]):
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
