#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# tui.py - Copyright (C) 2012 Red Hat, Inc.
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

"""
The urwid TUI base library
"""

import time
import urwid

from ovirt.node import base
from ovirt.node import ui
import ovirt.node.ui.builder
import ovirt.node.ui.widgets


class UrwidTUI(ovirt.node.ui.Window):
    app = None

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

    element_styles = {
        "text": "dark gray",
        "label": "black",
        "disabled": "white",
        "background": "light gray",
        "invalid": "dark red",
    }

    palette = [(None, 'default', element_styles["background"], 'bold',
                None, None),
               ('screen', None),
               ('header', 'white', 'dark blue'),
               ('table', element_styles["text"]),
               ('table.label', element_styles["label"]),
               ('table.header', element_styles["label"]),
               ('table.entry', element_styles["text"]),
               ('table.entry:focus', 'white', 'light blue'),
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
               ('plugin.widget.header', 'black, bold'),
               ('plugin.widget.divider', element_styles["text"]),
               ('plugin.widget.button', 'dark blue'),
               ('plugin.widget.button.disabled', element_styles["disabled"]),
               ('plugin.widget.label', element_styles["text"]),
               ('plugin.widget.label.keyword', element_styles["label"]),
               ('plugin.widget.progressbar.box', 'light gray'),
               ('plugin.widget.progressbar.uncomplete', None),
               ('plugin.widget.progressbar.complete', None, 'light gray'),
               ('plugin.widget.options', element_styles["label"]),
               ('plugin.widget.options.label', element_styles["label"]),
               ('plugin.widget.dialog', None),
               ('plugin.widget.page', None),
               ('plugin.widget.page.frame', None),
               ('plugin.widget.checkbox.label', element_styles["label"]),
               ('plugin.widget.checkbox', element_styles["label"]),
               ]

    def __init__(self, app):
        super(UrwidTUI, self).__init__(app)
        self.logger.info("Creating urwid tui for '%s'" % app)
        self.logger.debug("Detected encoding: %s" % urwid.get_encoding_mode())

    def show_body(self, body):
        """
        """
        assert type(body) is ui.Page
        widget = ui.builder.build_page(self, self._current_plugin, body)
        self.__display_as_body(widget)

    def show_page(self, page):
        """Shows the ui.Page as a page.
        This transforms the abstract ui.Page to a urwid specififc version
        and displays it.
        """
        assert type(page) is ui.Page
        widget = ui.builder.build_page(self, self._current_plugin, page)
        self.__display_as_page(widget)

    def show_dialog(self, dialog):
        """Shows the ui.Dialog as a dialog.
        This transforms the abstract ui.Dialog to a urwid specififc version
        and displays it.
        """
        assert type(dialog) is ui.Dialog
        widget = ui.builder.build_page(self, self._current_plugin, dialog)
        return self.__display_as_dialog(widget, dialog.title,
                                        dialog.escape_key)

    def topmost_dialog(self):
        dialog = [w for w in self.__widget_stack
                  if type(w) is ovirt.node.ui.widgets.ModalDialog][-1:]
        if dialog:
            dialog = dialog[0]
        else:
            dialog = None
        return dialog

    def close_topmost_dialog(self):
        dialog = self.topmost_dialog()
        if dialog:
            self.__close_dialog(dialog)

    def quit(self):
        """Quit the UI
        """
        self.logger.info("Quitting, exitting mainloop")
        raise urwid.ExitMainLoop()

    def run(self):
        """Run the UI
        """
        self.__main_frame = self.__create_screen()
        self.__register_default_hotkeys()

        self.__loop = urwid.MainLoop(self.__main_frame,
                              self._convert_palette(),
                              input_filter=self.__filter_hotkeys)
        self.__loop.run()

    def __build_menu(self):
        self.__menu = ovirt.node.ui.widgets.PluginMenu(self._plugins)

        def menu_item_changed(plugin):
            self._display_plugin(plugin)
        urwid.connect_signal(self.__menu, 'changed', menu_item_changed)

    def __create_screen(self):
        self.__build_menu()
        self.__page_frame = urwid.Frame(urwid.Filler(urwid.Text("")))
        self.__menu.set_focus(0)

        self.__notice = urwid.Text("Note: ")
        self.__notice_filler = urwid.Filler(self.__notice)
        self.__notice_attrmap = urwid.AttrMap(self.__notice_filler, "notice")
        menu_frame_columns = urwid.Columns([("weight", 0.3, self.__menu),
                              self.__page_frame], 4)

        body = urwid.Pile([
#                           ("fixed", 3, self.__notice_attrmap),
                           menu_frame_columns
                        ])

        header = urwid.Text(self.header, wrap='clip')
        header = urwid.AttrMap(header, 'header')
        footer = urwid.Text(self.footer, wrap='clip')
        screen = urwid.Frame(body, header, footer)
        return urwid.AttrMap(screen, "screen")

    def _check_outstanding_changes(self):
        has_outstanding_changes = False
        if self._current_plugin:
            pending_changes = self._current_plugin.pending_changes()
            if pending_changes:
                self.logger.warning("Pending changes: %s" % pending_changes)
                msg = ""
                widgets = dict(self._current_plugin.ui_content().children)
                self.logger.debug("Available widgets: %s" % widgets)
                for path, value in pending_changes.items():
                    if path in widgets:
                        widget = widgets[path]
                        field = widget.name
                        self.logger.debug("Changed widget: %s %s" % (path,
                                                                     widget))
                        msg += "- %s\n" % (field.strip(":"))
                if msg:
                    self.__display_as_dialog(urwid.Filler(urwid.Text(
                                "The following fields have changed:\n%s" %
                                msg)),
                                "Pending changes")
                    has_outstanding_changes = True
        return has_outstanding_changes

    def __display_as_body(self, widget):
        self.__main_frame.body = widget

    def __display_as_page(self, page):
        self.logger.debug("Displaying page %s" % page)
