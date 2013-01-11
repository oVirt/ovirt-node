#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# progress_page.py - Copyright (C) 2013 Red Hat, Inc.
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
from ovirt.node import plugins, ui, utils
import threading
import time


"""
Progress page of the installer
"""


class Plugin(plugins.NodePlugin):
    _model = None
    _elements = None
    _worker = None

    def __init__(self, application):
        super(Plugin, self).__init__(application)
        self._worker = InstallerThread(self)

    def name(self):
        return "Installation Progress"

    def rank(self):
        return 60

    def model(self):
        return self._model or {}

    def validators(self):
        return {}

    def ui_content(self):
        ws = [ui.Header("header[0]", "%s is beeing installed ..." %
                        self.application.product.PRODUCT_SHORT),
              ui.Divider("divider[0]"),
              ui.ProgressBar("progressbar", 0),
              ui.Divider("divider[1]"),
              ui.Label("log", ""),
              ]
        self.widgets.add(ws)
        page = ui.Page("progress", ws)
        page.buttons = []
        self._worker.start()
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        pass


class InstallerThread(threading.Thread):
    def __init__(self, progress_plugin):
        super(InstallerThread, self).__init__()
        self.progress_plugin = progress_plugin

    @property
    def logger(self):
        return self.progress_plugin.logger

    def run(self):
        time.sleep(0.3)  # Give the UI some time to build
        transaction = self.__build_transaction()

        progressbar = self.progress_plugin._elements["progressbar"]
        log = self.progress_plugin._elements["log"]
        log_lines = []

        txlen = len(transaction)
        try:
            for idx, tx_element in transaction.step():
                idx += 1
                self.logger.debug("Running %s: %s" % (idx, tx_element))
                log_lines.append("(%s/%s) %s" % (idx, txlen, tx_element.title))
                log.text("\n".join(log_lines))

                self.progress_plugin.dry_or(lambda: tx_element.commit())

                progressbar.current(int(100.0 / txlen * idx))
                log_lines[-1] = "%s (Done)" % log_lines[-1]
                log.text("\n".join(log_lines))
        except Exception as e:
            log.text("EXECPTION: %s" % e)

    def __build_transaction(self):
        self.__update_defaults_from_models()

        tx = utils.Transaction("Installation")

        tx.append(self.PartitionAndFormat())
        tx.append(self.SetPassword("the-password"))
        tx.append(self.InstallBootloader())

        return tx

    def __update_defaults_from_models(self):
        config = {}
        app = self.progress_plugin.application
        for pname, plugin in app.plugins().items():
            self.logger.debug("Config for %s" % (pname))
            try:
                model = plugin.model()
                config.update(model)
                self.logger.debug("Merged config: %s" % (model))
            except NotImplementedError:
                self.logger.debug("Merged no config.")

    class PartitionAndFormat(utils.Transaction.Element):
        title = "Partitioning and Creating File Systems"

        def commit(self):
            from ovirtnode import storage
            config_storage = storage.Storage()
            storage_setup = config_storage.perform_partitioning()
            if not storage_setup:
                raise RuntimeError("Failed to partition/format")

    class SetPassword(utils.Transaction.Element):
        title = "Setting Root Password"

        def __init__(self, root_password):
            super(InstallerThread.SetPassword, self).__init__()
            self.root_password = root_password

        def commit(self):
            from ovirtnode import password
            admin_pw_set = password.set_password(self.root_password, "admin")
            if not admin_pw_set:
                raise RuntimeError("Failed to set root password")

    class InstallBootloader(utils.Transaction.Element):
        title = "Installing Bootloader Configuration"

        def commit(self):
            from ovirtnode.install import Install
            install = Install()
            boot_setup = install.ovirt_boot_setup()
            if not boot_setup:
                raise RuntimeError("Failed to set install bootloader")
