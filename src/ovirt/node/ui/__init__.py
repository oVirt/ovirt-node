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
from ovirt.node.utils import console, security
from ovirt.node.exceptions import InvalidData

"""
This contains abstract UI Elements
"""


# http://stackoverflow.com/questions/739654/understanding-python-decorators
class Element(base.Base):
    """An abstract UI Element.
    This basically provides signals to communicate between real UI widget and
    the plugins

    Args:
        path: The model path this item is mapped to
        on_value_change: Emitted by the value() method if the value changes
        on_exception: Signal to be called when an exception is raosed during a
                      callback
    """
    path = None
    on_value_change = None

    on_exception = None

    def __init__(self, path=None):
        """Registers all widget signals.
        All signals must be given in self.signals
        """
        super(Element, self).__init__()
        self.path = path
        self.on_value_change = self.new_signal()
        self.on_notice_change = self.new_signal()
        self.logger.debug("Initializing %s" % self)

    def value(self, value=None):
        """A general way to set the "value" of a widget
        Can be a text or selection, ...
        """
        raise NotImplementedError

    def elements(self):
        return [self]

    def notice(self, txt):
        """Protoype command to show a notice associated with this element
        """
        self.on_notice_change(txt)

    def __repr__(self):
        return "<%s path='%s' at %s>" % (self.__class__.__name__, self.path,
                                         hex(id(self)))


class InputElement(Element):
    """An abstract UI Element for user input

    Args:
        on_change: To be called by the consumer when the associated widget
                   changed

        on_enabled_change: Called by the Element when enabled changes°
        on_valid_change: Called by the Element when validity changes°
    """
    on_change = None

    on_label_change = None
    on_enabled_change = None
    on_valid_change = None

    def __init__(self, path, label, is_enabled):
        super(InputElement, self).__init__(path)
        self.on_label_change = self.new_signal()
        self.on_enabled_change = self.new_signal()
        self.on_change = self.new_signal()
        self.on_valid_change = self.new_signal()
        self.label(label)
        self.enabled(is_enabled)
        self.text("")
        self.valid(True)

        self.on_change.connect(ChangeAction())

    def enabled(self, is_enabled=None):
        """Enable or disable the widget wrt user input
        """
        if is_enabled in [True, False]:
            self.on_enabled_change(is_enabled)
            self._enabled = is_enabled
        return self._enabled

    def valid(self, is_valid=None):
        """Get or set the validity of this element.
        If a reason is given show it as a notice.
        """
        if is_valid in [True, False]:
            self.on_valid_change(is_valid)
            self._valid = is_valid
        return self._valid

    def _validates(self):
        """Validate the value of this widget against the validator
        This funcion is mainly needed to implement widget specific
        validation methods
        """
        pass

    def text(self, text=None):
        """Get or set the textual value
        """
        if text is not None:
            self.on_value_change(text)
            self._text = text
        return self._text

    def label(self, label=None):
        """Can be used to retrieve or change the label
        """
        if label is not None:
            self.on_label_change(label)
            self._label = label
        return self._label

    def value(self, txt=None):
        return self.text(txt)


class ContainerElement(Element):
    """An abstract container Element containing other Elements
    """
    children = []
    title = None

    def __init__(self, path, children, title=None):
        super(ContainerElement, self).__init__(path)
        self.children = children
        self.title = title

    def elements(self):
        """Retrieve all Elements in this Element-Tree in a flat dict
        Returns:
            dict of mapping (path, element)
        """
        elements = [self]
        for element in self.children:
            elements += element.elements()
        return elements

    def value(self, dummy):
        """A container doesn't have a single value, therefor None
        """
        return NotImplementedError

    def enabled(self, is_enabled=True):
        """Enable/Disable all children
        """
        if is_enabled in [True, False]:
            for child in self.children:
                child.enabled(is_enabled)
        return all(child.enabled() for child in self.children)

    def __getitem__(self, path):
        return dict((c.path, c) for c in self.children)[path]


class Action(base.Base):
    callback = None

    def __init__(self, callback=None):
        super(Action, self).__init__()
        self.callback = callback

    def __call__(self, target, userdata=None):
        r = None
        if self.callback:
            self.logger.debug("Calling action %s %s with %s" % (self,
                                                                self.callback,
                                                                userdata))

            r = self.callback(userdata)
            self.logger.debug("Action %s called and returned: %s" % (self,
                                                                     r))
        else:
            self.logger.warning("No callback for %s" % self)
        return r

    def __str__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.callback)


