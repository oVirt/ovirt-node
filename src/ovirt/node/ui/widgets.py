#!/usr/bin/python
# -*- coding: utf-8 -*-
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
from ovirt.node import log
import urwid

LOGGER = log.getLogger(__name__)


class SelectableText(urwid.Text):
    """A Text widget that can be selected to be highlighted
    """
    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class NoticeDecoration(urwid.WidgetWrap):
    """This is adecorator which adds a notice field below it's target

    Args:
        notice: Get/Set the notice
    """
    _notice_widget = None

    _target = None
    _pile = None

    notice = property(lambda self: self.__notice_widget.get_text(),
                      lambda self, v: self.set_notice(v))

    def __init__(self, target):
        self._target = target
        self._notice_widget = urwid.Text("")
        self._notice_attrmap = urwid.AttrMap(self._notice_widget,
                                             "plugin.widget.notice")
        self._pile = urwid.Pile([self._target])
        super(NoticeDecoration, self).__init__(self._pile)
        self.set_notice(None)

    def set_notice(self, txt=None):
        """Set/remove the current notice

        Args:
            txt: Either the text to be displayed or None to hide the notice
        """
        if txt:
            self._notice_widget.set_text(txt)
            widgets = [self._target, self._notice_attrmap]
        else:
            widgets = [self._target]
        self._pile.contents = [(w, ('weight', 1)) for w in widgets]


class TableEntryWidget(urwid.AttrMap):
    """An entry in a table
    """
    _text = None

    signals = ["activate"]
    checkboxes = {True: "[x] ",
                  False: "[ ] "}

    def __init__(self, title, multi=False):
        assert len(self.checkboxes[True]) == len(self.checkboxes[False])
        self.multi = multi
        self.title = title
        self._text = self.__build_child()
#        self._text = Button(title)
#        self._text.button_left = ""
#        self._text.button_right = ""
        super(TableEntryWidget, self).__init__(self._text, 'table.entry',
                                                           'table.entry:focus')

    def keypress(self, size, key):
        if urwid.Button._command_map[key] == 'activate':
            self.__handle_activate()
        return key

    def mouse_event(self, size, event, button, x, y, focus):
        if button != 1 or not urwid.util.is_mouse_press(event):
            return False

        self.__handle_activate()
        return True

    def is_selected(self):
        if self.multi:
            return self._text.text.startswith(self.checkboxes[True])
        return True

    def select(self, is_selected=True):
        if self.multi:
            new_text = "%s%s" % (self.checkboxes[is_selected], self.title)
            self._text.set_text(new_text)

    def __build_child(self):
        self._text = SelectableText(self.title)
        if self.multi:
            self.select(False)
        return self._text

    def __handle_activate(self):
        if self.multi:
            is_checked = self.is_selected()
            LOGGER.debug("handling activate: %s" % is_checked)
            self.select(not is_checked)
        self._emit('activate', self)


class TableWidget(NoticeDecoration):
    """A table, with a single column
    """
    __walker = None
    __list = None
    __list_attrmap = None
    __linebox = None
    __linebox_attrmap = None

    signals = ['changed']

    _table_attr = "table"
    _label_attr = "table.label"
    _header_attr = "table.header"
    _text_attr = "plugin.widget.button"

    _position = 0

    def __init__(self, label, header, items, multi, height, enabled):
        self.__rows = -1
        self.__offset = -1
        self.__list_size = -1
        self.__scrollbar_visible = False
        self.__label = urwid.Text(label)
        self.__label_attrmap = urwid.AttrMap(self.__label, self._label_attr)
        if multi:
            header = (" " * len(TableEntryWidget.checkboxes[True])) + header
        self.__header = urwid.Text(header)
        self.__header_attrmap = urwid.AttrMap(self.__header, self._header_attr)
        self.__items = items
        self.__walker = urwid.SimpleListWalker(self.__items)
        self.__list = urwid.ListBox(self.__walker)
