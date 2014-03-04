#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# plugins.py - Copyright (C) 2012 Red Hat, Inc.
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
from ovirt.node import base, exceptions, ui, log
from ovirt.node.exceptions import InvalidData

"""
This contains much stuff related to plugins
"""


logger = log.getLogger(__name__)


class NodePlugin(base.Base):
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

    only_merge_on_valid_changes = True

    on_valid = None

    def __init__(self, application):
        super(NodePlugin, self).__init__()
        self.application = application
        self.__changes = Changeset()
        self.__invalid_changes = Changeset()
        self.widgets = UIElements()

        self.on_valid = self.new_signal()

        self.application.register_plugin(self)

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

    def on_merge(self, effective_changes):
        """Handles the changes and throws an Exception if something goes wrong
        Needs to be implemented by any subclass

        Args:
            changes (dict): changes which shall be applied to the model
        Returns:
            (False)True on (no)success or a ui.Dialog/ui.Page
        Raises:
            Errors
        """
        raise NotImplementedError()

    def pending_changes(self, only_effective_changes=True,
                        include_invalid=False):
        """Return all changes which happened since the last on_merge call

        Args:
            only_effective_changes: Boolean if all or only the effective
                changes are returned.
            include_invalid: If the invalid changes should be included
        Returns:
            dict of changes
        """
        changes = self.__effective_changes() if only_effective_changes \
            else self.__changes
        if include_invalid:
            changes.update(self.__invalid_changes)
        return Changeset(changes)

    def is_only_valid_changes(self):
        """If all changes are valid or not

        Returns:
            If all changes happened so far are valid
        """
        return self.__invalid_changes.is_empty()

    def dry_or(self, func):
        """Do nothing (when we are running dry) or run func
        """
        if self.application.args.dry:
            self.logger.info("Running dry, otherwise: %s" % func)
        else:
            self.logger.info("Running %s" % func)
            return func()

    def check_semantics(self, model=None):
        """Simulate a complete model change.
        This runs all current model values throught the checks to see
        if the model validates.

        Returns:
            True if the model validates
        Raises:
            An exception on a problem
        """
        self.logger.debug("Triggering on_change of model")
        is_valid = True
        try:
            model = Changeset(model or self.model())
            self.on_change(model)
        except NotImplementedError:
            self.logger.debug("Plugin has no model")
        except exceptions.InvalidData:
            self.logger.warning("Plugins model does not pass semantic " +
                                "check: %s" % model)
            is_valid = False
        finally:
            self.__changes = Changeset()
        return is_valid

    def __validate(self, changes):
        """Test changes against the validators

        Args:
            changes: A dict of (path, value) to be checked

        Returns:
            True on a valid value or if there is no validator for a path
        Raises:
            InvalidData on any invalid data
        """
        validators = self.validators()
        widgets = self.widgets

        for change in changes.items():
            path, value = change

            problems = []

            # We assume that the change is invalid, as long as it
            # isn't validated
            self.__invalid_changes.update({path: value})

            self.logger.debug("Validation of path %s" % str(change))

            try:
                if path in validators:
                    problems.append(validators[path](value))
            except exceptions.InvalidData as e:
                msg = e.message or str(e)
                self.logger.debug("Validation failed on validator with: %s"
                                  % msg)
                problems.append(msg)

            try:
                if path in widgets:
                    problems.append(widgets[path]._validates())
            except exceptions.InvalidData as e:
                msg = e.message or str(e)
                self.logger.debug("Validation failed on widget with: %s"
                                  % msg)
                problems.append(msg)

            problems = [p for p in problems if p not in [True, None]]

            if problems:
                txt = "\n".join(problems)
                self.logger.debug("Validation failed with: %s" % problems)
                raise exceptions.InvalidData(txt)

            # If we reach this line, then it's valid data
            self.__invalid_changes.drop([path])

        validates = self.__invalid_changes.is_empty()
        self.logger.debug("Validates? %s (%s)" % (validates,
                                                  self.__invalid_changes))

        return validates

    def _on_ui_change(self, change):
        """Called when some widget was changed
        change is expected to be a dict.
        """
        if type(change) not in [dict, Changeset]:
            self.logger.warning("Change is not a dict: %s (%s)" %
                                (repr(change), type(change)))

        change = Changeset(change)

        self.logger.debug("Passing UI change to callback on_change: %s" %
                          change)

        msg = None
        self.__changes.drop(change.keys())

        try:
            # Run validators
            self.__validate(change)

            try:
                # Run custom validation
                self.on_change(change)

            except exceptions.InvalidData:
                # If caught here, it's from custom validation, and we
                # don't know for sure what failed, so flag everything
                self.__invalid_changes.update(dict((k, v) for (k, v) in
                                              change.iteritems()))
                raise

            self.__changes.update(change)

        except exceptions.InvalidData as e:
            msg = e.message

        except Exception as e:
            self.on_valid(False)
            self.application.show_exception(e)

        all_changes_are_valid = self.is_only_valid_changes()

        for path in change.keys():
            if path in self.widgets:
                self.logger.debug("Updating %s widgets validity: %s (%s)"
                                  % (path, all_changes_are_valid, msg))
                self.widgets[path].valid(all_changes_are_valid)
                try:
                    self.widgets[path].notice(msg)
                except NotImplementedError:
                    self.logger.debug("Widget doesn't support notices.")
                    notice = ("The following requirements need to " +
                              "be met: \n%s" % msg)
                    self.application.show_exception(InvalidData(notice))
            else:
                self.logger.warning("No widget for path %s" % path)

        self.logger.debug("All valid changes: %s" %
                          self.__changes)
        self.logger.debug("All invalid changes: %s" %
                          self.__invalid_changes)

        self.on_valid(all_changes_are_valid)

        return all_changes_are_valid

    def _on_ui_save(self):
        """Called when data should be saved
        Calls merge_changes, but only with values that really changed
        """
        effective_changes = self.pending_changes()
        is_valid = False

        self.logger.debug("Request to apply model changes: %s" %
                          effective_changes)

        try:
            is_valid = self._on_ui_change(effective_changes)
        except exceptions.InvalidData as e:
            self.logger.info("Changes to be merged are invalid: %s" %
                             e.message)

        if self.only_merge_on_valid_changes and not is_valid:
            msg = "There are still fields with invalid values."
            self.logger.warning(msg)
            raise exceptions.PreconditionError(msg)

        successfull_merge = self.on_merge(effective_changes)

        if successfull_merge is None:
            self.logger.debug("on_save needs to return True/False or a " +
                              "Page/Dialog")
            successfull_merge = True

        if successfull_merge:
            self.logger.info("Changes were merged successfully")
            self.__changes = Changeset()
        else:
            self.logger.info("Changes were not merged.")

        return self.__handle_merge_result(successfull_merge)

    def __handle_merge_result(self, result):
        """Checks if a page/dialog was returned and displays it accordingly
        """
        self.logger.debug("Parsing plugin merge result: %s" % result)
        app = self.application

        if ui.Dialog in type(result).mro():
            app.show(result)

        elif ui.Page in type(result).mro():
            app.show(result)

        return result

    def _on_ui_reset(self):
        """Called when a ResetButton was clicked
        Discards all changes
        """
        changes = self.pending_changes(False)
        self.logger.debug("Request to discard model changes: %s" % changes)
        self.__changes = {}

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
                    self.logger.debug(("Skipping pseudo-change of '%s', " +
                                       "value (%s) did not change") % (key,
                                                                       value))
                else:
                    effective_changes[key] = value
        else:
            self.logger.debug("No changes at all detected.")
        if not effective_changes:
            self.logger.debug("No effective changes detected.")
        return effective_changes


