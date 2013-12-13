#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# builder.py - Copyright (C) 2012 Red Hat, Inc.
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
from ovirt.node import ui, base
from ovirt.node.ui import widgets as uw
import os
import urwid

"""
A visitor to build the urwid TUI from the abstract UI definitions.
Is based on the visitor pattern
"""


class UrwidUIBuilder(ui.AbstractUIBuilder):
    def _build_container(self, ui_container):
        assert ui.ContainerElement in type(ui_container).mro()
        widgets = []

        for element in ui_container.children:
            widget = self.build(element)
            if type(ui_container) is ui.ConfirmedEntry:
                # Special handling of the special widget, but why?
                # Why? Because nested Pile's need to be taken care of.
                # FIXME Generalize this (to cover other widgets too)
                widgets.append(widget)
            else:
                widgets.append(("pack", widget))

        # Add buttons
        if hasattr(ui_container, "buttons") and ui_container.buttons:
            widgets.append(self._build_button_bar(ui_container.buttons))

        if not any(type(t) is not tuple or t[0] == "weight" for t in widgets):
            # Add a weighted dummy if no weigthed dummy is in the Pile,
            # to fullfill urwid's assumptions
            # FIXME this whole function can be cleaned up!
            widgets.append(urwid.SolidFill())

        if ui.Page in type(ui_container).mro():
            page = uw.PageWidget(widgets, ui_container.title)
        else:
            page = uw.TabablePile(widgets)

        return page

    def _build_window(self, ui_window):
        return UrwidWindow(ui_window.path, self.application)

    def _build_page(self, ui_page):
        return self._build_container(ui_page)

    def _build_dialog(self, ui_dialog):
        return self._build_container(ui_dialog)

    def _build_label(self, ui_label):
        if type(ui_label) is ui.KeywordLabel:
            widget = uw.KeywordLabel(ui_label.keyword,
                                     ui_label.text())
        elif type(ui_label) is ui.Header:
            widget = uw.Header(ui_label.text(),
                               ui_label.template)
        elif type(ui_label) is ui.Notice:
            widget = uw.Notice(ui_label.text())

        else:
            widget = uw.Label(ui_label.text())

        def on_item_text_change_cb(w, v):
            self.logger.debug("Element changed, updating label " +
                              "'%s': %s" % (w, v))
            widget.text(v)
            self.application.ui.force_redraw()
        ui_label.on_value_change.connect(on_item_text_change_cb)

        return widget

    def _build_keywordlabel(self, ui_keywordlabel):
        return self._build_label(ui_keywordlabel)

    def _build_header(self, ui_header):
        return self._build_label(ui_header)

    def _build_notice(self, ui_notice):
        return self._build_label(ui_notice)

    def _build_button(self, ui_button):
        widget = uw.Button(ui_button.text(), ui_button.enabled())

        def on_widget_click_cb(widget, data=None):
            change = {ui_button.path: True}
            self.logger.debug("Button click: %s" % change)
            ui_button.on_activate(change)

        urwid.connect_signal(widget, "click", on_widget_click_cb)

        def on_item_enabled_change_cb(w, v):
            widget.enable(v)

        ui_button.on_enabled_change.connect(on_item_enabled_change_cb)

        return widget

    def _build_button_bar(self, ui_buttonbar):
        #if type(ui_buttonbar) is list:
        children = ui_buttonbar
        #else:
        #    children = ui_buttonbar.children
        # FIXME create dedicated widget
        button_widgets = []
        for element in children:
            assert type(element) in [ui.SaveButton, ui.ResetButton,
                                     ui.CloseButton, ui.Button, ui.QuitButton]
            widget = self._build_button(element)
            button_widgets.append(widget)
        max_width = int(1.5 * max([w.width() for w in button_widgets]))
        button_widgets = [(max_width, w) for w in button_widgets]
        button_bar = urwid.Filler(urwid.Columns(button_widgets))
        return button_bar

    def _build_entry(self, ui_entry):
        widget_class = None
        if type(ui_entry) is ui.Entry:
            widget_class = uw.Entry
        else:
            widget_class = uw.PasswordEntry

        widget = widget_class(ui_entry.label(),
                              align_vertical=ui_entry.align_vertical)
        widget.enable(ui_entry.enabled())

        widget.set_text(ui_entry.text())

        def on_item_enabled_change_cb(w, v):
            self.logger.debug("Element changed, updating entry '%s': %s" %
                              (w, v))
            if widget.selectable() != v:
                widget.enable(v)
            if v is False:
                widget.notice = ""
                widget.valid(True)

        ui_entry.on_enabled_change.connect(on_item_enabled_change_cb)

        def on_item_valid_change_cb(w, v):
            widget.valid(v)

        ui_entry.on_valid_change.connect(on_item_valid_change_cb)

        def on_item_notice_change_cb(w, n):
            widget.notice = n or ""

        ui_entry.on_notice_change.connect(on_item_notice_change_cb)

        def on_item_text_change_cb(w, v):
            self.logger.debug("Setting entry tooo: %s" % v)
            widget.set_text(v)

        ui_entry.on_value_change.connect(on_item_text_change_cb)

        def on_widget_value_change(widget, new_value):
            self.logger.debug("Entry %s changed, calling callback: '%s'" %
                              (widget, ui_entry.path))
            ui_entry.on_change({ui_entry.path: new_value})

        urwid.connect_signal(widget, 'change', on_widget_value_change)

        return widget

    def _build_passwordentry(self, ui_passwordentry):
        return self._build_entry(ui_passwordentry)

    def _build_divider(self, ui_divider):
        return uw.Divider(ui_divider.char)

    def _build_options(self, ui_options):
        widget = uw.Options(ui_options.label(), ui_options.options,
                            ui_options.option())

        def on_widget_change_cb(widget, data):
            ui_options.option(data)
            self.logger.debug("Options changed, calling callback: %s" % data)
            ui_options.on_change({ui_options.path: data})

        urwid.connect_signal(widget, "change", on_widget_change_cb)

        def on_item_change_cb(item, new_option):
            self.logger.debug("Selectiong option: %s" % new_option)
            widget.select(new_option)

        ui_options.on_value_change.connect(on_item_change_cb)

        return widget

    def _build_checkbox(self, ui_checkbox):
        widget = uw.Checkbox(ui_checkbox.label(), ui_checkbox.state())

        def on_widget_change_cb(widget, data=None):
            ui_checkbox.state(data)
            self.logger.debug("Checkbox changed, calling callback: %s" % data)
            ui_checkbox.on_change({ui_checkbox.path: data})

        urwid.connect_signal(widget, "change", on_widget_change_cb)

        return widget

    def _build_progressbar(self, ui_progressbar):
        widget = uw.ProgressBarWidget(float(ui_progressbar.current()),
                                      float(ui_progressbar.done))

        def on_item_current_change_cb(w, v):
            self.logger.debug("Model changed, updating progressbar '%s': %s" %
                              (w, v))
            widget.set_completion(v)
            self.application.ui.force_redraw()

        ui_progressbar.on_value_change.connect(on_item_current_change_cb)

        return widget

    def _build_table(self, ui_table):
        children = []

        for key, label in ui_table.items:
            c = self._build_tableitem(ui_table, key, label)
            children.append(c)
        widget = uw.TableWidget(ui_table.label(), ui_table.header,
                                children, ui_table.multi,
                                ui_table.height, ui_table.enabled())

        for c in children:
            c._table = widget

        if ui_table.multi:
            widget.selection(ui_table.selection())
        else:
            widget.focus(ui_table.selection())

        def on_change_cb(w, d=None):
            if ui_table.multi:
                ui_table.selection(widget.selection())
            else:
                ui_table.selection(w._key)

            ui_table.on_change({ui_table.path: w._key})

        urwid.connect_signal(widget, "changed", on_change_cb)

        def on_item_value_change_cb(p, v):
            # Update the selection in the ui.Element
            widget.selection(v)

        ui_table.on_value_change.connect(on_item_value_change_cb)

        return widget

    def _build_tableitem(self, ui_table, key, label):
        c = uw.TableEntryWidget(label, multi=ui_table.multi)
        c._key = key

        def on_activate_cb(w, data):
            ui_table.selection(w._table.selection())
            ui_table.on_change({ui_table.path: w._key})
            ui_table.on_activate({ui_table.path: w._key})

        urwid.connect_signal(c, "activate", on_activate_cb)
        return c

    def _build_row(self, ui_row):
        widgets = []
        self.logger.debug(ui_row.children)
        for element in ui_row.children:
            child = self.build(element)
            self.logger.debug(child)
            widgets.append(child)

        return urwid.Columns(widgets)


