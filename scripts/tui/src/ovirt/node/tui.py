#!/bin/env python

import urwid

import logging

import ovirt.node
import ovirt.node.widgets
import ovirt.node.plugins
import ovirt.node.utils

LOGGER = logging.getLogger(__name__)


class UrwidTUI(object):
    app = None

    __pages = {}
    __hotkeys = {}

    __loop = None
    __main_frame = None
    __menu = None
    __page_frame = None

    header = u"\n Configuration TUI\n"
    footer = u"Press ctrl+c to exit"

    palette = [('header', 'white', 'dark blue'),
               ('menu.entry', '', ''),
               ('menu.entry:focus', 'white', 'light blue', 'standout'),
               ('main.menu', 'black', ''),
               ('main.menu.frame', 'light gray', ''),
               ('plugin.widget.entry', 'dark gray', ''),
               ('plugin.widget.entry.frame', 'light gray', ''),
               ('plugin.widget.disabled', 'dark gray', 'light gray'),
               ('plugin.widget.notice', 'light red', ''),
               ('plugin.widget.header', 'light blue', 'light gray'),
               ('plugin.widget.divider', 'dark gray', ''),
               ('plugin.widget.button', 'dark blue', ''),
               ]

    def __init__(self, app):
        LOGGER.info("Creating urwid tui for '%s'" % app)
        self.app = app

    def __build_menu(self):
        self.__menu = ovirt.node.widgets.PluginMenu(self.__pages)

        def menu_item_changed(plugin):
            self.__change_to_page(plugin)
        urwid.connect_signal(self.__menu, 'changed', menu_item_changed)

    def __create_screen(self):
        self.__build_menu()
        self.__page_frame = urwid.Frame(urwid.Filler(urwid.Text("")))
        self.__menu.set_focus(0)
        body = urwid.Columns([("weight", 0.5, self.__menu),
                              self.__page_frame], 4)
        header = urwid.Text(self.header, wrap='clip')
        header = urwid.AttrMap(header, 'header')
        footer = urwid.Text(self.footer, wrap='clip')
        return urwid.Frame(body, header, footer)

    def __build_widget_for_item(self, plugin, path, item):
        item_to_widget_map = {
            ovirt.node.plugins.Label: ovirt.node.widgets.Label,
            ovirt.node.plugins.Header: ovirt.node.widgets.Header,
            ovirt.node.plugins.Entry: ovirt.node.widgets.Entry,
            ovirt.node.plugins.PasswordEntry: ovirt.node.widgets.PasswordEntry,
            ovirt.node.plugins.Button: ovirt.node.widgets.Button,
            ovirt.node.plugins.SaveButton: ovirt.node.widgets.Button,
            ovirt.node.plugins.Divider: ovirt.node.widgets.Divider,
        }

        assert type(item) in item_to_widget_map.keys(), \
               "No widget for item type"

        widget = None
        widget_class = item_to_widget_map[type(item)]

        if type(item) in [ovirt.node.plugins.Entry, \
                          ovirt.node.plugins.PasswordEntry]:
            value = None
            if item.initial_value_from_model:
                value = plugin.model()[path]

            widget = widget_class(item.label, value)

            def on_item_enabled_change_cb(w, v):
                LOGGER.debug("Model changed, updating widget '%s': %s" % (w,
                                                                          v))
                if widget.selectable() != v:
                    widget.enable(v)
            item.connect_signal("enabled[change]", on_item_enabled_change_cb)

            def on_widget_value_change(widget, new_value):
                LOGGER.debug("Widget changed, updating model '%s'" % path)

                try:
                    plugin.validate(path, new_value)
                    plugin._on_ui_change({path: new_value})
                    widget.notice = ""

                except ovirt.node.plugins.Concern as e:
                    LOGGER.error("Concern when updating: %s" % e)

                except ovirt.node.plugins.InvalidData as e:
                    widget.notice = e.message
                    LOGGER.error("Invalid data when updating: %s" % e)
                self.__loop.draw_screen()
            urwid.connect_signal(widget, 'change', on_widget_value_change)

        elif type(item) in [ovirt.node.plugins.Header, \
                            ovirt.node.plugins.Label]:
            widget = widget_class(item.text())

            def on_item_text_change_cb(w, v):
                LOGGER.debug("Model changed, updating widget '%s': %s" % (w,
                                                                          v))
                widget.text(v)
                self.__loop.draw_screen()
            item.connect_signal("text[change]", on_item_text_change_cb)

        elif type(item) in [ovirt.node.plugins.Button,
                            ovirt.node.plugins.SaveButton]:
            widget = widget_class(item.text())
            def on_widget_click_cb(widget, data=None):
                if type(item) is ovirt.node.plugins.SaveButton:
                    plugin._on_ui_save()
                else:
