#!/bin/env python

import urwid

import logging
import os

import ovirt.node
import ovirt.node.plugins


logging.basicConfig(level=logging.DEBUG,
                    filename="app.log")
LOGGER = logging.getLogger(__name__)


class SelectableText(urwid.Text):
    def selectable(self):
        return True
    def keypress(self, size, key):
        return key


class UrwidTUI(object):
    __pages = {}
    __hotkeys = {}

    __loop = None
    __main_frame = None
    __page_frame = None

    header = u"\n Configuration TUI\n"
    footer = u"Press ctrl+c to exit"

    palette = [('header', 'white', 'dark blue'),
               ('reveal focus', 'white', 'light blue', 'standout'),
               ('main.menu', 'black', ''),
               ('main.menu.frame', 'light gray', ''),
               ('plugin.entry', 'dark gray', ''),
               ('plugin.entry.frame', 'light gray', ''),]

    def __init__(self):
        pass

    def page_selected(self, widget, user_data):
        LOGGER.debug(user_data)

    def __pages_list(self):
        items = []
        for title, plugin in self.__pages.items():
            item = SelectableText(title)
            item.plugin = plugin
            item = urwid.AttrMap(item, None, 'reveal focus')
            items.append(item)
        walker = urwid.SimpleListWalker(items)
        listbox = urwid.ListBox(walker)
        def __on_page_change():
            widget, position = listbox.get_focus()
            plugin = widget.original_widget.plugin
            page = self.__build_plugin_widget(plugin)
            self.__page_frame.body = page
        urwid.connect_signal(walker, 'modified', __on_page_change)
        attr_listbox = urwid.AttrMap(listbox, "main.menu")
        return attr_listbox

    def __create_screen(self):
        menu = urwid.LineBox(self.__pages_list())
        menu = urwid.AttrMap(menu, "main.menu.frame")
        self.__page_frame = urwid.Frame(urwid.Filler(urwid.Text("-")))
        page = self.__page_frame
        body = urwid.Columns([
            ("weight", 0.5, menu), page
            ], 4)
        header = urwid.Text(self.header, wrap='clip')
        header = urwid.AttrMap(header, 'header')
        footer = urwid.Text(self.footer, wrap='clip')
        return urwid.Frame(body, header, footer)

    def __build_plugin_widget(self, plugin):
        """This method is building the widget for a plugin
        """
        widgets = []
        for item in plugin.ui_content():
            widget = None
            if type(item) is ovirt.node.plugins.Entry:
                label = urwid.Filler(urwid.Text(item.label + ":"))
                edit = urwid.Edit()
                def on_change(a, b):
                    plugin.ui_on_change({item.path: edit.get_text()[0]})
                urwid.connect_signal(edit, 'change', on_change)
                entry = edit
                entry = urwid.AttrMap(entry, "plugin.entry")
                entry = urwid.LineBox(entry)
                entry = urwid.AttrMap(entry, "plugin.entry.frame")
                entry = urwid.Filler(entry)
                widget = urwid.Columns([label, entry])
            elif type(item) is ovirt.node.plugins.Label:
                widget = urwid.Filler(urwid.Text(item.label))
                widget = urwid.AttrMap(widget, "plugin.label")
            widgets.append(widget)

        save = urwid.Button("Save", plugin.ui_on_save)
        save = urwid.Padding(save, "left", width=8)
        save = urwid.Filler(save, ("fixed bottom", 1))
        widgets.append(save)

        widget = urwid.Pile(widgets)
        return widget

    def __filter_hotkeys(self, keys, raw):
        key = str(keys)
        LOGGER.debug("Keypress: %s" % key)
        if key in self.__hotkeys.keys():
            self.__hotkeys[key]()
        return keys

    def __register_default_hotkeys(self):
        self.register_hotkey(["esc"], self.quit)
        self.register_hotkey(["q"], self.quit)


    def suspend(self):
        urwid.raw_display.Screen.stop()

    def resume(self):
        urwid.raw_display.Screen.start()

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


class App(object):
    plugins = []

    ui = None

    def __init__(self, ui):
        self.ui = ui

    def __load_plugins(self):
        self.plugins = [m.Plugin(self) for m in ovirt.node.plugins.load_all()]

        for plugin in self.plugins:
            LOGGER.debug("Adding plugin " + plugin.name())
            self.ui.register_plugin(plugin.ui_name(), plugin)

    def __drop_to_shell(self):
        self.ui.suspend()
        os.system("reset ; bash")
        self.ui.resume()

    def run(self):
        self.__load_plugins()
        self.ui.register_hotkey("f12", self.__drop_to_shell)
        self.ui.footer = "Press ctrl+x or esc to quit."
        self.ui.run()

if __name__ == '__main__':
    ui = UrwidTUI()
    app = App(ui)
    app.run()
