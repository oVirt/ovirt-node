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

    def validate(self, path, value):
        """Validates a value against the validator of a given path

        Args:
            path: A model path for a validator
            value: The value to be validated

        Returns:
            True on a valid value or if there is no validator for a path

        Raises:
            InvalidData on any invalid data
        """
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

    def validate_model(self):
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
            for path, value in self.model().items():
                self.on_change({path: value})
        except NotImplementedError:
            LOGGER.debug("Plugin has no model")
        except InvalidData:
            LOGGER.warning("Plugin has invalid model")
            is_valid = False
        return is_valid

    def on_merge(self, changes):
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


class Widget(object):
    _signal_cbs = None
    signals = []
    signaling_properties = []

    def __init__(self):
        """Registers all widget signals.
        All signals must be given in self.signals
        """
        for name in self.signals:
            self._register_signal(name)
        for name in self.signaling_properties:
            self._register_signaling_property(name)

    def _register_signal(self, name):
        """Each signal that get's emitted must be registered using this
        function.

        This is just to have an overview over the signals.
        """
        if self._signal_cbs is None:
            self._signal_cbs = {}
        if name not in self._signal_cbs:
            self._signal_cbs[name] = []
#            LOGGER.debug("Registered new signal '%s' for '%s'" % (name, self))

    def connect_signal(self, name, cb):
        """Connect an callback to a signal
        """
        assert name in self._signal_cbs, "Unregistered signal '%s'" % name
        self._signal_cbs[name].append(cb)

    def emit_signal(self, name, userdata=None):
        """Emit a signal
        """
        if self._signal_cbs is None or name not in self._signal_cbs:
            return False
        for cb in self._signal_cbs[name]:
            LOGGER.debug("CB for sig %s: %s" % (name, cb))
            cb(self, userdata)

    def _register_signaling_property(self, name):
        LOGGER.debug("Registered new property '%s' for '%s'" % (name, self))
        if "_%s" % name not in self.__dict__:
            self.__dict__["_%s" % name] = None
        self._register_signal("%s[change]" % name)

    def _signaling_property(self, name, valid_value_cb, new_value):
        if valid_value_cb():
            self.emit_signal("%s[change]" % name, new_value)
            self.__dict__["_%s" % name] = new_value
        return self.__dict__["_%s" % name]


class InputWidget(Widget):
    signaling_properties = ["enabled"]

    def enabled(self, is_enabled=None):
        return self._signaling_property("enabled", \
                                        lambda: is_enabled in [True, False],
                                        is_enabled)


class Label(Widget):
    """Represents a r/o label
    """
    signaling_properties = ["text"]

    def __init__(self, text):
        self._text = text
        super(Label, self).__init__()

    def text(self, value=None):
        return self._signaling_property("text", \
                                        lambda: value != None,
                                        value)


class Header(Label):
    pass


class Entry(InputWidget):
    """Represents an entry field
    TODO multiline
    """

    def __init__(self, label, value=None, initial_value_from_model=True,
                 enabled=True):
        self.label = label
        self.value = value
        self.initial_value_from_model = initial_value_from_model
        self._enabled = enabled
        super(Entry, self).__init__()


class PasswordEntry(Entry):
    pass


class Button(Label, InputWidget):
    def __init__(self, label="Save", enabled=True):
        self._enabled = enabled
        super(Button, self).__init__(label)


class SaveButton(Button):
    pass


class Divider(Widget):
    def __init__(self, char=u" "):
        self.char = char


class Options(Widget):
    signals = ["change"]
    signaling_properties = ["option"]

    def __init__(self, label, options):
        self.label = label
        self.options = options
        super(Options, self).__init__()

    def option(self, option=None):
        return self._signaling_property("option", \
                                        lambda: option in self.options,
                                        option)


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
