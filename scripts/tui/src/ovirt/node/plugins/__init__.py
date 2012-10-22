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
This contains much stuff related to plugins
"""
import pkgutil
import logging

import ovirt.node.plugins
import ovirt.node.exceptions

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

    def __init__(self, application):
        self.__changes = {}
        self.application = application

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
                    raise ovirt.node.exceptions.InvalidData(msg)
        return True

    def ui_name(self):
        """Returns the UI friendly name for this plugin.
        Is e.g. used for the menu entry.

        Returns:
            Title of the plugin as a string
        """
        return self.name()

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

    def on_change(self, changes):
        """Applies the changes to the plugins model, will do all required logic
        return True if succeeds, otherwie false or throw an error
        This is expected to do semanitcal checks on the model.

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
        except ovirt.node.exceptions.InvalidData:
            LOGGER.warning("Plugins model does not pass sematic check: %s" % \
                           model)
            is_valid = False
        finally:
            self.__changes = {}
        return is_valid

    def on_merge(self, effective_changes):
        """Handles the changes and throws an Exception if something goes wrong
        Needs to be implemented by any subclass

        Args:
            changes (dict): changes which shall be applied to the model
        Returns:
            True on success, or False otherwise
        Raises:
            Errors
        """
        raise NotImplementedError()

    def _on_ui_change(self, change):
        """Called when some widget was changed
        change is expected to be a dict.
        """
        if type(change) is not dict:
            LOGGER.warning("Change is not a dict: %s" % change)

        LOGGER.debug("Passing UI change to callback on_change: %s" % change)
        self.on_change(change)
        self.__changes.update(change)
        LOGGER.debug("Sum of all UI changes up to now: %s" % self.__changes)
        return True

    def _on_ui_save(self):
        """Called when data should be saved
        Calls merge_changes, but only with values that really changed
        """
        LOGGER.debug("Request to apply model changes")
        effective_changes = self.pending_changes() or {}
        successfull_merge = self.on_merge(effective_changes)
        if successfull_merge:
            self.__changes = {}
        return successfull_merge

    def pending_changes(self, only_effective_changes=True):
        """Return all changes which happened since the last on_merge call

        Args:
            only_effective_changes: Boolean if all or only the effective
                changes are returned.
        Returns:
            dict of changes
        """
        return self.__effective_changes() if only_effective_changes \
                                          else self.__changes

    def __effective_changes(self):
        """Calculates the effective changes, so changes which change the
        value of a path.

        Returns:
            dict of effective changes
        """
        effective_changes = {}
        if self.__changes:
            model = self.model()
            for key, value in self.__changes.items():
                if key in model and value == model[key]:
                    LOGGER.debug(("Skipping pseudo-change of '%s', value " + \
                                  "(%s) did not change") % (key, value))
                else:
                    effective_changes[key] = value
        else:
            LOGGER.debug("No effective changes detected.")
        return effective_changes if len(effective_changes) > 0 else None