#        filler = urwid.Filler(page, ("fixed top", 1), height=35)
        filler = urwid.Pile([page])
        self.__page_frame.body = filler

    def _display_plugin(self, plugin):
        if self._check_outstanding_changes():
            return
        start = time.time()
        self._current_plugin = plugin
        plugin_page = ovirt.node.ui.builder.page_from_plugin(self, plugin)
        self.__display_as_page(plugin_page)
        stop = time.time()
        diff = stop - start
        self.logger.debug("Build and displayed plugin_page in %ss" %
                          diff)

    def __display_as_dialog(self, body, title, escape_key="esc"):
        self.logger.debug("Displaying dialog: %s / %s" % (body, title))
#        filler = urwid.Filler(body, ("fixed top", 1), height=35)
        filler = urwid.Pile([body])
        dialog = ovirt.node.ui.widgets.ModalDialog(title, filler, escape_key,
                                                   self.__loop.widget)
        urwid.connect_signal(dialog, "close",
                             lambda: self.__close_dialog(dialog))
        self.__loop.widget = dialog
        self.__widget_stack.append(dialog)
        self._draw_screen()
        return dialog

    def __close_dialog(self, dialog):
        self.logger.debug("Widget stack: %s" % self.__widget_stack)
        new_stack = [w for w in self.__widget_stack if w != dialog]
        self.__widget_stack = new_stack
        self.logger.debug("New widget stack: %s" % self.__widget_stack)
        if self.__widget_stack:
            self.__loop.widget = self.__widget_stack[-1]
        else:
            self.__loop.widget = self.__main_frame
        self.logger.debug("Dialog %s closed" % dialog)

    def __filter_hotkeys(self, keys, raw):
        key = str(keys)

        if type(self.__loop.widget) is ovirt.node.ui.widgets.ModalDialog:
            self.logger.debug("Modal dialog escape: %s" % key)
            if self.__loop.widget.escape_key is None:
                self.logger.debug("Dialog can not be closed with magic key")
            elif self.__loop.widget.escape_key in keys:
                self.close_topmost_dialog()
                return

        if key in self._hotkeys.keys():
            self.logger.debug("Running hotkeys: %s" % key)
            self._hotkeys[key]()

        self.logger.debug("Keypress: %s" % key)

        return keys

    def __register_default_hotkeys(self):
        self.register_hotkey(["esc"], self._quit_if_no_dialogs)
        self.register_hotkey(["window resize"], self._check_min_size_cb)

    def _quit_if_no_dialogs(self):
        if self.topmost_dialog() is None:
            self.quit()
        else:
            self.logger.debug("There are still open dialogs")

    def _draw_screen(self):
        self.__loop.draw_screen()

    def size(self):
        if not self.__loop.screen:
            # FIXME sometimes screen is None, but why?
            return (0, 0)
        return self.__loop.screen.get_cols_rows()

    def _min_size(self):
            return (80, 23)

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
                d = ui.Dialog("Error", [("dialog.error", ui.Label(msg))])
                d.buttons = []
                self._error_dialog = self.show_dialog(d)
        else:
            if hasattr(self, "_error_dialog") and self._error_dialog:
                self._error_dialog.close()
                self._error_dialog = None

    def watch_pipe(self, cb):
        """Return a fd to be used as stdout, cb called for each line
        """
        return self.__loop.watch_pipe(cb)

    def notify(self, category, msg):
        self.logger.info("UI notification (%s): %s" % (category, msg))
        # FIXME do notification

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
            if k == None:
                continue
            colors = [e or default[idx] for idx, e in enumerate(v)]
            rest = default[len(colors):]
            palette.append(tuple([k] + colors + rest))
        return palette
