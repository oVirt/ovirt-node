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
from ovirt.node.config import defaults
from ovirt.node.utils import console
import threading
import time


"""
Progress page of the installer
"""


class Plugin(plugins.NodePlugin):
    _worker = None

    def __init__(self, application):
        super(Plugin, self).__init__(application)
        self._worker = InstallerThread(self)

    def name(self):
        return "Installation Progress"

    def rank(self):
        return 60

    def model(self):
        return {}

    def validators(self):
        return {}

    def ui_content(self):
        method = "Installing"
        product = self.application.product.PRODUCT_SHORT
        ws = [ui.Header("header[0]", "%s %s" % (method, product)),
              ui.Divider("divider[0]"),
              ui.ProgressBar("progressbar", 0),
              ui.Divider("divider[1]"),
              ui.Label("log", ""),
              ui.Divider("divider[2]"),
              ui.Button("action.reboot", "Reboot")
              ]
        self.widgets.add(ws)
        page = ui.Page("progress", ws)
        page.buttons = []
        self._worker.start()
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        if "action.reboot" in effective_changes:
            utils.system.reboot()


class InstallerThread(threading.Thread):
    def __init__(self, progress_plugin):
        super(InstallerThread, self).__init__()
        self.progress_plugin = progress_plugin

    @property
    def logger(self):
        return self.progress_plugin.logger

    def run(self):
        try:
            self.progress_plugin.widgets["action.reboot"].enabled(False)
            time.sleep(0.3)  # Give the UI some time to build
            transaction = self.__build_transaction()

            progressbar = self.progress_plugin.widgets["progressbar"]
            log = self.progress_plugin.widgets["log"]
            log_lines = []

            txlen = len(transaction)

            for idx, tx_element in transaction.step():
                idx += 1
                self.logger.debug("Running %s: %s" % (idx, tx_element))
                log_lines.append("(%s/%s) %s" % (idx, txlen, tx_element.title))
                log.text("\n".join(log_lines))

                def do_commit():
                    tx_element.commit()

                with console.CaptureOutput() as captured:
                    # Sometimes a tx_element is wrapping some code that
                    # writes to stdout/stderr which scrambles the screen,
                    # therefore we are capturing this
                    self.progress_plugin.dry_or(do_commit)

                progressbar.current(int(100.0 / txlen * idx))
                log_lines[-1] = "%s (Done)" % log_lines[-1]
                log.text("\n".join(log_lines))

        except Exception as e:
            msg = "Exception: %s" % repr(e)
            self.logger.debug(msg, exc_info=True)
            log.text(msg)

        finally:
            self.progress_plugin.widgets["action.reboot"].enabled(True)

        if captured.stderr.getvalue():
            se = captured.stderr.getvalue()
            if se:
                log.text("Stderr: %s" % se)

        # We enforce a redraw, because this the non-mainloop thread
        self.progress_plugin.application.ui.force_redraw()

    def __build_transaction(self):
        """Determin what kind of transaction to build
        Builds transactions for:
        - Installation
        - Upgrade
        """
        cfg = self.__build_config()

        self.logger.debug("Building transaction")

        tx = utils.Transaction("Installation")

        if cfg["method"] in ["install"]:
            tx += [self.UpdateDefaultsFromModels(cfg),
                   self.PartitionAndFormat(cfg["installation.devices"]),
                   self.SetPassword(cfg["root.password_confirmation"]),
                   self.InstallImageAndBootloader(cfg["boot.device"]),
                   self.SetKeyboardLayout(cfg["keyboard.layout"])]

        elif cfg["method"] in ["upgrade", "downgrade", "reinstall"]:
            tx.title = "Update"
            tx += [self.InstallImageAndBootloader()]
            new_password = cfg.get("upgrade.password_confirmation", None)
            if new_password:
                tx += [self.SetPassword(new_password)]

        self.logger.debug("Built transaction: %s" % tx)

        return tx

    def __build_config(self):
        app = self.progress_plugin.application
        config = {}
        for pname, plugin in app.plugins().items():
            self.logger.debug("Config for page %s" % (pname))
            try:
                model = plugin.model()
                config.update(model)
                self.logger.debug("Merged config: %s" % (model))
            except NotImplementedError:
                self.logger.debug("Merged no config.")
        self.logger.debug("Final config: %s" % config)
        return config

    class UpdateDefaultsFromModels(utils.Transaction.Element):
        title = "Writing configuration file"

        def __init__(self, cfg):
            super(InstallerThread.UpdateDefaultsFromModels, self).__init__()
            self.config = cfg

        def prepare(self):
            # Update/Write the config file
            cfg = self.config
            model = defaults.Installation()

            model.install_on(init=[cfg["boot.device"]] +
                             cfg["installation.devices"],
                             root_size=cfg["storage.root_size"],
                             efi_size=cfg["storage.efi_size"],
                             swap_size=cfg["storage.swap_size"],
                             logging_size=cfg["storage.logging_size"],
                             config_size=cfg["storage.config_size"],
                             data_size=cfg["storage.data_size"])

            kbd = defaults.Keyboard()
            kbd.update(self.config["keyboard.layout"])

        def commit(self):
            pass
            # Everything done during prepare

    class PartitionAndFormat(utils.Transaction.Element):
        title_tpl = "Partitioning and Creating File Systems on '%s'"

        def __init__(self, dst):
            self.dst = dst
            self.title = self.title_tpl % dst
            super(InstallerThread.PartitionAndFormat, self).__init__()

        def commit(self):
            from ovirtnode import storage
            # Re-read defaults file to pick up changes
            storage._functions.parse_defaults()
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
            self.logger.debug("Setting root password: %s" % self.root_password)
            if not admin_pw_set:
                raise RuntimeError("Failed to set root password")

    class InstallImageAndBootloader(utils.Transaction.Element):
        def __init__(self, dst=None):
            self.dst = dst
            if dst:
                self.title = "Installing Image and Bootloader " + \
                    "Configuration to '%s'" % dst
            else:
                self.title = "Updating Image and Bootloader"
            super(InstallerThread.InstallImageAndBootloader, self).__init__()

        def commit(self):
            from ovirtnode.install import Install
            install = Install()
            boot_setup = install.ovirt_boot_setup()
            if not boot_setup:
                raise RuntimeError("Failed to set install bootloader")

    class SetKeyboardLayout(utils.Transaction.Element):
        title_tpl = "Setting keyboard layout to '%s'"

        def __init__(self, kbd_layout):
            self.kbd_layout = kbd_layout
            self.title = self.title_tpl % kbd_layout
            super(InstallerThread.SetKeyboardLayout, self).__init__()

        def commit(self):
            utils.Keyboard().set_layout(self.kbd_layout)