#        self.__list_linebox = urwid.LineBox(self.__list)
        self.multi = multi
        self.__height = height

        def __on_item_change():
            widget, self._position = self.__list.get_focus()
            self._update_scrollbar()
            urwid.emit_signal(self, "changed", widget)
        urwid.connect_signal(self.__walker, 'modified', __on_item_change)

        self.__position_label = urwid.Text("", align="right")
        self.__position_label_attrmap = urwid.AttrMap(self.__position_label,
                                                      self._label_attr)

        self.__text = urwid.Text(u"")
        self.__scrollbar = urwid.Filler(urwid.Padding(
                                        urwid.AttrMap(self.__text,
                                        self._text_attr), 'left', 1))
        self.__columns = urwid.Columns([self.__list], focus_column=0)

        self.__box = urwid.BoxAdapter(self.__columns, height)
        self.__box_attrmap = urwid.AttrMap(self.__box, self._table_attr)

        pile_children = []
        if label:
            pile_children.append(self.__label_attrmap)
        pile_children += [self.__header_attrmap,
                          self.__box,
                          self.__position_label_attrmap]

        self.__pile = urwid.Pile(pile_children)

        self._update_scrollbar()

        super(TableWidget, self).__init__(self.__pile)

    def _update_scrollbar(self):
        n = len(self.__list.body)
        self.__position_label.set_text("(%s / %s)" % (self._position + 1, n))

    def set_focus(self, n):
        self.__list.set_focus(n)

    def focus(self, key):
        for c in self.__items:
            if c._key == key:
                    self.set_focus(self.__items.index(c))

    def selection(self, selection=None):
        if selection:
            for c in self.__items:
                LOGGER.debug("checking: %s" % c)
                if self.multi and c._key in selection:
                    c.select(True)
        selected = [w._key for w in self.__items if w.is_selected()]
        return selected

    def render(self, size, focus=False):

        rows = self.__height
        list_size = len(self.__list.body)
        offset = self.__list.body.focus - self.__list.offset_rows

        if rows < list_size:
            if (rows, list_size) != (self.__rows, self.__list_size):
                self.ratio = float(list_size) / rows
                knob_height = round((rows - 2) / self.ratio)
                self.knob_height = knob_height if knob_height > 1 else 1
                if rows - 2 - self.knob_height > 0:
                    if self.knob_height is 1:
                    #Calculate ourselves, subtracting 3 (for the arrows
                    # and the knob itself)
                        self.below_knob = abs(float(list_size - rows) / (rows -
                                                                         3))
                    else:
                        self.below_knob = abs(float(list_size -
                                                    rows) / (rows - 2 -
                                                             self.ratio))
                else:
                    self.below_knob = float(list_size - rows)
                self.above_knob = int(offset / self.below_knob)
                (self._rows, self.__list_size) = (rows, list_size)
            elif offset != self.__offset:
                above_knob = int(offset / self.below_knob)
                (self.above_knob, self._offset) = (above_knob, offset)
            else:
                rt = super(TableWidget, self).render(size, focus)
                self.__columns.set_focus_column(0)
                return rt

            blocks_above = u'\u2592' * self.above_knob
            blocks_below = u'\u2592' * (rows - self.above_knob - 2 -
                                        self.truncate(self.knob_height))

            self.__text.set_text([('edit', u"▲"), blocks_above +
                                  u"\u2588" * (self.truncate(self.knob_height))
                                  + blocks_below, ('edit', u"▼")])

            (self.__rows, self._offset, self.__list_size) = (rows, offset,
                                                             list_size)
            self._show_scroll_bar()
        else:
            self._hide_scroll_bar()
        rt = super(TableWidget, self).render(size, focus)
        self.__columns.set_focus_column(0)
        return rt

    def truncate(self, x):
        r = round(x)
        if (x - r) > 0.0:
            return int(r) + 1
        return int(r)

    def _hide_scroll_bar(self):
        if self.__scrollbar_visible is True:
            del self.__columns.contents[1]
            self.__scrollbar_visible = False
            self.__rows = -1
            self.__offset = -1
            self.__list_size = -1

    def _show_scroll_bar(self):
        if self.__scrollbar_visible is False:
            self.__columns.contents.append([self.__scrollbar, self.__columns.
                                            options('given', 2)])
            self.__scrollbar_visible = True


class PluginMenuEntry(TableEntryWidget):
    def __init__(self, title, plugin):
        super(PluginMenuEntry, self).__init__(title)
        self._text.plugin = plugin


