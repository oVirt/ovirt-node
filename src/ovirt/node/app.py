#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# app.py - Copyright (C) 2012 Red Hat, Inc.
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
from optparse import OptionParser
from ovirt.node import base, utils, plugins, ui, loader
from ovirt.node.config import defaults
from ovirt.node.ui import urwid_builder
from ovirt.node.utils import system, Timer, console
import sys

"""
Representing the whole application (not just the TUI).
Basically the application consists of two parts: Page-Plugins and the UI
which communicate with each other.
"""

RUNTIME_LOG_CONF_FILENAME = "/etc/ovirt-node/logging.conf"
RUNTIME_DEBUG_LOG_CONF_FILENAME = "/etc/ovirt-node/logging.debug.conf"


def parse_cmdline():
    """Parses the relevant cmdline arguments
    """
    parser = OptionParser()
    parser.add_option("--defaults",
                      dest="defaults",
                      help="Central oVirt Node configuration file")
    parser.add_option("--dry",
                      action='store_true',
                      dest="dry",
                      default=False,
                      help="Just write defaults, nothing else")
    parser.add_option("--debug",
                      action='store_true',
                      dest="debug",
                      default=False,
                      help="Run in debug mode (suitable for pdb)")

    return parser.parse_args()


class Application(base.Base):
    """The controller part when seeing as an MVC pattern

    Args:
        __plugins: All known plugins
        ui_builder: The builder used to build the UI
        ui: The root window of the UI
    """
    __plugins = {}
    __current_plugin = None

    ui_builder = None
    ui = None

    def __init__(self, plugin_base, args, quit=None,
                 ui_builder=urwid_builder.UrwidUIBuilder):
        """Constructs a new application

        Args:
            plugin_base: The package where to find page-plugins
            ui_builder: An implementation of the UIBuilder class to be used
        """
        import gettext

        reload(sys)
        sys.setdefaultencoding('utf-8')
        gettext.install('ovirt_node', '/usr/share/locale', unicode=True)

        super(Application, self).__init__()
        self.logger.info(("Starting '%s' application " +
                          "with '%s' UI") % (plugin_base, ui_builder))

        self.args = args
        self.__parse_cmdline()

        self.ui_builder = ui_builder(self)
        self.ui = self.ui_builder.build(ui.Window("screen", self))
        self.plugin_base = plugin_base
        self.quit = lambda: quit(self) if quit else self.app_quit

    def __parse_cmdline(self):
        if self.args.defaults:
            # FIXME Should be read by clients
            defaults.OVIRT_NODE_DEFAULTS_FILENAME = self.args.defaults
            self.logger.debug("Setting config file: %s (%s)" %
                              (self.args.defaults,
                               defaults.OVIRT_NODE_DEFAULTS_FILENAME))

        self.logger.debug("Commandline arguments: %s" % self.args)

    def plugins(self):
        """Retrieve all loaded plugins
        """
        return self.__plugins

    def get_plugin(self, mixed):
        """Find a plugin by instance, name, or type
        """
        mtype = type(mixed)
        self.logger.debug("Looking up plugin: %s (%s)" % (mixed, mtype))
        plugin = None

        if isinstance(mixed, plugins.NodePlugin):
            plugin = mixed
        elif mtype in [str, unicode]:
            plugin = self.__plugins[mixed]
        elif mtype is type:
            type_to_instance = dict((type(p), p) for p
                                    in self.__plugins.values())
            if mixed not in type_to_instance:
                raise RuntimeError("Requested plugin type '%s' is not in %s" %
                                   (mixed, type_to_instance))
            plugin = type_to_instance[mixed]
        else:
            raise Exception("Can't look up: %s" % mixed)

        self.logger.debug("Found plugin for type: %s" % plugin)
        return plugin

    def current_plugin(self):
        """Returns the current plugin
        """
        return self.__current_plugin

    def assign_actions(self, ui_container):
        """Searches through an element-tree (container is the root) and
        sets callbacks on all common ui.Actions.

        The ui.Module is just specififying the behavior, how the behaior is
        realized happens here. E.g. what a SaveAction actaully triggers.

        Args:
            ui_container: The element-tree root
        """
        self.logger.debug("Assigning UI actions to %s" % ui_container)
        assert ui.ContainerElement in type(ui_container).mro()
        plugin = self.current_plugin()
        window = self.ui
        elements = ui_container.elements()

        def cond_close_dialog(userdata):
            self.logger.debug("Closing dialog: %s" % userdata)
            if issubclass(type(userdata), ui.Dialog):
                window.close_dialog(userdata.title)
            else:
                window.close_topmost_dialog()

        def call_on_ui_save(d):
            self.current_plugin()._on_ui_save()

        def call_on_ui_reset(d):
            self.current_plugin()._on_ui_reset()

        def call_on_ui_change(d):
            return self.current_plugin()._on_ui_change(d)

        def call_on_ui_reload(d):
            self.switch_to_plugin(self.current_plugin(), False)

        def call_quit(d):
            self.quit()

        # All known handlers
        handlers = {ui.SaveAction: call_on_ui_save,
                    ui.CloseAction: cond_close_dialog,
                    ui.ResetAction: call_on_ui_reset,
                    ui.ChangeAction: call_on_ui_change,
                    ui.ReloadAction: call_on_ui_reload,
                    ui.QuitAction: call_quit,
                    }

        for element in elements:
            for path, signal in element.list_signals():
                callbacks = signal.callbacks
                for cb in callbacks:
                    if type(cb) in handlers and not cb.callback:
                        action = handlers[type(cb)]
                        self.logger.debug("Setting %s.%s to %s" %
                                          (element, cb, action))
                        cb.callback = action

            if type(element) is ui.SaveButton:
                # http://stackoverflow.com/questions/2731111/
                # python-lambdas-and-variable-bindings
                def toggle_savebutton_disabled(t, v, e=element):
                    e.enabled(v)
                plugin.on_valid.connect(toggle_savebutton_disabled)

    def populate_with_values(self, ui_container):
        """Take values from model and inject them into the appropriate UI
        elements.

        The mapping happens through the "path". Each UI Element has an assigned
        path, which associates them with a place in the model.
        """
        self.logger.debug("Assigning model values to %s" % ui_container)
        assert ui.ContainerElement in type(ui_container).mro()
        model = self.current_plugin().model()
        for element in ui_container.elements():
            if element.path in model:
                value = model[element.path]
                self.logger.debug("Populating %s: %s" % (element, value))
                element.value(value)

    def switch_to_plugin(self, plugin, check_for_changes=True):
        """Set the context to the given plugin.
        This includes displaying the page-plugin UI on a page.
        """
        self.logger.debug("Switching to plugin " +
                          "%s, with checks? %s" % (plugin, check_for_changes))
        if check_for_changes and self._check_outstanding_changes():
            return
        plugin = self.get_plugin(plugin)
        self.__current_plugin = plugin
        with Timer() as t:
            content = plugin.ui_content()
            self.show(content)
        self.logger.debug("Build and displayed plugin_page in %s seconds" % t)
        self.logger.debug("Switched to plugin '%s'" % plugin)
        self.logger.info("Current page is '%s'" % plugin.ui_name())

    def show(self, ui_container):
        """Shows the ui.Page as a page.
        This transforms the abstract ui.Page to a urwid specififc version
        and displays it.
        """
        assert ui.Page in type(ui_container).mro()
        plugin = self.current_plugin()
        self.populate_with_values(ui_container)
        self.assign_actions(ui_container)
        plugin.check_semantics()
        if ui.Dialog in type(ui_container).mro():
            self.ui._show_on_dialog(ui_container)
        elif ui.Page in type(ui_container).mro():
            self.ui._show_on_page(ui_container)
        else:
            raise Exception("Unknown container: %s" % ui_container)
        return ui_container

    def show_exception(self, e):
        """Show an exception
        """
        self.logger.debug(e, exc_info=True)
        notice = ui.InfoDialog("dialog.notice", "An exception occurred",
                               "%s" % e)
        self.show(notice)

    @property
    def product(self):
        return system.ProductInformation()

    def run(self):
        self.__load_plugins()

        if not self.__plugins:
            raise Exception("No plugins found in '%s'" % self.plugin_base)
        self.ui.register_hotkey("f2", self.__drop_to_shell)
        self.ui.register_hotkey("f12", self.__reload_page)
        self.ui.register_hotkey("window resize", self.__check_terminal_size)

        self.ui.header = "\n %s\n" % str(self.product)
        self.ui.footer = "Press esc to quit."

        try:
            if system.is_rescue_mode():
                self.logger.error("The TUI cannot be used in rescue mode. "
                                  "Please reboot without rescue to "
                                  "configure/install.")
                import sys
                sys.exit(0)
            self.ui.run()
        except Exception as e:
            console.reset()
            self.logger.error("An error appeared in the UI: %s" % repr(e))
            self.logger.info("Exception:", exc_info=True)
            console.writeln("Press ENTER to logout ...")
            console.writeln("or enter 's' to drop to shell")
            if console.wait_for_keypress() == 's':
                self.__drop_to_shell()

    def app_quit(self):
        self.logger.info("Quitting")
        self.ui.quit()

    def notice(self, msg):
        """Displays a notice on the screen
        """
        if True:
            children = [ui.Label("app.notice.text", msg)]
            dialog = ui.Dialog("app.notice", "Notice", children)
            dialog.buttons = [ui.CloseButton("app.notice.close")]
            self.show(dialog)
        else:
            self.ui._show_on_notice(msg)

    def _check_outstanding_changes(self):
        """This function checks if any UI Element has changed
        """
        has_outstanding_changes = False
        return has_outstanding_changes
        # FIXME the rest of this function has to be activated when it
        # is possible to set the selected menu item in the left-sided
        # main menu
        # otehrwise this popup will show, but the next menu item is selected
        # and we can not reset it to the entry which raised this popup
        if self.current_plugin() and self.current_plugin().pending_changes():
            pending_changes = self.current_plugin().pending_changes()
            elements = self.current_plugin().widgets
            self.logger.debug("Pending changes: %s" % pending_changes)
            self.logger.debug("Available elements: %s" % elements)
            msg = ""
            for path in [p for p in pending_changes if p in elements]:
                self.logger.debug("Element '%s' changed" % path)
                # assumption that element is a container
                element = elements[path]
                field = element.label()
                self.logger.debug("Changed widget: " +
                                  "%s %s" % (path, element))
                msg += "- %s\n" % (field.strip(":"))
            if msg:
                txt = "The following fields have changed:\n%s" % msg
                txt += "\n\nPlease save or reset the page."
                dialog = ui.Dialog("dialog.changes", "Pending Changes",
                                   [ui.Label("dialog.changes.txt", txt)])
                dialog.buttons = [ui.CloseButton("dialog.changes.close",
                                                 "Back")]
                self.show(dialog)
                has_outstanding_changes = True

    def __load_plugins(self):
        """Load all plugins by looking at the available plugin groups
        and calling createPlugins on a package, if it exists.
        the createPlugins function is responsible for creating the plugin
        """
        self.__plugins = {}
        groups = loader.plugin_groups_iterator(self.plugin_base,
                                               "createPlugins")
        for group, createPlugins in groups:
            if createPlugins:
                self.logger.debug("Package has plugins: %s" % group)
                createPlugins(self)
            else:
                self.logger.debug("Package has no plugins: %s" % group)

    def register_plugin(self, plugin):
        """Register the plugin in the application and it's UI
        Args:
            plugin: Plugin to be registered, needs to be derived from
                    plugins.NodePlugin
        """
        self.logger.debug("Registering plugin '%s': %s" %
                          (plugin.name(), plugin))
        if plugin.name() in self.__plugins:
            raise RuntimeError("Plugin with name '%s' is already registered" %
                               plugin.name())
        self.__plugins[plugin.name()] = plugin
        self.ui.register_plugin(plugin.ui_name(), plugin)

    def __drop_to_shell(self):
        utils.console.writeln("Dropping to rescue shell ...")

        def open_console():
            utils.process.call("clear ; bash", shell=True)

        def return_ok(dialog, changes):
            with self.ui.suspended():
                open_console()

        try:
            txt = "Making changes in the rescue shell is unsupported. Do not "
            txt += "use this without guidance from support representatives"
            dialog = ui.ConfirmationDialog("dialog.shell", "Rescue Shell", txt
                                           )

            dialog.buttons[0].on_activate.clear()
            dialog.buttons[0].on_activate.connect(ui.CloseAction())
            dialog.buttons[0].on_activate.connect(return_ok)
            self.show(dialog)

        except:
            # Error when the UI is not running
            open_console()

    def __reload_page(self):
        self.ui.reset()

    def __check_terminal_size(self):
        cols, rows = self.ui.size()
        if cols < 80 or rows < 24:
            self.logger.warning("Window size is too small: %dx%d" % (cols,
                                                                     rows))