class ChangeAction(Action):
    """Action to validate the current change
    """
    pass


class SaveAction(Action):
    """Action to save the current page/dialog
    """
    pass


class CloseAction(Action):
    """Action to close the current/given dialog

    Args:
        dialog: The dialog to close
    """
    dialog = None

    def __init__(self, callback=None, dialog=None):
        super(CloseAction, self).__init__(callback)
        self.dialog = dialog


class ResetAction(Action):
    """Action to reset all InputElements on the current page/dialog
    """
    pass


class ReloadAction(Action):
    """Action to reload the current page/dialog
    """
    pass


class QuitAction(Action):
    """Action to quit the application
    """
    pass


class Row(ContainerElement):
    """Align elements horizontally in one row
    """
    pass


class Label(Element):
    """Represents a r/o label
    """

    def __init__(self, path, text):
        super(Label, self).__init__(path)
        self.text(text)

    def text(self, text=None):
        if text is not None:
            self.on_value_change(text)
            self._text = text
        return self._text

    def value(self, txt=None):
        return self.text(txt)


class Notice(Label):
    def __init__(self, path, text):
        super(Notice, self).__init__(path, text)


class Header(Label):
    template = "\n  %s\n"

    def __init__(self, path, text, template=template):
        super(Header, self).__init__(path, text)
        self.template = template


class KeywordLabel(Label):
    """A label consisting of a prominent keyword and a value.
    E.g.: <b>Networking:</b> Enabled
    """

    def __init__(self, path, keyword, text=""):
        super(KeywordLabel, self).__init__(path, text)
        self.keyword = keyword


class Entry(InputElement):
    """Represents an entry field
    TODO multiline

    Args:
        on_valid_change: Is emitted by this class when the value of valid
                         changes e.g. when a plugin is changing it.
    """

    def __init__(self, path, label, enabled=True, align_vertical=False):
        super(Entry, self).__init__(path, label, enabled)
        self.align_vertical = align_vertical


class PasswordEntry(Entry):
    pass


class ConfirmedEntry(ContainerElement):
    """A container for elements which must be identical
    """

    on_change = None
    on_valid_change = None

    _primary = None
    _secondary = None

    _changes = None

    is_password = False
    min_length = 0
    _additional_notice = None

    def __init__(self, path, label, is_password=False, min_length=0):
        self.on_change = self.new_signal()
        self.on_valid_change = self.new_signal()
        self._changes = {}

        children = []

        entry_class = PasswordEntry if is_password else Entry
        self._primary = entry_class("%s[0]" % path,
                                    label)
        self._secondary = entry_class("%s[1]" % path,
                                      "Confirm %s" % label)
        self._notice = Notice("%s.notice" % path, "")
        children += [self._primary, self._secondary, self._notice]

        for child in [self._primary, self._secondary]:
            self._changes[child.path] = ""
            # Remove all callbacks - so we don't triggre on_change and friends
            # We redirect it to call the validation methods of this widget
            child.on_change.clear()
            child.on_change.connect(self.__on_change)

        if is_password:
            self.is_password = is_password
            self.min_length = min_length

        self.on_change.connect(ChangeAction())

        super(ConfirmedEntry, self).__init__(path, children)

    def _validates(self):
        if self.is_password:
            self.logger.debug("Doing security check")
            msg = ""
            pw, pwc = self._values()
            try:
                msg = security.password_check(pw, pwc,
                                              min_length=self.min_length)
            except ValueError as e:
                msg = e.message
                if msg:
                    raise InvalidData(msg)
            self._additional_notice = msg

    def __on_change(self, target, change):
        self._additional_notice = ""
        self._changes.update(change)
        self.on_change({self.path: self.value()})

    def _values(self):
        return (self._changes[self._primary.path],
                self._changes[self._secondary.path])

    def value(self, new_value=None):
        if new_value is not None:
            pass
        return self._values()[0]

    def valid(self, is_valid=None):
        if is_valid in [True, False]:
            self._primary.valid(is_valid)
            self._secondary.valid(is_valid)
            self.on_valid_change(is_valid)
        return self._primary.valid()

    def notice(self, txt=""):
        msg = "\n".join(t for t in [txt, self._additional_notice] if t)
        self._notice.text(msg)