def inherits(obj, t):
    return t in type(obj).mro()


class UrwidWindow(ui.Window):

    _builder = ui.AbstractUIBuilder

    _plugins = {}
    _hotkeys = {}

    __loop = None
    __main_frame = None
    __menu = None
    __page_frame = None

    __widget_stack = []

    _current_plugin = None

    header = u"\n Configuration TUI\n"
    footer = u"Press ctrl+c to quit"

    with_menu = True

    element_styles = {
        "text": "black",
        "label": "dark gray",
        "disabled": "dark red",
        "background": "light gray",
        "invalid": "dark red",
        "header": 'black, bold',
    }

    palette = [(None, 'default', element_styles["background"], 'bold',
                None, None),
               ('screen', None),
               ('header', 'white', 'dark blue'),
               ('footer', element_styles["text"]),
               ('table', element_styles["text"]),
               ('table.label', element_styles["label"]),
               ('table.header', element_styles["label"] + ", standout"),
               ('table.entry', element_styles["text"]),
               ('table.entry:focus', None, 'dark blue'),
               ('main.menu', 'black'),
               ('main.menu.frame', element_styles["text"]),
               ('notice', 'light red'),
               ('plugin.widget.entry', element_styles["text"]),
               ('plugin.widget.entry.disabled', element_styles["disabled"]),
               ('plugin.widget.entry.invalid', element_styles["invalid"]),
               ('plugin.widget.entry.label', element_styles["label"]),
               ('plugin.widget.entry.label.invalid', element_styles["label"]),
               ('plugin.widget.entry.frame', element_styles["text"]),
               ('plugin.widget.entry.frame.invalid',
                element_styles["invalid"]),
               ('plugin.widget.entry.frame.disabled',
                element_styles["disabled"]),
               ('plugin.widget.notice', element_styles["invalid"]),
               ('plugin.widget.header', element_styles["header"]),
               ('plugin.widget.divider', element_styles["text"]),
               ('plugin.widget.button', 'dark blue'),
               ('plugin.widget.button.disabled', element_styles["disabled"]),
               ('plugin.widget.label', element_styles["text"]),
               ('plugin.widget.label.keyword', element_styles["label"]),
               ('plugin.widget.progressbar.box', element_styles["disabled"]),
               ('plugin.widget.progressbar.uncomplete',
                element_styles["label"]),
               ('plugin.widget.progressbar.complete', "white",
                element_styles["disabled"]),
               ('plugin.widget.options', element_styles["text"]),
               ('plugin.widget.options.disabled', element_styles["disabled"]),
               ('plugin.widget.options.label', element_styles["label"]),
               ('plugin.widget.dialog', None),
               ('plugin.widget.page', None),
               ('plugin.widget.page.header', element_styles["header"]),
               ('plugin.widget.page.frame', None),
               ('plugin.widget.checkbox.label', element_styles["label"]),
               ('plugin.widget.checkbox', element_styles["text"])
               ]

    def __init__(self, path, application, with_menu=True):
        super(UrwidWindow, self).__init__(path, application)
        urwid.set_encoding("utf8")
        self._builder = UrwidUIBuilder(self.application)
        self.with_menu = with_menu
        self.logger.debug("Creating urwid tui for '%s'" % application)
        self.logger.debug("Detected encoding: %s" % urwid.get_encoding_mode())

    def _show_body(self, body):
        """
        """
        assert inherits(body, ui.Page)
        widget = self._builder._build_page(body)
        self.__display_as_body(widget)

    def _show_on_page(self, page):
        widget = self._builder._build_page(page)
        self.__display_as_page(widget)

    def _show_on_dialog(self, dialog):
        widget = self._builder._build_page(dialog)
        return self.__display_as_dialog(widget, dialog.title,
                                        dialog.escape_key)

    def topmost_dialog(self):
        dialog = [w for w in self.__widget_stack
                  if inherits(w, uw.ModalDialog)][-1:]
        if dialog:
            dialog = dialog[0]
        else:
            dialog = None
        return dialog

    def close_topmost_dialog(self):
        dialog = self.topmost_dialog()
        if dialog:
            self.close_dialog(dialog)
        self.force_redraw()

    def quit(self):
        """Quit the UI
        """
        self.logger.info("Quitting, exitting mainloop")
        raise urwid.ExitMainLoop()

    def reset(self):
        self.__main_frame = self.__create_screen()
        self.__loop.widget = self.__main_frame

    def run(self):
        """Run the UI
        """
        self.__main_frame = self.__create_screen()
        self.__register_default_hotkeys()

        self.__loop = urwid.MainLoop(self.__main_frame,
                                     self._convert_palette(),
                                     input_filter=self.__filter_hotkeys)

        self.navigate.to_first_plugin()

        self.__init_pipe()

        self.__loop.run()

    def __init_pipe(self):
        self._pipe_q = []

        def cb_from_q(data):
            self.logger.debug("Data reading")
            try:
                while self._pipe_q:
                    cb = self._pipe_q.pop()
                    self.logger.debug("Data run: %s" % cb)
                    cb()
            except Exception:
                self.logger.debug("No callback")

        self._pipe_fd = self.__loop.watch_pipe(cb_from_q)

    def thread_connection(self):
        dst = self

        class UrwidUIThreadConnection(ui.Window.UIThreadConnection, base.Base):
            def call(self, callback):
                """Run the callback in the context of the UI thread
                """
                self.logger.debug("Data: %s to %s - %s" % (callback,
                                                           dst._pipe_fd,
                                                           dst._pipe_q))
                dst._pipe_q.append(callback)
                os.write(dst._pipe_fd, "Data!")

        return UrwidUIThreadConnection()

    def suspended(self):
        """Supspends the screen to do something in the foreground
        """
        class SuspendedScreen(base.Base):
            def __init__(self, loop):
                super(SuspendedScreen, self).__init__()
                self.__loop = loop

            def __enter__(self):
                self.__loop.screen.stop()

            def __exit__(self, a, b, c):
                self.__loop.screen.start()
        return SuspendedScreen(self.__loop)

    def __build_plugin_menu(self):
        self.__menu = uw.PluginMenu(self._plugins)

        def menu_item_changed(plugin):
            self.application.switch_to_plugin(plugin)
        urwid.connect_signal(self.__menu, 'changed', menu_item_changed)

    def __create_screen(self):
        columns = []

        self.__page_frame = urwid.Frame(urwid.Filler(urwid.Text("")))

        if self.with_menu:
            self.__build_plugin_menu()
            self.__menu.set_focus(0)
            columns += [("weight", 0.3, self.__menu)]

        columns += [self.__page_frame]

        menu_frame_columns = urwid.Columns(columns, 4)

        body = urwid.Pile([menu_frame_columns])

        header = urwid.Text(self.header, wrap='clip')
        header = urwid.AttrMap(header, 'header')
        footer = urwid.Text(self.footer, wrap='clip')
        footer = urwid.AttrMap(footer, 'footer')
        screen = urwid.Frame(body, header, footer)
        return urwid.AttrMap(screen, "screen")

    def __display_as_body(self, widget):
        self.__main_frame.body = widget

    def __display_as_page(self, page):
        self.logger.debug("Displaying page %s" % page)
