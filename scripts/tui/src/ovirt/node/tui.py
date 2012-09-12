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
               ('plugin.widget.entry', 'dark gray', ''),
               ('plugin.widget.entry.frame', 'light gray', ''),
               ('plugin.widget.disabled', 'light gray', 'dark gray'),
               ('plugin.widget.notice', 'light red', ''),
               ('plugin.widget.header', 'light blue', 'light gray'),
               ]

    def __init__(self):
        pass

    def __build_pages_list(self):
        items = []
        for title, plugin in self.__pages.items():
            if plugin.has_ui():
                item = SelectableText(title)
                item.plugin = plugin
                item = urwid.AttrMap(item, None, 'reveal focus')
                items.append(item)
            else:
                LOGGER.info("No UI page for plugin %s" % plugin)
        walker = urwid.SimpleListWalker(items)
        self.__menu_list = urwid.ListBox(walker)

        def __on_item_change():
            widget, position = self.__menu_list.get_focus()
            plugin = widget.original_widget.plugin
            self.__change_to_page(plugin)

        urwid.connect_signal(walker, 'modified', __on_item_change)
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

    def __build_widget_for_item(self, plugin, path, item):
        widget = None

        if type(item) is ovirt.node.plugins.Entry or \
            type(item) is ovirt.node.plugins.Password:
            label_text = urwid.Text("\n" + item.label + ":")
            label = label_text
            mask = None
            if type(item) is ovirt.node.plugins.Password:
                mask = "*"
            edit = urwid.Edit(mask=mask)
            edit_attrmap = urwid.AttrMap(edit, "plugin.widget.entry")
            linebox = urwid.LineBox(edit_attrmap)
            linebox_attrmap = urwid.AttrMap(linebox,
                                            "plugin.widget.entry.frame")
            entry = linebox_attrmap
            main_widget = urwid.Columns([label, entry])

            notice_text = urwid.Text("")
            notice_attrmap = urwid.AttrMap(notice_text, "plugin.widget.notice")
            notice_widget = notice_attrmap

            widget = urwid.Pile([main_widget, notice_widget])

            if item.initial_value_from_model:
                value = plugin.model()[path]
                if value:
                    edit.set_edit_text(value)

            def on_change(widget, new_value):
                LOGGER.debug("Widget content changed for path '%s'" % path)

                try:
                    if path in plugin.validators():
                        msg = plugin.validators()[path](new_value)
                        # True and None are allowed
                        if msg not in [True, None]:
                            raise ovirt.node.plugins.InvalidData(msg)

                    plugin._on_ui_change({path: new_value})
                    notice_text.set_text("")

                except ovirt.node.plugins.Concern as e:
                    LOGGER.error("Concern when updating: %s" % e)

                except ovirt.node.plugins.InvalidData as e:
                    notice_text.set_text(e.message)
                    LOGGER.error("Invalid data when updating: %s" % e)

            urwid.connect_signal(edit, 'change', on_change)

            def foo(w, v):
                if edit.selectable() == v:
                    return True
                else:
                    edit.selectable = lambda: v
                    LOGGER.debug("dissing")
                    if v:
                        edit_attrmap.set_attr_map({None: ""})
                    else:
                        edit_attrmap.set_attr_map({
                            None: "plugin.widget.disabled"
                            })
            item.connect_signal("enabled[change]", foo)

        elif type(item) is ovirt.node.plugins.Header:
            label = urwid.Text("\n  %s\n" % item.label)
            label_attrmap = urwid.AttrMap(label, "plugin.widget.header")
            widget = label_attrmap

        elif type(item) is ovirt.node.plugins.Label:
            label = urwid.Text(item.label)
            widget = urwid.AttrMap(label, "plugin.widget.label")

        return widget

    def __build_plugin_widget(self, plugin):
        """This method is building the widget for a plugin
        """
        widgets = []

        for path, item in plugin.ui_content():
            widget = self.__build_widget_for_item(plugin, path, item)
            widgets.append(("flow", widget))

        save = urwid.Button("Save", lambda x: plugin._on_ui_save())
        save = urwid.Padding(save, "left", width=8)
        save = urwid.Filler(save, ("fixed top", 1))
        widgets.append(save)

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
                return {'left': 0,
                        'top': 1,
                        'overlay_width': 30,
                        'overlay_height': 4}
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
            LOGGER.debug("Adding plugin %s" % plugin)
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