class Button(InputElement):
    """A button can be used to submit or save the current page/dialog
    There are several derivatives which are "shortcuts" to launch a specific
    action.

    Args:
        on_activate: The signal shall be called by the toolkit implementing the
                     button, when the button got "clicked"
    """
    on_activate = None

    def __init__(self, path, label, enabled=True):
        """Constructor

        Args:
            path: Path within the model
            label: Label of the button
            enabled: If the button is enabled (can be clicked)
        """
        super(Button, self).__init__(path, label, enabled)
        self.text(label)
        self.label(label)

        self.on_activate = self.new_signal()
        self.on_activate.connect(ChangeAction())
        self.on_activate.connect(SaveAction())

    def value(self, value=None):
        self.on_value_change(value)
        self.label(value)


class SaveButton(Button):
    """This derived class is primarily needed to allow an easy disabling of the
    save button when the changed data is invalid.
    """
    def __init__(self, path, label="Save", enabled=True):
        super(SaveButton, self).__init__(path, label, enabled)


class ResetButton(Button):
    """This button calls the ResetAction to reset all UI data to the current
    model, discrading all pending changes.
    """
    def __init__(self, path, label="Reset", enabled=True):
        super(ResetButton, self).__init__(path, label, enabled)
        self.on_activate.clear()
        self.on_activate.connect(ResetAction())
        self.on_activate.connect(ReloadAction())


class CloseButton(Button):
    """The close button can be used to close the top-most dialog
    """
    def __init__(self, path, label="Close", enabled=True):
        super(CloseButton, self).__init__(path, label, enabled)
        self.on_activate.clear()
        self.on_activate.connect(CloseAction())


class QuitButton(Button):
    """The quit button can be used to quit the whole application
    """
    def __init__(self, path, label="Quit", enabled=True):
        super(QuitButton, self).__init__(path, label, enabled)
        self.on_activate.clear()
        self.on_activate.connect(QuitAction())


class Divider(Element):
    """A divider can be used to add some space between UI Elements.

    Args:
        char: A (optional) char to be used as a separator
    """
    def __init__(self, path, char=u" "):
        super(Divider, self).__init__(path)
        self.char = char


class Options(InputElement):
    """A selection of options

    Args:
        label: The caption of the options
        options:
    """

    def __init__(self, path, label, options, selected=None):
        super(Options, self).__init__(path, label, True)
        self.options = options
        self.option(selected or options[0][0])

    def option(self, option=None):
        if option in dict(self.options).keys():
            self.on_value_change(option)
            self._option = option
        return self._option

    def value(self, value=None):
        return self.option(value)


class Checkbox(InputElement):
    """A simple Checkbox

    Args:
        label: Caption of this checkbox
        state: The initial change
    """

    def __init__(self, path, label, state=False, is_enabled=True):
        super(Checkbox, self).__init__(path, label, is_enabled)
        self.state(state)

    def state(self, s=None):
        if s in [True, False]:
            self.on_value_change(s)
            self._state = s
        return self._state

    def value(self, value=None):
        return self.state(value)


class ProgressBar(Element):
    """A abstract progress bar.

    Args:
        current: The initial value
        done: The maximum value
    """
    def __init__(self, path, current=0, done=100):
        super(ProgressBar, self).__init__(path)
        self.current(current)
        self.done = done

    def current(self, current=None):
        """Get/Set the current status

        Args:
            current: New value or None

        Returns:
            The current progress
        """
        if current is not None:
            self.on_value_change(current)
            self._current = current
        return self._current

    def value(self, value):
        return self.current(value)


