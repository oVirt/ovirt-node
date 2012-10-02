"""
This contains much stuff related to plugins
"""
import pkgutil
import logging

import ovirt.node.plugins

LOGGER = logging.getLogger(__name__)


def __walk_plugins():
    """Used to find all plugins
    """
    package = ovirt.node.plugins
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        yield (importer, modname, ispkg)


def load_all():
    """Load all plugins
    """
    modules = []
    for importer, modname, ispkg in __walk_plugins():
        #print("Found submodule %s (is a package: %s)" % (modname, ispkg))
        module = __import__("ovirt.node.plugins." + modname, fromlist="dummy")
        #print("Imported", module)
        modules += [module]
    return modules


class NodePlugin(object):
    """
    Basically a plugin provides a model which is changed by the UI (using the
    model() method)
    When the user "saves", the changes are provided to the plugin which can
    then decide what to do with the changes.

    Flow:

    1. [Start UI]
    2. [Change UI] triggers check_changes(), exception leads to UI dialog
    3. [Save UI]   triggers save_changes(),  exception leads to UI dialog


    Errors are propagated back by using Errors/Exceptions.
    """

    _changes = None

    def __init__(self):
        self._changes = {}

    def name(self):
        """Returns the name of the plugin.
        This is used as the entry for the navigation list.

        Returns:
            The name of the plugin
        """
        raise NotImplementedError()

    def rank(self):
        """Is used to add a order in-between plugins 0<n<100
        """
        return 50

    def model(self):
        """Returns the model of the plugin.
        A model is just a dict (key-PatternObj) where each path (key) maps to a
        value which is modified by changes in the UI.

        Returns:
            The model (dict) of the plugin
        """
        raise NotImplementedError()

    def validators(self):
        """Returns a dict of validators.
        The dict, mapping a (model) path to a validator is used to validate
        new model values (a change).
        It can but does not need to contain an entry for the paths in the
        model.

        Returns:
            A dict of validators
        """
        raise NotImplementedError()

    def validate(self, changes):
        """Test changes against the validators

        Args:
            changes: A dict of (path, value) to be checked

        Returns:
            True on a valid value or if there is no validator for a path
        Raises:
            InvalidData on any invalid data
        """
        for path, value in changes.items():
            if path in self.validators():
                msg = self.validators()[path](value)
                # True and None are allowed values
                if msg not in [True, None]:
                    raise ovirt.node.plugins.InvalidData(msg)
        return True

    def has_ui(self):
        """Determins if a page for this should be displayed in the UI

        Returns:
            True if a page shall be displayed, False otherwise
        """
        return True

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples or a tuple with the
        previous specified list of items and a second element with a dict
        serving additional ui configs.

        Returns:
            List of (path, widget)
        """
        raise NotImplementedError()

    def ui_config(self):
        """Specifies additional details for the UI
        E.g. if some defaults should be omitted (default save button).

        save_button: If the save button shall be displayed (True)

        Returns:
            A dict of config items and their values.
        """
        return {}

    def on_change(self, changes):
        """Applies the changes to the plugins model, will do all required logic
        return True if succeeds, otherwie false or throw an error

        Args:
            changes (dict): changes which shall be checked against the model
        Returns:
            True on success, or False otherwie
        Raises:
            Errors
        """
        raise NotImplementedError()

    def check_semantics(self, model=None):
        """Simulate a complete model change.
        This runs all current model values throught the checks to see
        if the model validates.

        Returns:
            True if the model validates
        Raises:
            An exception on a problem
        """
        LOGGER.debug("Triggering revalidation of model")
        is_valid = True
        try:
            model = model or self.model()
            self.on_change(model)
        except NotImplementedError:
            LOGGER.debug("Plugin has no model")
        except InvalidData:
            LOGGER.warning("Plugin has invalid model")
            is_valid = False
        return is_valid

    def on_merge(self, effective_changes):
        """Handles the changes and throws an Exception if something goes wrong
        Needs to be implemented by any subclass

        Args:
            changes (dict): changes which shall be applied to the model
        Returns:
            True on success, or False otherwie
        Raises:
            Errors
        """
        raise NotImplementedError()

    def ui_name(self):
        return self.name()

    def _on_ui_change(self, change):
        """Called when some widget was changed
        change is expected to be a dict.
        """
        assert type(change) is dict
        LOGGER.debug("Model change: " + str(change))
        self.on_change(change)
        self._changes.update(change)
        LOGGER.debug(self._changes)
        return True

    def _on_ui_save(self):
        """Called when data should be saved
        Calls merge_changes, but only with values that really changed
        """
        LOGGER.debug("Request to apply model changes")
        real_changes = {}
        if self._changes:
            for key, value in self._changes.items():
                if value == self.model()[key]:
                    LOGGER.debug(("Skipping pseudo-change of '%s', value " + \
                                  "did not change") % key)
                else:
                    real_changes[key] = value
        else:
            LOGGER.debug("No changes detected")
        return self.on_merge(real_changes)


# http://stackoverflow.com/questions/739654/understanding-python-decorators
class Widget(object):
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
        for cb in self._signal_cbs[name]:
            LOGGER.debug("CB for sig %s: %s" % (name, cb))
            cb(self, userdata)

    def set_text(self, value):
        """A general way to set the "text" of a widget
        """
        raise NotImplementedError


class InputWidget(Widget):
    """
    """

    def __init__(self, is_enabled):
        self.enabled(is_enabled)
        super(InputWidget, self).__init__()

    @Widget.signal_change
    def enabled(self, is_enabled=None):
        if is_enabled in [True, False]:
            self._enabled = is_enabled
        return self._enabled

    @Widget.signal_change
    def text(self, text=None):
        if text != None:
            self._text = text
        return self._text

    def set_text(self, txt):
        self.text(txt)


class Label(Widget):
    """Represents a r/o label
    """

    def __init__(self, text):
        self.text(text)
        super(Label, self).__init__()

    @Widget.signal_change
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


class Entry(InputWidget):
    """Represents an entry field
    TODO multiline
    """

    def __init__(self, label, value=None, enabled=True):
        self.label = label
        self._text = value
        super(Entry, self).__init__(enabled)


class PasswordEntry(Entry):
    pass


class Button(Label):
    def __init__(self, label, enabled=True):
        Label.__init__(self, label)
#        InputWidget.__init__(self, enabled)


class SaveButton(Button):
    def __init__(self, enabled=True):
        super(SaveButton, self).__init__(self, "Save", enabled)


class Divider(Widget):
    def __init__(self, char=u" "):
        self.char = char


class Options(Widget):

    def __init__(self, label, options):
        self.label = label
        self.options = options
        self.option(options[0])
        super(Options, self).__init__()

    @Widget.signal_change
    def option(self, option=None):
        if option in self.options:
            self._option = option
        return self._option

    def set_text(self, txt):
        self.option(txt)


class InvalidData(Exception):
    """E.g. if a string contains characters which are not allowed
    """
    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self.message)


class Concern(InvalidData):
    """E.g. if a password is not secure enough
    """
    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self.message)


class ContentRefreshRequest(Exception):
    pass
