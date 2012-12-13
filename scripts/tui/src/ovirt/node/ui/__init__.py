#!/usr/bin/python
# -*- coding: utf-8 -*-
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
from ovirt.node import base
import traceback

"""
This contains abstract UI Elements
"""


# http://stackoverflow.com/questions/739654/understanding-python-decorators
class Element(base.Base):
    """An abstract UI Element.
    This basically provides signals to communicate between real UI widget and
    the plugins
    """
    _signal_cbs = None

    def __init__(self):
        """Registers all widget signals.
        All signals must be given in self.signals
        """
        super(Element, self).__init__()
        self.logger.debug("Initializing new %s" % self)

    def set_text(self, value):
        """A general way to set the "text" of a widget
        """
        raise NotImplementedError


class InputElement(Element):
    """An abstract UI Element pfor user input
    """

    def __init__(self, name, is_enabled):
        super(InputElement, self).__init__()
        self.name = name
        self.enabled(is_enabled)

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
    title = None

    def __init__(self, children, title=None):
        super(ContainerElement, self).__init__()
        self.children = children
        self.title = title

    def children(self, v=None):
        if v:
            self.children = v
        return self.children


class Page(ContainerElement):
    """An abstract page with a couple of widgets
    """
    buttons = []

    def __init__(self, children, title=None):
        super(Page, self).__init__(children, title)
        self.buttons = self.buttons or [
                        (None, SaveButton()),
                        (None, ResetButton())
                        ]


class Dialog(Page):
    """An abstract dialog, similar to a page
    """

    escape_key = "esc"

    def __init__(self, title, children):
        super(Dialog, self).__init__(children, title)
        self.close(False)

    @Element.signal_change
    def close(self, v=True):
        self._close = v


class InfoDialog(Dialog):
    def __init__(self, title, children):
        super(InfoDialog, self).__init__(title, children)
        self.buttons = [(None, CloseButton())]


class Row(ContainerElement):
    """Align elements horizontally in one row
    """
    pass


class Label(Element):
    """Represents a r/o label
    """

    def __init__(self, text):
        super(Label, self).__init__()
        self.text(text)

    @Element.signal_change
    def text(self, text=None):
        if text != None:
            self._text = text
        return self._text

    def set_text(self, txt):
        self.text(txt)


class Header(Label):
    template = "\n  %s\n"

    def __init__(self, text, template=template):
        super(Header, self).__init__(text)
        self.template = template


class KeywordLabel(Label):
    """A label consisting of a prominent keyword and a value.
    E.g.: <b>Networking:</b> Enabled
    """

    def __init__(self, keyword, text=""):
        super(KeywordLabel, self).__init__(text)
        self.keyword = keyword


class Entry(InputElement):
    """Represents an entry field
    TODO multiline
    """

    def __init__(self, label, enabled=True, align_vertical=False):
        super(Entry, self).__init__(label, enabled)
        self.label = label
        self.align_vertical = align_vertical
        self.valid(True)

    @Element.signal_change
    def valid(self, is_valid):
        if is_valid in [True, False]:
            self._valid = is_valid
        return self._valid


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


class ResetButton(Button):
    def __init__(self, enabled=True):
        super(ResetButton, self).__init__("Reset", enabled)


class CloseButton(Button):
    def __init__(self, enabled=True):
        super(CloseButton, self).__init__("Close", enabled)


class Divider(Element):
    def __init__(self, char=u" "):
        super(Divider, self).__init__()
        self.char = char


class Options(InputElement):
    """A selection of options

    Args:
        label: The caption of the options
        options:
    """
    def __init__(self, label, options):
        super(Options, self).__init__(label, True)
        self.label = label
        self.options = options
        self.option(options[0])

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
    def __init__(self, label, state=False, is_enabled=True):
        super(Checkbox, self).__init__(label, is_enabled)
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
        super(ProgressBar, self).__init__()
        self.current(current)
        self.done = done

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
        super(Table, self).__init__(label, enabled)
        self.label = label
        self.header = header
        self.items = items
        self.height = height

    @Element.signal_change
    def select(self, selected=None):
        if selected in dict(self.items).keys():
            self._selected = selected
        return self._selected


class Window(Element):
    """Abstract Window definition
    """

    def __init__(self, app):
        super(Window, self).__init__()
        self.logger.info("Creating UI for application '%s'" % app)
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
        self.logger.debug("Registering hotkey '%s': %s" % (hotkey, cb))
        self._hotkeys[str(hotkey)] = cb

    def show_dialog(self, dialog):
        """Show a dialog.
        The dialog can be closed using dialog.close()

        Args:
            dialog: The dialog to be shown
        """
        raise NotImplementedError

    def show_page(self, page):
        """Show / switch to a page.
        Displays the given page (which does not need to be patr of a plugin)

        Args:
            page: The page to be shown
        """
        raise NotImplementedError

    def run(self):
        raise NotImplementedError


class TransactionProgressDialog(Dialog):
    def __init__(self, transaction, plugin, initial_text=""):
        self.transaction = transaction
        self.texts = [initial_text, ""]
        self.plugin = plugin

        self._close_button = CloseButton()
        self.buttons = [(None, self._close_button)]
        self._progress_label = Label(initial_text)
        widgets = [("dialog.progress", self._progress_label)]
        super(TransactionProgressDialog, self).__init__(self.transaction.title,
                                                        widgets)

    def add_update(self, txt):
        self.texts.append(txt)
        self._progress_label.set_text("\n".join(self.texts))

    def run(self):
        self.plugin.application.ui.show_dialog(self)
        self._close_button.enabled(False)
        try:
            self.transaction.prepare()  # Just to display something in dry mode
            for idx, e in enumerate(self.transaction):
                txt = "(%s/%s) %s" % (idx + 1, len(self.transaction), e.title)
                self.add_update(txt)
                self.plugin.dry_or(lambda: e.commit())
            self.add_update("\nAll changes were applied successfully.")
        except Exception as e:
            self.add_update("\nAn error occurred when applying the changes:")
            self.add_update(e.message)
            self.logger.warning("'%s' on transaction '%s': %s - %s" %
                                (type(e), self.transaction, e, e.message))
            self.logger.debug(str(traceback.format_exc()))
        self._close_button.enabled(True)