class Table(InputElement):
    """Represents a simple Table with one column
    """
    _selected = None
    on_activate = None

    def __init__(self, path, label, header, items, selected_item=None,
                 height=5, enabled=True, multi=False):
        """Args:
        path: The model path to map to
        label: An optional label
        header: The header above the cells, can be used to name the rows)
        items: A list of tuples (key, label) (both str like)
        height: The height of the Table
        selected_item: The item (key) which shall be selected initially
        enabled: Whether the table can be changed or not
        multi: Whether we allow multiple items to be selected
        """
        super(Table, self).__init__(path, label, enabled)
        self.header = header
        if type(items) in [str, tuple, unicode]:
            #For convenience, create a list of tuples if it is not already one
            if type(items) in [str, unicode]:
                self.items = [(i, item) for i, item in zip(range(len(
                                                           items.split('\n'))),
                                                           items.split('\n'))]
            elif type(items) is tuple:
                self.items = [items]
        else:
            self.items = items
        self.height = height
        self.multi = multi
        self.on_activate = self.new_signal()
        if multi:
            self.selection(selected_item or [])
            self.on_activate.connect(ChangeAction())
            self.on_change.clear()
        else:
            if selected_item or self.items:
                self.selection(selected_item or self.items[0][0])
            self.on_activate.connect(ChangeAction())
            self.on_activate.connect(SaveAction())

    def selection(self, selected=None):
        """Get/Select the given item (key) or multiple items if multi

        Args:
            selected: The item key to be selected
        Returns:
            The select item key or a list of keys which are selected
        """
        if self.multi:
            return self.__selection_multi(selected)
        return self.__selection_single(selected)

    def __selection_single(self, selected=None):
        if selected in dict(self.items).keys():
            self.on_value_change(selected)
            self._selected = selected
        return self._selected

    def __selection_multi(self, selected=None):
        if type(selected) in [list, str, unicode]:
            if type(selected) in [str, unicode]:
                # for convenience create a list for single strings
                selected = [selected]
            self.on_value_change(selected)
            self._selected = set([k for k in selected
                                  if k in dict(self.items).keys()])
        return list(self._selected)

    def value(self, value=None):
        return self.selection(value)


class Window(Element):
    """Abstract Window definition
    """

    application = None

    __hotkeys_enabled = True

    def __init__(self, path, application):
        super(Window, self).__init__(path=path)
        self.logger.info("Creating UI for application '%s'" % application)
        self.application = application

        self._plugins = {}
        self._hotkeys = {}

        self.footer = None

        self.navigate = Window.Navigation(self.application)

    def register_plugin(self, title, plugin):
        """Register a plugin to be shown in the UI
        """
        if title in self._plugins:
            raise RuntimeError("Plugin with same path is " +
                               "already registered: %s" % title)
        self._plugins[title] = plugin

    def hotkeys_enabled(self, new_value=None):
        """Disable all attached hotkey callbacks

        Args:
            new_value: If hotkeys shall be enabled or disabled

        Returns:
            If the hotkeys are enabled or disabled
        """
        if new_value in [True, False]:
            self.__hotkeys_enabled = new_value
        return self.__hotkeys_enabled

    def register_hotkey(self, hotkey, cb):
        """Register a hotkey

        Args:
            hotkeys: The key combination (very vague ...) triggering the
                     callback
             cb: The callback to be called
        """
        if type(hotkey) is str:
            hotkey = [hotkey]
        self.logger.debug("Registering hotkey '%s': %s" % (hotkey, cb))
        self._hotkeys[str(hotkey)] = cb

    def _show_on_page(self, page):
        """Shows the ui.Page as on a dialog.
        """
        raise NotImplementedError

    def _show_on_dialog(self, dialog):
        """Shows the ui.Dialog as on a dialog.
        """
        raise NotImplementedError

    def _show_on_notice(self, text):
        """Shows the text in the notice field
        Something liek a HUD display
        """
        raise NotImplementedError

    def close_dialog(self, dialog):
        """Close the ui.Dialog
        """
        raise NotImplementedError

    def suspended(self):
        """Supspends the screen to do something in the foreground
        Returns:
            ...
        """
        raise NotImplementedError

    def force_redraw(self):
        """Forces a complete redraw of the UI
        """
        raise NotImplementedError

    def reset(self):
        """Reset the UI
        """
        raise NotImplementedError

    def run(self):
        """Starts the UI
        """
        raise NotImplementedError

    def thread_connection(self):
        """Run a callback in the context of the UI thread

        Returns:
            A new UIThreadConnection instance
        """
        raise NotImplementedError

    class UIThreadConnection(base.Base):
        """A class to interact with the UI thread
        This is needed if other threads want to interact with the UI
        """

        def call(self, callback):
            """Call a callback in the context of the UI thread
            This needs to be used when updates to the ui are made

            Args:
                callback: A callable to be called in the ctx of the ui thread

            Returns:
                Nothing
            """
            raise NotImplementedError

    class Navigation(base.Base):
        """A convenience class to navigate through a window
        """

        application = None

        def __init__(self, application):
            self.application = application
            super(Window.Navigation, self).__init__()

        def index(self):
            plugins = self.application.plugins().items()
            get_rank = lambda path_plugin: path_plugin[1].rank()
            self.logger.debug("Available plugins: %s" % plugins)
            sorted_plugins = [p for n, p in sorted(plugins, key=get_rank)
                              if p.has_ui()]
            self.logger.debug("Available plugins with ui: %s" % sorted_plugins)
            return sorted_plugins

        def to_plugin(self, plugin_candidate):
            """Goes to the plugin (by instance or type)
            Args
                idx: The plugin instance/type to go to
            """
            self.logger.debug("Navigating to plugin %s" % plugin_candidate)
            self.application.switch_to_plugin(plugin_candidate)
            self.logger.debug("Navigated to plugin %s" % plugin_candidate)

        def to_nth(self, idx, is_relative=False):
            """Goes to the plugin (by idx)
            Any pending changes are ignored.

            Args
                idx: The plugin idx to go to
            """
            plugins = self.index()
            self.logger.debug("Switching to page %s (%s)" % (idx, plugins))
            if is_relative:
                idx += plugins.index(self.application.current_plugin())
            plugin = plugins[idx]
            self.to_plugin(plugin)

        def to_next_plugin(self):
            """Goes to the next plugin, based on the current one
            """
            self.to_nth(1, True)

        def to_previous_plugin(self):
            """Goes to the previous plugin, based on the current one
            """
            self.to_nth(-1, True)

        def to_first_plugin(self):
            """Goes to the first plugin
            """
            self.to_nth(0)

        def to_last_plugin(self):
            """Goes to the last plugin
            """
            self.to_nth(-1)