#                   Nit propagating the signal as a signal to the plugin
#                   item.emit_signal("click", widget)
                    plugin._on_ui_change({path: True})
            urwid.connect_signal(widget, "click", on_widget_click_cb)

        elif type(item) in [ovirt.node.plugins.Divider]:
            widget = widget_class(item.char)
        return widget

    def __build_plugin_widget(self, plugin):
        """This method is building the widget for a plugin
        """
        widgets = []
        config = {
            "save_button": True
        }

        ui_content = plugin.ui_content()
        config.update(plugin.ui_config())

        for path, item in ui_content:
            widget = self.__build_widget_for_item(plugin, path, item)
            widgets.append(("flow", widget))

        if config["save_button"]:
#            save = urwid.Button("Save", lambda x: plugin._on_ui_save())
#            save = urwid.Padding(save, "left", width=8)
#            save = urwid.Filler(save, ("fixed top", 1))
            save = ovirt.node.widgets.Button("Save")
            urwid.connect_signal(save, 'click', lambda x: plugin._on_ui_save())
            widgets.append(urwid.Filler(save))

        widgets.append(urwid.Filler(urwid.Text("")))


        pile = urwid.Pile(widgets)
        # FIXME why is this fixed?
        widget = urwid.Filler(pile, ("fixed top", 1), height=20)
        return widget

    def __change_to_page(self, plugin):
        plugin_widget = self.__build_plugin_widget(plugin)
        page = plugin_widget
        self.__page_frame.body = page

    def __filter_hotkeys(self, keys, raw):
        key = str(keys)
        LOGGER.debug("Keypress: %s" % key)
        if type(self.__loop.widget) is ovirt.node.widgets.ModalDialog:
            LOGGER.debug("Modal dialog escape: %s" % key)
            dialog = self.__loop.widget
            if dialog.escape_key in keys:
                self.__loop.widget = dialog.previous_widget
            return

        if key in self.__hotkeys.keys():
            LOGGER.debug("Running hotkeys: %s" % key)
            self.__hotkeys[key]()
        return keys

    def __register_default_hotkeys(self):
        self.register_hotkey(["esc"], self.quit)
        self.register_hotkey(["q"], self.quit)

    def popup(self, title, msg, buttons=None):
        LOGGER.debug("Launching popup")

        dialog = ovirt.node.widgets.ModalDialog(urwid.Filler(urwid.Text(msg)),
                                                title, "esc",
                                                self.__loop.widget)
        self.__loop.widget = dialog

    def suspended(self):
        """Supspends the screen to do something in the foreground
        """
        class SuspendedScreen(object):
            def __init__(self, loop):
                self.__loop = loop

            def __enter__(self):
                self.__loop.screen.stop()

            def __exit__(self, a, b, c):
                self.__loop.screen.start()
        return SuspendedScreen(self.__loop)

    def register_plugin(self, title, plugin):
        """Register a plugin to be shown in the UI
        """
        self.__pages[title] = plugin

    def register_hotkey(self, hotkey, cb):
        """Register a hotkey
        """
        if type(hotkey) is str:
            hotkey = [hotkey]
        LOGGER.debug("Registering hotkey '%s': %s" % (hotkey, cb))
        self.__hotkeys[str(hotkey)] = cb

    def quit(self):
        """Quit the UI
        """
        raise urwid.ExitMainLoop()

    def run(self):
        """Run the UI
        """
        self.__main_frame = self.__create_screen()
        self.__register_default_hotkeys()

        self.__loop = urwid.MainLoop(self.__main_frame,
                              self.palette,
                              input_filter=self.__filter_hotkeys)
        self.__loop.run()
