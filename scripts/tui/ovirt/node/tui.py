#!/bin/env python

import urwid

import logging
import os

import ovirt.node
import ovirt.node.plugins


logging.basicConfig(level=logging.DEBUG,
                    filename="app.log", filemode="w")
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
    __menu_list = None
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

    def __build_pages_list(self):
        items = []
        for title, plugin in self.__pages.items():
            item = SelectableText(title)
            item.plugin = plugin
            item = urwid.AttrMap(item, None, 'reveal focus')
            items.append(item)
        walker = urwid.SimpleListWalker(items)
        self.__menu_list = urwid.ListBox(walker)
        def __on_page_change():
            widget, position = self.__menu_list.get_focus()
            plugin = widget.original_widget.plugin
            page = self.__build_plugin_widget(plugin)
            self.__page_frame.body = page
        urwid.connect_signal(walker, 'modified', __on_page_change)
        attr_listbox = urwid.AttrMap(self.__menu_list, "main.menu")
        return attr_listbox

    def __build_menu(self):
        menu = urwid.LineBox(self.__build_pages_list())
        menu = urwid.AttrMap(menu, "main.menu.frame")
        return menu

    def __create_screen(self):
        menu = self.__build_menu()
        self.__page_frame = urwid.Frame(urwid.Filler(urwid.Text("")))
        self.__menu_list.set_focus(0)
        body = urwid.Columns([("weight", 0.5, menu), self.__page_frame], 4)
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

        save = urwid.Button("Save", self.popup) #plugin.ui_on_save)
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

    def popup(self, msg=None, buttons=None):
        LOGGER.debug("Launching popup")
        class Dialog(urwid.PopUpLauncher):
            def create_pop_up(self):
                return urwid.Filler(urwid.Text("Fooo"))
            def get_pop_up_parameters(self):
                return {'left':0, 'top':1, 'overlay_width':30, 'overlay_height':4}
        dialog = Dialog(self.__page_frame)
        dialog.open_pop_up()

    def suspended(self):
        """Supspends the screen to do something in the foreground
        TODO resizing is curently broken after resuming
        """
        class SuspendedScreen(object):
            def __init__(self, loop):
                self.__loop = loop
            def __enter__(self):
                self.screen = urwid.raw_display.Screen()
                self.screen.stop()
            def __exit__(self, a, b, c):
                self.screen.start()
                # Hack to force a screen refresh
                self.__loop.process_input(["up"])
                self.__loop.process_input(["down"])
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


class App(object):
    plugins = []

    ui = None

    def __init__(self, ui):
        self.ui = ui

    def __load_plugins(self):
        self.plugins = [m.Plugin() for m in ovirt.node.plugins.load_all()]

        for plugin in self.plugins:
            LOGGER.debug("Adding plugin " + plugin.name())
            self.ui.register_plugin(plugin.ui_name(), plugin)

    def __drop_to_shell(self):
        with self.ui.suspended():
            os.system("reset ; bash")

    def run(self):
        self.__load_plugins()
        self.ui.register_hotkey("f12", self.__drop_to_shell)
        self.ui.footer = "Press ctrl+x or esc to quit."
        self.ui.run()

if __name__ == '__main__':
    ui = UrwidTUI()
    app = App(ui)
    app.run()