class Page(ContainerElement):
    """An abstract page with a couple of widgets
    """
    buttons = []

    def __init__(self, path, children, title=None):
        super(Page, self).__init__(path, children, title)
        self.buttons = self.buttons or [SaveButton("%s.save" % path,
                                                   _("Save")),
                                        ResetButton("%s.reset" % path,
                                                    _("Reset"))
                                        ]

    def elements(self):
        return super(Page, self).elements() + self.buttons


class Dialog(Page):
    """An abstract dialog, similar to a page

    Args:
        on_close: Emitted by the Dialog when it requests a close
    """

    escape_key = "esc"
    on_close_change = None

    def __init__(self, path, title, children):
        super(Dialog, self).__init__(path, children, title)
        self.buttons = [SaveButton("%s.save" % path, _("Save")),
                        CloseButton("%s.close" % path, _("Reset"))
                        ]
        self.on_close_change = self.new_signal()
        self.close(False)
        self.on_close_change.connect(CloseAction(dialog=self))

    def close(self, v=True):
        if v:
            self.on_close_change(self)


class InfoDialog(Dialog):
    """A dialog with a title and a text
    """
    def __init__(self, path, title, text, buttons=None):
        super(InfoDialog, self).__init__(path, title, [])
        self.children = [Label(path + ".label", text)]
        self.buttons = buttons or [CloseButton(path + ".close", _("Close"))]


class TextViewDialog(Dialog):
    """A dialog to display much text, e.g. log files
    """
    def __init__(self, path, title, contents, height=16):
        super(TextViewDialog, self).__init__(path, title, [])
        self.children = [Table("contents", "", _("Contents"),
                               contents, height=height)]
        self.buttons = [CloseButton("dialog.close", _("Close"))]


class ConfirmationDialog(InfoDialog):
    """A generic dialog showing a text and offering buttons
    By default a OK and Close button will be shown.
    """
    def __init__(self, path, title, text, buttons=None):
        self.children = [Divider("divider[0]"),
                         Label("label[0]", text)
                         ]
        if not buttons:
            # Default: OK and Close
            self.buttons = [Button(path + ".yes", _("OK")),
                            CloseButton(path + ".close", _("Cancel"))]
            buttons = self.buttons
        super(ConfirmationDialog, self).__init__(path, title, text,
                                                 buttons)


