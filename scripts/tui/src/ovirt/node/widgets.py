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
        for title, plugin in self.__pages.items():
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


class Header(Label):
    """A read only widget representing a header
    """

    def __init__(self, text):
        super(Header, self).__init__("\n  %s\n" % text)
        self._label_attrmap.set_attr_map({None: "plugin.widget.header"})


class Entry(urwid.WidgetWrap):

    signals = ['change']

    notice = property(lambda self: self._notice.get_text(), \
                      lambda self, v: self._notice.set_text(v))

    selectable = lambda self: True

    def enable(self, is_enabled):
        self.selectable = lambda: is_enabled
        if is_enabled:
            self._edit_attrmap.set_attr_map({None: ""})
        else:
            self._edit_attrmap.set_attr_map({
                None: "plugin.widget.disabled"
                })

    def __init__(self, label, value=None, mask=None):
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

        if value:
            self._edit.set_edit_text(value)

        def on_widget_change_cb(widget, new_value):
            urwid.emit_signal(self, 'change', self, new_value)
        urwid.connect_signal(self._edit, 'change', on_widget_change_cb)

        super(Entry, self).__init__(self._pile)


class PasswordEntry(Entry):
    def __init__(self, label, value=None):
        super(PasswordEntry, self).__init__(label, value, mask="*")
