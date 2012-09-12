
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
        raise Exception("Not yet implemented.")

    def model(self):
        """Returns the model of the plugin.
        A model is just a dict (key-PatternObj) where each path (key) maps to a
        value which is modified by changes in the UI.

        Returns:
            The model (dict) of the plugin
        """
        raise Exception("Not yet implemented.")

    def validators(self):
        """Returns a dict of validators.
        The dict, mapping a (model) path to a validator is used to validate
        new model values (a change).
        It can but does not need to contain an entry for the paths in the
        model.

        Returns:
            A dict of validators
        """

    def has_ui(self):
        """Determins if a page for this should be displayed in the UI

        Returns:
            True if a page shall be displayed, False otherwise
        """
        return True

    def ui_content(self):
        """Describes the UI this plugin requires
        This is an ordered list of (path, widget) tuples.
        """
        raise Exception("Not yet implemented.")

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
        raise Exception("Not yet implemented.")

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
        raise Exception("Not yet implemented.")

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

    def _on_ui_save(self):
        """Called when data should be saved
        Calls merge_changes, but only with values that really changed
        """
        LOGGER.debug("Request to apply model changes")
        if self._changes:
            real_changes = {}
            for key, value in self._changes.items():
                if value == self.model()[key]:
                    LOGGER.debug(("Skipping pseudo-change of '%s', value " + \
                                  "did not change") % key)
                else:
                    real_changes[key] = value
            return self.on_merge(real_changes)
        else:
            LOGGER.debug("No changes detected")
        return True


class Widget(object):
    _enabled = True
    _signals = None

    def enabled(self, is_enabled=None):
        if is_enabled in [True, False]:
            self.emit_signal("enabled[change]", is_enabled)
            self._enabled = is_enabled
        return self._enabled

    def connect_signal(self, name, cb):
        if self._signals is None:
            self._signals = {}
        if name not in self._signals:
            self._signals[name] = []
        self._signals[name].append(cb)

    def emit_signal(self, name, userdata=None):
        if self._signals is None or \
           name not in self._signals:
            return False
        for cb in self._signals[name]:
            LOGGER.debug("CB for sig %s: %s" % (name, cb))
            cb(self, userdata)


class Label(Widget):
    """Represents a r/o label
    """
    def __init__(self, label):
        self.label = label


class Header(Label):
    pass


class Entry(Widget):
    """Represents an entry field
    TODO multiline
    """
    def __init__(self, label, value=None, initial_value_from_model=True,
                 enabled=True):
        self.label = label
        self.value = value
        self.initial_value_from_model = initial_value_from_model
        self._enabled = enabled


class Password(Entry):
    pass


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