class TransactionProgressDialog(Dialog):
    """Display the progress of a transaction in a dialog
    """

    def __init__(self, path, transaction, plugin, initial_text=""):
        self.transaction = transaction
        title = _("Transaction: %s") % self.transaction.title
        self._progress_label = Label("dialog.progress", initial_text)
        super(TransactionProgressDialog, self).__init__(path,
                                                        title,
                                                        [self._progress_label])
        self.texts = [initial_text, ""]
        self.plugin = plugin

        self._close_button = CloseButton("button.close", _("Close"))
        self.buttons = [self._close_button]

    def add_update(self, txt):
        self.texts.append(txt)
        self._progress_label.text("\n".join(self.texts))

    def run(self):
        try:
            self.plugin.application.show(self)
            self._close_button.enabled(False)
            if self.transaction:
                self.logger.debug("Initiating transaction")
                self.__run_transaction()
            else:
                self.add_update("There were no changes, nothing to do.")
            self._close_button.enabled(True)

            # We enforce a redraw, because this the non-mainloop thread
            self.plugin.application.ui.force_redraw()
        except Exception as e:
            self.logger.warning("An exception in the Transaction: %s" % e,
                                exc_info=True)

    def __run_transaction(self):
        try:
            self.add_update("Checking pre-conditions ...")
            for idx, tx_element in self.transaction.step():
                txt = "(%s/%s) %s" % (idx + 1, len(self.transaction),
                                      tx_element.title)
                self.add_update(txt)
                with console.CaptureOutput() as captured:
                    # Sometimes a tx_element is wrapping some code that
                    # writes to stdout/stderr which scrambles the screen,
                    # therefore we are capturing this
                    self.plugin.dry_or(lambda: tx_element.commit())
            self.add_update("\nAll changes were applied successfully.")
        except Exception as e:
            self.logger.info("An exception during the transaction: %s" % e,
                             exc_info=True)
            self.add_update("\nAn error occurred while applying the changes:")
            self.add_update("%s" % e)

        if captured.stderr.getvalue():
            se = captured.stderr.getvalue()
            if se:
                self.add_update("Stderr: %s" % se)


class AbstractUIBuilder(base.Base):
    """An abstract class
    Every toolkit that wants to be a backend for the above elements needs to
    implement this builder. An instance of that specififc builder is then
    passed to the application which uses the builder to build the UI.
    """
    application = None

    def __init__(self, application):
        super(AbstractUIBuilder, self).__init__()
        self.application = application

    def build(self, ui_element):
        assert Element in type(ui_element).mro()

        builder_for_element = {
            ContainerElement: self._build_container,

            Window: self._build_window,
            Page: self._build_page,
            Dialog: self._build_dialog,

            Label: self._build_label,
            KeywordLabel: self._build_keywordlabel,

            Entry: self._build_entry,
            PasswordEntry: self._build_passwordentry,

            Header: self._build_header,
            Notice: self._build_notice,

            Button: self._build_button,

            Options: self._build_options,
            ProgressBar: self._build_progressbar,
            Table: self._build_table,
            Checkbox: self._build_checkbox,

            Divider: self._build_divider,
            Row: self._build_row,
        }

        self.logger.debug("Building %s" % ui_element)

        ui_element_type = type(ui_element)
        builder_func = None

        # Check if builder is available for UI Element
        if ui_element_type in builder_for_element:
            builder_func = builder_for_element[ui_element_type]
        else:
            # It could be a derived type, therefor find it's base:
            for sub_type in type(ui_element).mro():
                if sub_type in builder_for_element:
                    builder_func = builder_for_element[sub_type]

        if not builder_func:
            raise Exception("No builder for UI element '%s' (%s)" %
                            (ui_element, type(ui_element).mro()))

        # Build widget from UI Element
        widget = builder_func(ui_element)

        # Give the widget the ability to also use the ui_builder
        widget._ui_builder = self

        return widget

    def _build_container(self, ui_container):
        raise NotImplementedError

    def _build_window(self, ui_window):
        raise NotImplementedError

    def _build_page(self, ui_page):
        raise NotImplementedError

    def _build_dialog(self, ui_dialog):
        raise NotImplementedError

    def _build_label(self, ui_label):
        raise NotImplementedError

    def _build_keywordlabel(self, ui_keywordlabel):
        raise NotImplementedError

    def _build_header(self, ui_header):
        raise NotImplementedError

    def _build_notice(self, ui_notice):
        raise NotImplementedError

    def _build_button(self, ui_button):
        raise NotImplementedError

    def _build_button_bar(self, ui_button):
        raise NotImplementedError

    def _build_entry(self, ui_entry):
        raise NotImplementedError

    def _build_passwordentry(self, ui_passwordentry):
        raise NotImplementedError

    def _build_divider(self, ui_divider):
        raise NotImplementedError

    def _build_options(self, ui_options):
        raise NotImplementedError

    def _build_checkbox(self, ui_checkbox):
        raise NotImplementedError

    def _build_progressbar(self, ui_progressbar):
        raise NotImplementedError

    def _build_table(self, ui_table):
        raise NotImplementedError

    def _build_row(self, ui_row):
        raise NotImplementedError