#        filler = urwid.Filler(page, ("fixed top", 1), height=35)
        filler = urwid.Pile([page])
        padding = urwid.Padding(filler, left=1, right=1)
        self.__page_frame.body = padding

    def __display_as_dialog(self, body, title, escape_key="esc"):
        self.logger.debug("Displaying dialog: %s / %s" % (body, title))
        self.logger.debug("Stack: %s" % self.__widget_stack)
#        filler = urwid.Filler(body, ("fixed top", 1), height=35)
        filler = urwid.Pile([body])
        dialog = uw.ModalDialog(title, filler, escape_key,
                                self.__loop.widget)
        self.__loop.widget = dialog
        self.__widget_stack.append(dialog)
        self.force_redraw()
        self.logger.debug("New Stack: %s" % self.__widget_stack)
        return dialog

    def close_dialog(self, dialog):
        if type(dialog) in [str, unicode]:
            # Hack to alow to close a dialog by name
            for d in self.__widget_stack:
                if d.title == dialog:
                    dialog = d
        self.logger.debug("Closing dialog: %s" % dialog)
        self.logger.debug("Widget stack: %s" % self.__widget_stack)
        new_stack = [w for w in self.__widget_stack if w != dialog]
        self.__widget_stack = new_stack
        self.logger.debug("New widget stack: %s" % self.__widget_stack)
        if self.__widget_stack:
            self.__loop.widget = self.__widget_stack[-1]
        else:
            self.__loop.widget = self.__main_frame
        assert dialog not in new_stack
        self.logger.debug("Dialog %s closed" % dialog)

    def __filter_hotkeys(self, keys, raw):
        key = str(keys)

        if inherits(self.__loop.widget, uw.ModalDialog):
            self.logger.debug("Modal dialog escape: %s" % key)
            if self.__loop.widget.escape_key is None:
                self.logger.debug("Dialog can not be closed with magic key")
            elif self.__loop.widget.escape_key in keys:
                self.close_topmost_dialog()
                return

        if self.hotkeys_enabled() and key in self._hotkeys.keys():
            self.logger.debug("Running hotkeys: %s" % key)
            self._hotkeys[key]()

        if self.application.args.debug:
            self.logger.debug("Keypress: %s" % key)

        return keys

    def __register_default_hotkeys(self):
        self.register_hotkey(["esc"], self._quit_if_no_dialogs)
        self.register_hotkey(["window resize"], self._check_min_size_cb)

    def _quit_if_no_dialogs(self):
        if self.topmost_dialog() is None:
            self.application.quit() if self.application.quit is not \
                self.application.app_quit else self.quit()
        else:
            self.logger.debug("There are still open dialogs")

    def force_redraw(self):
        if self.__loop:
            self.__loop.draw_screen()

    def size(self):
        if not self.__loop.screen:
            # FIXME sometimes screen is None, but why?
            return (0, 0)
        return self.__loop.screen.get_cols_rows()

    def _min_size(self):
            return (80, 24)

    def _check_min_size_cb(self):
        size = self.size()
        msize = self._min_size()
        width, height = size
        min_width, min_height = msize
        if width < min_width or height < min_height:
            msg = ("The current window size %s is smaller " +
                   "than the minimum size %s") % (size, msize)
            self.logger.warning(msg)
            if not hasattr(self, "_error_dialog") or not self._error_dialog:
                d = ui.Dialog("error", "Error", [ui.Label("label", msg)])
                d.buttons = []
                self._error_dialog = self._show_on_dialog(d)
        else:
            if hasattr(self, "_error_dialog") and self._error_dialog:
                self._error_dialog.close()
                self._error_dialog = None
                self.close_topmost_dialog()

    def watch_pipe(self, cb):
        """Return a fd to be used as stdout, cb called for each line
        """
        return self.__loop.watch_pipe(cb)

    def _convert_palette(self):
        """Convert our palette to the format urwid understands.

        Non existsing or None values are filled with the defaults.
        """
        p = {}
        for t in self.palette:
            k = t[0]
            v = list(t[1:])
            p[k] = v

        palette = []
        default = p[None]
        for k, v in p.items():
            if k is None:
                continue
            colors = [e or default[idx] for idx, e in enumerate(v)]
            rest = default[len(colors):]
            palette.append(tuple([k] + colors + rest))
        return palette
