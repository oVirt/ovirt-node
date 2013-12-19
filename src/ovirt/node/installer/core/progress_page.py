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


"""
Progress page of the installer
"""


class Plugin(plugins.NodePlugin):
    _worker = None

    def __init__(self, application):
        super(Plugin, self).__init__(application)
        self._worker = InstallerThread(self)

    def name(self):
        return _("Installation Progress")

    def rank(self):
        return 60

    def model(self):
        return {}

    def validators(self):
        return {}

    def ui_content(self):
        method = _("Installing")
        product = self.application.product.PRODUCT_SHORT
        ws = [ui.Header("header[0]", "%s %s" % (method, product)),
              ui.Divider("divider[0]"),
              ui.ProgressBar("progressbar", 0),
              ui.Divider("divider[1]"),
              ui.Label("log", ""),
              ui.Divider("divider[2]"),
              ui.Button("action.reboot", _("Reboot"))
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
            self.dry_or(lambda: utils.system.reboot())


class InstallerThread(threading.Thread):
    ui_thread = None

    def __init__(self, progress_plugin):
        super(InstallerThread, self).__init__()
        self.progress_plugin = progress_plugin

    @property
    def logger(self):
        return self.progress_plugin.logger

    def run(self):
        try:
            app = self.progress_plugin.application
            self.ui_thread = app.ui.thread_connection()

            self.__run()
        except Exception as e:
            self.logger.exception("Installer thread failed: %s" % e)

    def __run(self):
        app = self.progress_plugin.application
        reboot_button = self.progress_plugin.widgets["action.reboot"]
        progressbar = self.progress_plugin.widgets["progressbar"]
        log = self.progress_plugin.widgets["log"]
        log_lines = ["Starting ..."]

        captured_stderr = []

        try:
            self.ui_thread.call(lambda: log.text("\n".join(log_lines)))
            self.ui_thread.call(lambda: reboot_button.enabled(False))
            self.ui_thread.call(lambda: app.ui.hotkeys_enabled(False))

            transaction = self.__build_transaction()
            txlen = len(transaction)

            for idx, tx_element in transaction.step():
                idx += 1
                self.logger.debug("Running %s: %s" % (idx, tx_element))
                log_lines.append("(%s/%s) %s" % (idx, txlen, tx_element.title))
                self.ui_thread.call(lambda: log.text("\n".join(log_lines)))

                def do_commit():
                    tx_element.commit()

                with console.CaptureOutput() as captured:
                    # Sometimes a tx_element is wrapping some code that
                    # writes to stdout/stderr which scrambles the screen,
                    # therefore we are capturing this
                    self.progress_plugin.dry_or(do_commit)

                    if captured.stderr.getvalue():
                        captured_stderr.append(captured.stderr.getvalue())

                log_lines[-1] = "%s (Done)" % log_lines[-1]

                def update_ui():
                    progressbar.current(int(100.0 / txlen * idx))
                    log.text("\n".join(log_lines))
                self.ui_thread.call(update_ui)

        except Exception as e:
            self.logger.exception("Installer transaction failed")
            msg = "Exception: %s" % repr(e)
            self.ui_thread.call(lambda: log.text(msg))

        finally:
            pass
            self.ui_thread.call(lambda: reboot_button.enabled(True))
            self.ui_thread.call(lambda: app.ui.hotkeys_enabled(True))

        if captured_stderr:
            self.ui_thread.call(lambda: log.text("Stderr: %s" %
                                                 str(captured_stderr)))

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
                   self.SetPassword(cfg["admin.password"]),
                   self.InstallImageAndBootloader(cfg["boot.device.current"]),
                   self.SetKeyboardLayout(cfg["keyboard.layout"])]

        elif cfg["method"] in ["upgrade", "downgrade", "reinstall"]:
            tx.title = "Update"
            tx += [self.InstallImageAndBootloader()]
            tx += [self.SetKeyboardLayout(cfg["keyboard.layout"])]
            tx += [self.MigrateConfigs()]
            new_password = cfg.get("upgrade.password", None)
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
            cfg = self.config

            # Data size get's a special handling because it grabs the
            # remaining space
            data_size = cfg.get("storage.data_size", "-1")
            data_size = data_size if int(data_size) >= 0 else "-1"
            self.logger.debug("Using a data_size of %s" % data_size)

            model = defaults.Installation()

            model.install_on(init=[cfg["boot.device.current"]] +
                             cfg["installation.devices"],
                             root_size=cfg["storage.root_size"],
                             efi_size=cfg["storage.efi_size"],
                             swap_size=cfg["storage.swap_size"],
                             logging_size=cfg["storage.logging_size"],
                             config_size=cfg["storage.config_size"],
                             data_size=data_size)

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
        title = "Setting Admin Password"

        def __init__(self, admin_password):
            super(InstallerThread.SetPassword, self).__init__()
            self.admin_password = admin_password

        def commit(self):
            from ovirtnode import password
            admin_pw_set = password.set_password(self.admin_password, "admin")
            self.logger.debug("Setting admin password")
            if not admin_pw_set:
                raise RuntimeError("Failed to set admin password")

    class InstallImageAndBootloader(utils.Transaction.Element):
        def __init__(self, dst=None):
            self.dst = dst
            if dst:
                self.title = _("Installing Image and Bootloader ") + \
                    _("Configuration to '%s'") % dst
            else:
                self.title = _("Updating Image and Bootloader")
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
            model = defaults. Keyboard()
            model.update(layout=self.kbd_layout)
            tx = model.transaction()
            tx()

    class MigrateConfigs(utils.Transaction.Element):
        title = "Migrating configuration data"

        def __init__(self):
            super(InstallerThread.MigrateConfigs, self).__init__()

        def commit(self):
            from ovirt.node.config import migrate
            migrate.MigrateConfigs().translate_all()