class Changeset(dict, base.Base):
    """A wrapper around a dict to provide some convenience functions
    """
    def __init__(self, changes=None):
        super(Changeset, self).__init__()
        base.Base.__init__(self)
        if changes:
            self.update(changes)

    def values_for(self, keys):
        assert self.contains_all(keys), "Missing keys: %s" % \
            set(keys).difference(set(self.keys()))
        return [self[key] for key in keys]

    def contains_all(self, keys):
        return set(keys).issubset(set(self.keys()))

    def contains_any(self, keys):
        return any([key in self for key in keys])

    def __getitem__(self, key):
        """Diferent to a dict: We return none if a key does not exist
        """
        return dict.get(self, key, None)

    def reset(self, changes):
        self.clear()
        self.update(changes)

    def drop(self, keys):
        for key in keys:
            del self[key]

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        if key in self:
            dict.__delitem__(self, key)

    def is_empty(self):
        """If there are any keys set

        >>> c = Changeset()
        >>> c.is_empty()
        True
        >>> c.update({"a": 1})
        >>> c.is_empty()
        False
        >>> c.drop(["a"])
        >>> c.is_empty()
        True
        """
        return len(self) == 0

    def update(self, changes):
        dict.update(self, changes)


class UIElements(base.Base):
    """A helper class to handle widgets
    """
    _elements = None

    def __init__(self, widgets=[]):
        super(UIElements, self).__init__()
        self._elements = {}
        self.add(widgets)

    def subset(self, paths):
        return [self[p] for p in paths if p in self]

    def group(self, paths):
        """Group the specified (by-path) widgets

        Args:
            paths: A list of paths of widgets to be grouped
        Returns:
            A UIElements.Group
        """
        return UIElements.Group(self, paths)

    def add(self, elements):
        """Add one or many elements to this helper
        """
        elements = elements if type(elements) is list else [elements]

        for element in elements:
            self._elements[element.path] = element
            if ui.ContainerElement in type(element).mro():
                self.logger.debug("Is a container adding children")
                self.add(element.children)

    def __getitem__(self, path):
        return self._elements[path]

    def __contains__(self, element):
        key = element if type(element) in [str, unicode] else element.path
        return key in self._elements

    def __iter__(self):
        for e in self._elements:
            yield e

    def __str__(self):
        return "<UIElements %s>" % self._elements

    class Group(list, base.Base):
        def __init__(self, uielements, paths):
            super(UIElements.Group, self).__init__()
            base.Base.__init__(self)
            self.uielements = uielements
            self.extend(paths)

        def enabled(self, is_enable):
            """Enable or disable all widgets of this group
            """
            self.logger.debug("Enabling widget group: %s" % self)
            map(lambda w: w.enabled(is_enable), self.elements())

        def text(self, text):
            """Enable or disable all widgets of this group
            """
            self.logger.debug("Setting text of widget group: %s" % self)
            map(lambda w: w.value(text), self.elements())

        def elements(self):
            """Return the UI elements of this group
            """
            return self.uielements.subset(self)
