#!/usr/bin/python
#
# widgets.py - Copyright (C) 2012 Red Hat, Inc.
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
Widgets for oVirt Node's urwid TUI
"""
import urwid
import logging

LOGGER = logging.getLogger(__name__)


class SelectableText(urwid.Text):
    """A Text widget that can be selected to be highlighted
    """
    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class PluginMenuEntry(urwid.AttrMap):
    """An entry in the main menu
    """
    __text = None

    def __init__(self, title, plugin):
        self.__text = SelectableText(title)
        self.__text.plugin = plugin
        super(PluginMenuEntry, self).__init__(self.__text, 'menu.entry',
                                              'menu.entry:focus')


class PluginMenu(urwid.WidgetWrap):
    """The main menu listing all available plugins (which have a UI)
    """
    __pages = None
    __walker = None
    __list = None
    __list_attrmap = None
    __linebox = None
    __linebox_attrmap = None

    signals = ['changed']

    def __init__(self, pages):
        self.__pages = pages
        self.__build_walker()
        self.__build_list()
        self.__build_linebox()
        super(PluginMenu, self).__init__(self.__linebox_attrmap)

    def __build_walker(self):
        items = []

        plugins = self.__pages.items()
        plugins = sorted(plugins, key=lambda two: two[1].rank())

        for title, plugin in plugins:
            if plugin.has_ui():
                item = PluginMenuEntry(title, plugin)
                items.append(item)
            else:
                LOGGER.warning("No UI page for plugin %s" % plugin)

        self.__walker = urwid.SimpleListWalker(items)

    def __build_list(self):
        self.__list = urwid.ListBox(self.__walker)

        def __on_item_change():
            widget, position = self.__list.get_focus()
            plugin = widget.original_widget.plugin
            urwid.emit_signal(self, "changed", plugin)

        urwid.connect_signal(self.__walker, 'modified', __on_item_change)

        self.__list_attrmap = urwid.AttrMap(self.__list, "main.menu")

    def __build_linebox(self):
        self.__linebox = urwid.LineBox(self.__list_attrmap)
        self.__linebox_attrmap = urwid.AttrMap(self.__linebox,
                                               "main.menu.frame")

    def set_focus(self, n):
        self.__list.set_focus(n)


class DialogBox(urwid.WidgetWrap):
    def __init__(self, body, title, bodyattr=None, titleattr=None):
        self.body = urwid.LineBox(body)
        self.title = urwid.Text(title)
        if titleattr is not None:
            self.title = urwid.AttrMap(self.title, titleattr)
        if bodyattr is not None:
            self.body = urwid.AttrMap(self.body, bodyattr)

        box = urwid.Overlay(self.title, self.body,
                            align='center',
                            valign='top',
                            width=len(title),
                            height=None,
                            )
        urwid.WidgetWrap.__init__(self, box)

    def selectable(self):
        return self.body.selectable()

    def keypress(self, size, key):
        return self.body.keypress(size, key)


class ModalDialog(urwid.Overlay):
    def __init__(self, body, title, escape_key, previous_widget, bodyattr=None,
                 titleattr=None):
        self.escape_key = escape_key
        self.previous_widget = previous_widget

        if type(body) in [str, unicode]:
            body = urwid.Text(body)

        box = DialogBox(body, title, bodyattr, titleattr)

        super(ModalDialog, self).__init__(box, previous_widget, 'center',
                                          ('relative', 70), 'middle',
                                          ('relative', 70))


class Label(urwid.WidgetWrap):
    """A read only widget representing a label
    """

    def __init__(self, text):
        self._label = urwid.Text(text)
        self._label_attrmap = urwid.AttrMap(self._label,
                                            "plugin.widget.label")
        super(Label, self).__init__(self._label_attrmap)

    def text(self, value=None):
        if value != None:
            self._label.set_text(value)
        return self._label.get_text()

    def set_text(self, txt):
        self.text(txt)


class Header(Label):
    """A read only widget representing a header
    """
    _header_attr = "plugin.widget.header"

    def __init__(self, text):
        super(Header, self).__init__("\n  %s\n" % text)
        self._label_attrmap.set_attr_map({None: self._header_attr})


class KeywordLabel(Label):
    """A read only widget consisting of a "<b><keyword>:</b> <value>"
    """
    _keyword_attr = "plugin.widget.label.keyword"
    _text_attr = "plugin.widget.label"

    def __init__(self, keyword, text=""):
        super(KeywordLabel, self).__init__(text)
        self._keyword = keyword
        self.text(text)
#        self._label_attrmap.set_attr_map({None: ""})

    def text(self, text=None):
        if text is not None:
            self._text = text
            keyword_markup = (self._keyword_attr, self._keyword)
            text_markup = (self._text_attr, self._text)
            markup = [keyword_markup, text_markup]
            self._label.set_text(markup)
        return self._text


class Entry(urwid.WidgetWrap):
    signals = ['change']

    notice = property(lambda self: self._notice.get_text(), \
                      lambda self, v: self._notice.set_text(v))

    selectable = lambda self: True

    def enable(self, is_enabled):
        self.selectable = lambda: is_enabled
        attr_map = {None: "plugin.widget.entry"}
        if not is_enabled:
            attr_map = {None: "plugin.widget.entry.disabled"}
        self._edit_attrmap.set_attr_map(attr_map)

    def valid(self, is_valid):
        attr_map = {None: "plugin.widget.entry.frame"}
        if not is_valid:
            attr_map = {None: "plugin.widget.entry.frame.invalid"}
        self._linebox_attrmap.set_attr_map(attr_map)

    def __init__(self, label, mask=None):
        self._label = urwid.Text("\n" + label + ":")
        self._edit = urwid.Edit(mask=mask)
        self._edit_attrmap = urwid.AttrMap(self._edit, "plugin.widget.entry")
        self._linebox = urwid.LineBox(self._edit_attrmap)
        self._linebox_attrmap = urwid.AttrMap(self._linebox,
                                              "plugin.widget.entry.frame")
        self._columns = urwid.Columns([self._label, self._linebox_attrmap])

        self._notice = urwid.Text("")
        self._notice_attrmap = urwid.AttrMap(self._notice,
                                             "plugin.widget.notice")

        self._pile = urwid.Pile([self._columns, self._notice_attrmap])

        def on_widget_change_cb(widget, new_value):
            urwid.emit_signal(self, 'change', self, new_value)
        urwid.connect_signal(self._edit, 'change', on_widget_change_cb)

        super(Entry, self).__init__(self._pile)

    def set_text(self, txt):
        self._edit.set_edit_text(txt)


class PasswordEntry(Entry):
    def __init__(self, label):
        super(PasswordEntry, self).__init__(label, mask="*")


class Button(urwid.WidgetWrap):
    signals = ["click"]

    selectable = lambda self: True

    def __init__(self, label):
        self._button = urwid.Button(label)

        def on_click_cb(widget, data=None):
            urwid.emit_signal(self, 'click', self)
        urwid.connect_signal(self._button, 'click', on_click_cb)

        self._button_attrmap = urwid.AttrMap(self._button,
                                              "plugin.widget.button")

        self._padding = urwid.Padding(self._button_attrmap,
                                      width=len(label) + 4)

        super(Button, self).__init__(self._padding)

    def enable(self, is_enabled):
        self.selectable = lambda: is_enabled
        if is_enabled:
            self._button_attrmap.set_attr_map({None: ""})
        else:
            self._button_attrmap.set_attr_map({
                None: "plugin.widget.button.disabled"
                })


class Divider(urwid.WidgetWrap):
    def __init__(self, char=u" "):
        self._divider = urwid.Divider(char)
        self._divider_attrmap = urwid.AttrMap(self._divider,
                                              "plugin.widget.divider")
        super(Divider, self).__init__(self._divider_attrmap)


class Options(urwid.WidgetWrap):
    signals = ["change"]

    def __init__(self, label, options, selected_option_key):
        self._options = options
        self._button_to_key = {}
        self._bgroup = []
        self._buttons = [urwid.Text(label + ":")]
        for option_key, option_label in self._options:
            widget = urwid.RadioButton(self._bgroup, option_label,
                                       on_state_change=self._on_state_change)
            self._button_to_key[widget] = option_key
            if option_key == selected_option_key:
                widget.set_state(True)
            self._buttons.append(widget)
        self._columns = urwid.Columns(self._buttons)
        self._pile = urwid.Pile([urwid.Divider(), self._columns,
                                 urwid.Divider()])
        super(Options, self).__init__(self._pile)

    def _on_state_change(self, widget, new_state):
        if new_state:
            data = self._button_to_key[widget]
            urwid.emit_signal(self, "change", widget, data)

    def select(self, key):
        for button in self._buttons:
            if button in self._button_to_key:
                bkey = self._button_to_key[button]
                if key == bkey:
                    button.set_state(True)

    def set_text(self, txt):
        self.select(txt)


#https://github.com/pazz/alot/blob/master/alot/widgets/globals.py
class ChoiceWidget(urwid.Text):
    def __init__(self, choices, callback, cancel=None, select=None,
                 separator=' '):
        self.choices = choices
        self.callback = callback
        self.cancel = cancel
        self.select = select
        self.separator = separator

        items = []
        for k, v in choices.items():
            if v == select and select is not None:
                items += ['[', k, ']:', v]
            else:
                items += ['(', k, '):', v]
            items += [self.separator]
        urwid.Text.__init__(self, items)

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key == 'enter' and self.select is not None:
            self.callback(self.select)
        elif key == 'esc' and self.cancel is not None:
            self.callback(self.cancel)
        elif key in self.choices:
            self.callback(self.choices[key])
        else:
            return key


class PageWidget(urwid.WidgetWrap):
    save_button = None

    def __init__(self, widgets):
#        self._listwalker = urwid.SimpleListWalker(widgets)
#        self._listbox = urwid.ListBox(self._listwalker)
        self._pile = urwid.Pile(widgets)
        super(PageWidget, self).__init__(self._pile)


class RowWidget(urwid.Columns):
    pass