class PluginMenu(urwid.WidgetWrap):
    """The main menu listing all available plugins (which have a UI)
    FIXME Use TableWidget
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
                LOGGER.debug("No UI page for plugin %s" % plugin)

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


class ModalDialog(urwid.WidgetWrap):
    signals = ['close']

    title = None

    def __init__(self, title, body, escape_key, previous_widget):
        self.escape_key = escape_key
        self.previous_widget = previous_widget

        if type(body) in [str, unicode]:
            body = urwid.Text(body)
        self.title = title
        body = urwid.LineBox(body, title)
        overlay = urwid.Overlay(body, previous_widget, 'center',
                                ('relative', 100), 'bottom',
                                ('relative', 100))
        overlay_attrmap = urwid.AttrMap(overlay, "plugin.widget.dialog")
        super(ModalDialog, self).__init__(overlay_attrmap)

    def close(self):
        urwid.emit_signal(self, "close")

    def __repr__(self):
        return "<%s title='%s' at %s>" % (self.__class__.__name__, self.title,
                                          hex(id(self)))


class Label(urwid.WidgetWrap):
    """A read only widget representing a label
    """

    def __init__(self, label):
        self._label = urwid.Text(label)
        self._label_attrmap = urwid.AttrMap(self._label,
                                            "plugin.widget.label")
        super(Label, self).__init__(self._label_attrmap)

    def text(self, value=None):
        if value is not None:
            self._label.set_text(value)
        return self._label.get_text()

    def set_text(self, txt):
        self.text(txt)


class Notice(Label):
    """A read only widget for notices
    """
    _notice_attr = "plugin.widget.notice"

    def __init__(self, label):
        super(Notice, self).__init__(label)
        self._label_attrmap.set_attr_map({None: self._notice_attr})


class Header(Label):
    """A read only widget representing a header
    """
    _header_attr = "plugin.widget.header"

    def __init__(self, label, template="\n  %s\n"):
        super(Header, self).__init__(template % label)
        self._label_attrmap.set_attr_map({None: self._header_attr})


class KeywordLabel(Label):
    """A read only widget consisting of a "<b><keyword>:</b> <value>"
    """
    _keyword_attr = "plugin.widget.label.keyword"
    _text_attr = "plugin.widget.label"

    def __init__(self, keyword, label=""):
        super(KeywordLabel, self).__init__(label)
        self._keyword = keyword
        self.text(label)
#        self._label_attrmap.set_attr_map({None: ""})

    def text(self, text=None):
        if text is not None:
            self._text = text
            keyword_markup = (self._keyword_attr, self._keyword)
            text_markup = (self._text_attr, self._text)
            markup = [keyword_markup, text_markup]
            self._label.set_text(markup)
        return self._text


class Entry(NoticeDecoration):
    signals = ['change', 'click']

    _selectable = True

    def __init__(self, label, mask=None, align_vertical=False):
        with_linebox = False
        self._align_vertical = align_vertical

        if with_linebox:
            label = "\n" + label

        self._label = urwid.Text(label)
        self._label_attrmap = urwid.AttrMap(self._label,
                                            "plugin.widget.entry.label")
        self._edit = urwid.Edit(mask=mask, wrap="clip",
                                layout=UnderscoreRight())
        self._edit_attrmap = urwid.AttrMap(self._edit, "plugin.widget.entry")
        self._linebox = urwid.LineBox(self._edit_attrmap)
        self._linebox_attrmap = urwid.AttrMap(self._linebox,
                                              "plugin.widget.entry.frame")

        input_widget = self._edit_attrmap
        if with_linebox:
            input_widget = self._linebox_attrmap

        alignment_widget = urwid.Columns
        if self._align_vertical:
            alignment_widget = urwid.Pile
        self._columns = alignment_widget([self._label_attrmap,
                                          input_widget])

        self._pile = urwid.Pile([self._columns])

        def on_widget_change_cb(widget, new_value):
            urwid.emit_signal(self, 'change', self, new_value)
        urwid.connect_signal(self._edit, 'change', on_widget_change_cb)

        super(Entry, self).__init__(self._pile)

    def enable(self, is_enabled):
        self._selectable = is_enabled
        edit_attr_map = {None: "plugin.widget.entry"}
        linebox_attr_map = {None: "plugin.widget.entry.frame"}
        if not is_enabled:
            edit_attr_map = {None: "plugin.widget.entry.disabled"}
            linebox_attr_map = {None: "plugin.widget.entry.frame.disabled"}
        self._edit_attrmap.set_attr_map(edit_attr_map)
        self._linebox_attrmap.set_attr_map(linebox_attr_map)

    def valid(self, is_valid):
        attr_map_label = {None: "plugin.widget.entry.label"}
        attr_map_edit = {None: "plugin.widget.entry"}
        attr_map_linebox = {None: "plugin.widget.entry.frame"}
        if is_valid:
            self.set_notice(None)
        else:
            attr_map_label = {None: "plugin.widget.entry.label.invalid"}
            attr_map_edit = {None: "plugin.widget.entry.invalid"}
            attr_map_linebox = {None: "plugin.widget.entry.frame.invalid"}
        if self._selectable:
            # Only update style if it is selectable/enabled
            self._label_attrmap.set_attr_map(attr_map_label)
            self._edit_attrmap.set_attr_map(attr_map_edit)
            self._linebox_attrmap.set_attr_map(attr_map_linebox)

    def set_text(self, txt):
        self._edit.set_edit_text(txt or "")

    def selectable(self):
        return self._selectable


class PasswordEntry(Entry):
    def __init__(self, label, align_vertical=False):
        super(PasswordEntry, self).__init__(label, mask="*",
                                            align_vertical=align_vertical)


class Button(NoticeDecoration):
    signals = ["click"]

    _selectable = True

    _button_attr = "plugin.widget.button"
    _button_disabled_attr = "plugin.widget.button.disabled"

    def __init__(self, label, is_enabled=True):
        self._button = urwid.Button(label)

        def on_click_cb(widget, data=None):
            if self.selectable():
                urwid.emit_signal(self, 'click', self)
        urwid.connect_signal(self._button, 'click', on_click_cb)

        self._button_attrmap = urwid.AttrMap(self._button, self._button_attr)

        self._padding = urwid.Padding(self._button_attrmap,
                                      width=self.width())

        self.enable(is_enabled)

        super(Button, self).__init__(self._padding)

    def selectable(self):
        return self._selectable

    def enable(self, is_enabled):
        self._selectable = is_enabled
        if is_enabled:
            amap = {None: self._button_attr}
        else:
            amap = {None: self._button_disabled_attr}
        self._button_attrmap.set_attr_map(amap)

    def width(self):
        return len(self._button.label) + 4


class Divider(urwid.WidgetWrap):
    def __init__(self, char=u" "):
        self._divider = urwid.Divider(char)
        self._divider_attrmap = urwid.AttrMap(self._divider,
                                              "plugin.widget.divider")
        super(Divider, self).__init__(self._divider_attrmap)


class Options(urwid.WidgetWrap):
    signals = ["change"]

    _selectable = True
    _label_attr = "plugin.widget.options.label"
    _option_attr = "plugin.widget.options"
    _option_disabled_attr = "plugin.widget.options.disabled"

    def __init__(self, label, options, selected_option_key):
        self._options = options
        self._button_to_key = {}
        self._bgroup = []
        self._label = urwid.Text(label)
        self._label_attrmap = urwid.AttrMap(self._label, self._label_attr)

        self._buttons = []
        for option_key, option_label in self._options:
            widget = urwid.RadioButton(self._bgroup, option_label,
                                       on_state_change=self._on_state_change)
            self._button_to_key[widget] = option_key
            if option_key == selected_option_key:
                widget.set_state(True)
            widget_attr = urwid.AttrMap(widget, self._option_attr)
            self._buttons.append(widget_attr)
        self._columns = urwid.Columns([self._label_attrmap] + self._buttons)
        self._pile = urwid.Pile([self._columns])
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
                    LOGGER.debug("Selected option %s (%s)" % (key, button))
        LOGGER.warning("Could not set selection '%s'" % key)

    def set_text(self, txt):
        self.select(txt)

    def selectable(self):
        return self._selectable

    def enable(self, is_enabled):
        self._selectable = is_enabled
        if is_enabled:
            amap = {None: self._option_attr}
        else:
            amap = {None: self._option_disabled_attr}
        for am in self._buttons:
            am.set_attr_map(amap)


class Checkbox(urwid.WidgetWrap):
    signals = ['change']
    _selectable = True

    _checkbox_attr = "plugin.widget.checkbox"
    _checkbox_disabled_attr = "plugin.widget.checkbox.disabled"

    def __init__(self, label, state):
        self._label = urwid.Text(label)
        self._label_attrmap = urwid.AttrMap(self._label,
                                            "plugin.widget.checkbox.label")
        self._checkbox = urwid.CheckBox("", state)
        self._checkbox_attrmap = urwid.AttrMap(self._checkbox,
                                               self._checkbox_attr)
        self._divider = urwid.Divider()
        self._container = urwid.Columns([self._label_attrmap,
                                         self._checkbox_attrmap])

        def on_change_cb(widget, new_value):
            urwid.emit_signal(self, 'change', self, new_value)
        urwid.connect_signal(self._checkbox, 'change', on_change_cb)

        super(Checkbox, self).__init__(urwid.Pile([self._container,
                                                   self._divider]))

    def set_text(self, s):
        if s in [True, False]:
            self._checkbox.set_state(s)
        else:
            raise Exception("Invalid value: %s" % s)

    def selectable(self):
        return self._selectable

    def enable(self, is_enabled):
        self._selectable = is_enabled
        if is_enabled:
            amap = {None: self._checkbox_attr}
        else:
            amap = {None: self._checkbox_disabled_attr}
        self._checkbox_attrmap.set_attr_map(amap)


class PageWidget(NoticeDecoration):
    save_button = None

    def __init__(self, widgets, title=None):
#        self._listwalker = urwid.SimpleListWalker(widgets)
#        self._container = urwid.ListBox(self._listwalker)
        self._container = TabablePile(widgets)
        self._container_attrmap = urwid.AttrMap(self._container,
                                                "plugin.widget.page")
        self._header = None
        if title:
            self._header = urwid.AttrMap(urwid.Text(title),
                                         "plugin.widget.page.header")
        self._frame = urwid.Frame(self._container_attrmap, self._header)
        self._box = urwid.Padding(self._frame, width=("relative", 97))
        super(PageWidget, self).__init__(self._box)


class RowWidget(urwid.Columns):
    pass


class ProgressBarWidget(urwid.WidgetWrap):
    def __init__(self, current, done):
        self._progressbar = urwid.ProgressBar(
            "plugin.widget.progressbar.uncomplete",
            "plugin.widget.progressbar.complete",
            current, done)
        self._linebox = urwid.LineBox(self._progressbar)
        self._linebox_attrmap = urwid.AttrMap(self._linebox,
                                              "plugin.widget.progressbar.box")
        super(ProgressBarWidget, self).__init__(self._linebox_attrmap)

    def set_completion(self, v):
        self._progressbar.set_completion(v)


class UnderscoreRight(urwid.StandardTextLayout):
    def layout(self, text, width, align, wrap):
        s = urwid.StandardTextLayout.layout(self, text, width, align, wrap)
        out = []
        last_offset = 0
        for row in s:
            used = 0
            for seg in row:
                used += seg[0]
                if len(seg) == 3:
                    last_offset = seg[2]
            if used == width:
                out.append(row)
                continue
            fill = width - used
            if fill == width:
                #Fake out empty entries
                row = [(1, 0, 1), (0, 1)]
                last_offset = 1
            if fill < 0:
                fill = 1
            out.append(row + [(fill, last_offset, '_'*fill)])
        return out


class TabablePile(urwid.Pile):
    """A pile where you can use (shift+)tab to cycle (back-)forward through the
    children
    """
    def keypress(self, size, key):
        new_pos = self.focus_position
        delta = 0
        LOGGER.debug("tab key: %s" % key)
        if "tab" in key:
            delta = 1
        elif "shift tab" in key:
            delta = -1
        if delta:
            LOGGER.debug("Setting focus to: %s" % new_pos)
            while new_pos >= 0 and new_pos < len(self.contents):
                new_pos += delta
                new_pos = new_pos % len(self.contents)
                if self.contents[new_pos][0].selectable():
                    self.focus_position = new_pos
                    break
            LOGGER.debug("Focus on: %s" % self.focus)
        return super(TabablePile, self).keypress(size, key)
