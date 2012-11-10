#!/usr/bin/python
#
# __init__.py - Copyright (C) 2012 Red Hat, Inc.
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
This contains abstract UI Elements
"""
import logging

LOGGER = logging.getLogger(__name__)


def deprecated(func):
    LOGGER.warning("Deprecated %s" % func)
    return lambda *args, **kwargs: func(*args, **kwargs)


# http://stackoverflow.com/questions/739654/understanding-python-decorators
class Element(object):
    """An abstract UI Element.
    This basically provides signals to communicate between real UI widget and
    the plugins
    """
    _signal_cbs = None

    def __init__(self):
        """Registers all widget signals.
        All signals must be given in self.signals
        """
        LOGGER.debug("Initializing new %s" % self)

    @staticmethod
    def signal_change(func):
        """A decorator for methods which should emit signals
        """
        def wrapper(self, userdata=None, *args, **kwargs):
            signame = func.__name__
            self._register_signal(signame)
            self.emit_signal(signame, userdata)
            return func(self, userdata)
        return wrapper

    def _register_signal(self, name):
        """Each signal that get's emitted must be registered using this
        function.

        This is just to have an overview over the signals.
        """
        if self._signal_cbs is None:
            self._signal_cbs = {}
        if name not in self._signal_cbs:
            self._signal_cbs[name] = []
            LOGGER.debug("Registered new signal '%s' for '%s'" % (name, self))

    def connect_signal(self, name, cb):
        """Connect an callback to a signal
        """
        if not self._signal_cbs:
            raise Exception("Signals not initialized %s for %s" % (name, self))
        if name not in self._signal_cbs:
            raise Exception("Unregistered signal %s for %s" % (name, self))
        self._signal_cbs[name].append(cb)

    def emit_signal(self, name, userdata=None):
        """Emit a signal
        """
        if self._signal_cbs is None or name not in self._signal_cbs:
            return False
        LOGGER.debug("Emitting '%s'" % name)
        for cb in self._signal_cbs[name]:
            LOGGER.debug("... %s" % cb)
            cb(self, userdata)

    def set_text(self, value):
        """A general way to set the "text" of a widget
        """
        raise NotImplementedError


class InputElement(Element):
    """An abstract UI Element pfor user input
    """

    def __init__(self, name, is_enabled):
        self.name = name
        self.enabled(is_enabled)
        super(InputElement, self).__init__()

    @Element.signal_change
    def enabled(self, is_enabled=None):
        if is_enabled in [True, False]:
            self._enabled = is_enabled
        return self._enabled

    @Element.signal_change
    def text(self, text=None):
        if text != None:
            self._text = text
        return self._text

    def set_text(self, txt):
        self.text(txt)


class ContainerElement(Element):
    """An abstract container Element containing other Elements
    """
    children = []

    def __init__(self, children):
        self.children = children
        super(ContainerElement, self).__init__()

    def children(self, v=None):
        if v:
            self.children = v
        return self.children


class Page(ContainerElement):
    """An abstract page with a couple of widgets
    """
    has_save_button = True


class Dialog(Page):
    """An abstract dialog, similar to a page
    """

    def __init__(self, title, children):
        self.title = title
        self.close(False)
        super(Dialog, self).__init__(children)

    @Element.signal_change
    def close(self, v=True):
        self._close = v


class Row(ContainerElement):
    """Align elements horizontally in one row
    """
    pass


class Label(Element):
    """Represents a r/o label
    """

    def __init__(self, text):
        self.text(text)
        super(Label, self).__init__()

    @Element.signal_change
    def text(self, text=None):
        if text != None:
            self._text = text
        return self._text

    def set_text(self, txt):
        self.text(txt)


class Header(Label):
    pass


class KeywordLabel(Label):
    """A label consisting of a prominent keyword and a value.
    E.g.: <b>Networking:</b> Enabled
    """

    def __init__(self, keyword, text=""):
        super(Label, self).__init__()
        self.keyword = keyword
        self.text(text)


class Entry(InputElement):
    """Represents an entry field
    TODO multiline
    """

    def __init__(self, label, enabled=True, align_vertical=False):
        self.label = label
        self.align_vertical = align_vertical
        super(Entry, self).__init__(label, enabled)


class PasswordEntry(Entry):
    pass


class Button(InputElement):
    def __init__(self, label, enabled=True):
        super(Button, self).__init__(label, enabled)
        self.text(label)

    @Element.signal_change
    def label(self, label=None):
        if label != None:
            self._label = label
        return self._label

    def set_text(self, txt):
        self.text(txt)


class SaveButton(Button):
    def __init__(self, enabled=True):
        super(SaveButton, self).__init__("Save", enabled)


class Divider(Element):
    def __init__(self, char=u" "):
        self.char = char


class Options(Element):
    """A selection of options

    Args:
        label: The caption of the options
        options:
    """
    def __init__(self, label, options):
        self.label = label
        self.options = options
        self.option(options[0])
        super(Options, self).__init__()

    @Element.signal_change
    def option(self, option=None):
        if option in self.options:
            self._option = option
        return self._option

    def set_text(self, txt):
        self.option(txt)


class Checkbox(InputElement):
    """A simple Checkbox

    Args:
        label: Caption of this checkbox
        state: The initial change
    """
    def __init__(self, label, state=False):
        self.label = label
        self.state(state)

    @Element.signal_change
    def state(self, s):
        if s in [True, False]:
            self._state = s
        return self._state


class ProgressBar(Element):
    """A abstract progress bar.

    Args:
        current: The initial value
        done: The maximum value
    """
    def __init__(self, current=0, done=100):
        self.current(current)
        self.done = done
        super(ProgressBar, self).__init__()

    @Element.signal_change
    def current(self, current=None):
        """Get/Set the current status

        Args:
            current: New value or None

        Returns:
            The current progress
        """
        if current is not None:
            self._current = current
        return self._current


class Table(InputElement):
    """Represents a simple Table with one column

    Args:
        header: A string
        items: A list of tuples (key, label)
        height: The height of the Table
    """

    def __init__(self, label, header, items, height=5, enabled=True):
        self.label = label
        self.header = header
        self.items = items
        self.height = height
        super(Table, self).__init__(label, enabled)

    @Element.signal_change
    def select(self, selected=None):
        if selected in dict(self.items).keys():
            self._selected = selected
        return self._selected


class Window(Element):
    """Abstract Window definition
    """

    def __init__(self, app):
        LOGGER.info("Creating UI for application '%s'" % app)
        self.app = app

        self._plugins = {}
        self._hotkeys = {}

        self.footer = None

    def register_plugin(self, title, plugin):
        """Register a plugin to be shown in the UI
        """
        self._plugins[title] = plugin

    def register_hotkey(self, hotkey, cb):
        """Register a hotkey
        """
        if type(hotkey) is str:
            hotkey = [hotkey]
        LOGGER.debug("Registering hotkey '%s': %s" % (hotkey, cb))
        self._hotkeys[str(hotkey)] = cb

    def run(self):
        raise NotImplementedError
