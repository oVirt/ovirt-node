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
from ovirt.node import base, exceptions
import augeas as _augeas
import lockfile
import time
import traceback

"""
Utility functions.
It is aimed that the modules in trhis package display live informations and not
informations based on static config files.
Use the .config package for stuff related to configuration files.
And use the model.py module for oVirt Node's defaults file.
"""


class AugeasWrapper(base.Base):
    _aug = _augeas.Augeas()

    def __init__(self):
        super(AugeasWrapper, self).__init__()
#        self._aug = _augeas.Augeas() # Is broken
        self._aug.set("/augeas/save/copy_if_rename_fails", "")

    @staticmethod
    def force_reload():
        """Needs to be called when files were changed on-disk without using Aug
        """
        AugeasWrapper._aug.load()

    def get(self, p, strip_quotes=False):
        v = self._aug.get(p)
        # v can be many types str, bool, ...
        if type(v) in [str, unicode] and strip_quotes:
            v = unicode(v).strip("'\"")
        return v

    def set(self, p, v, do_save=True):
        self._aug.set(p, v)
        if do_save:
            self.save()

    def remove(self, p, do_save=True):
        self._aug.remove(p)
        if do_save:
            self.save()

    def save(self):
        return self._aug.save()

    def match(self, p):
        return self._aug.match(p)

    def load(self):
        return self._aug.load()

    def set_many(self, new_dict, basepath=""):
        """Set's many augpaths at once

        Args:
            new_dict: A dict with a mapping (path, value)
            basepath: An optional prefix for each path of new_dict
        """
        for key, value in new_dict.items():
            path = basepath + key
            self.set(path, value)
        return self.save()

    def remove_many(self, paths, basepath=None):
        """Removes many keys at once

        Args:
            paths: The paths to be removed
            basepath: An optional prefix for each path of new_dict
        """
        for key in paths:
            path = basepath + key
            self.remove(path, False)
        return self.save()

    def get_many(self, paths, strip_basepath=""):
        """Get all values for all the paths

        Args:
            paths: Paths from which to fetch the values
            strip_basepath: Prefix to be stripped from all paths
        """
        values = {}
        for path in paths:
            if strip_basepath:
                path = path[len(strip_basepath):]
            values[path] = self.get(path)
        return values


def parse_bool(txt):
    """Parse common "bool" values (yes, no, true, false, 1)

    >>> parse_bool(True)
    True

    >>> txts = ["yes", "YES!", "1", 1, "y"]
    >>> all((parse_bool(txt) for txt in txts))
    True

    >>> txts = ["no", "NO!", "0", 0, False, None, "foo", "n"]
    >>> all((not parse_bool(txt) for txt in txts))
    True

    Args:
        txt: Text to be parsed
    Returns:
        True if it looks like a bool representing True, False otherwise
    """
    if txt is not None and type(txt) in [str, unicode, int, bool]:
        utxt = unicode(txt)
        if len(utxt) > 0 and utxt[0] in ["y", "t", "Y", "T", "1"]:
            return True
    return False


class Transaction(list, base.Base):
    """A very simple transaction mechanism.

    >>> class StepA(Transaction.Element):
    ...     def commit(self):
    ...         print "Step A"
    ...         return "Stepped A"

    >>> class StepB(Transaction.Element):
    ...     def commit(self):
    ...         print "Step B"
    ...         return "Stepped B"

    >>> class StepC(Transaction.Element):
    ...     def commit(self):
    ...         raise Exception("Step C")

    >>> tx = Transaction("Steps", [StepA(), StepB()])
    >>> tx()
    Step A
    Step B
    True

    >>> len(tx)
    2

    >>> tx.prepare()
    True
    >>> for e in tx:
    ...     e.commit()
    Step A
    'Stepped A'
    Step B
    'Stepped B'

    >>> tx = Transaction("Steps", [StepA(), StepB(), StepC()])
    >>> tx()
    Traceback (most recent call last):
        ...
    TransactionError: 'Transaction failed: Step C'

    >>> txs = [
    ...     Transaction("Step A", [StepA()]),
    ...     Transaction("Step B", [StepB()])
    ... ]
    >>> txs
    [[<StepA 'None'>], [<StepB 'None'>]]
    """
    title = None
    _lockfilename = "/tmp/transaction-in-progress"
    _prepared_elements = None

    def __init__(self, title, elements=[]):
        super(Transaction, self).__init__()
        base.Base.__init__(self)
        self.title = title
        self._prepared_elements = []
        self.extend(elements)

    def prepare(self):
        self._prepared_elements = []
        for element in self:
            self.logger.debug("Preparing element '%s'" % element)
            if Transaction.Element not in element.__class__.mro():
                raise exceptions.PreconditionError(("%s is no Transaction." +
                                                    "Element") % element)
            self._prepared_elements.append(element)
            element.prepare()
        return True

    def commit(self):
        for element in self:
            self.logger.debug("Committing element '%s'" % element)
            element.commit()
        return True

    def abort(self):
        for element in self._prepared_elements:
            self.logger.debug("Aborting element '%s'" % element)
            element.abort()
        self._prepared_elements = []
        return True

    def run(self):
        self.logger.debug("Running transaction '%s'" % self)
        try:
            with lockfile.FileLock(self._lockfilename):
                self.prepare()
                self.commit()
        except Exception as e:
            self.logger.exception("Transaction failed (%s): %s" % (e,
                                                                   e.message))
            self.abort()
            raise exceptions.TransactionError("Transaction failed: " +
                                              "%s" % e.message)
        self.logger.info("Transaction '%s' succeeded" % self)
        return True

    def __call__(self):
        return self.run()

    def __str__(self):
        return self.build_str(["title"], {"elements": list.__str__(self)})

    def step(self):
        try:
            with lockfile.FileLock(self._lockfilename):
                self.logger.debug("Preparing transaction %s" % self)
                self.prepare()
                for idx, e in enumerate(self):
                    yield (idx, e)
        except Exception as e:
            self.logger.warning("'%s' on transaction '%s': %s - %s" %
                                (type(e), self, e, e.message))
            self.logger.debug(str(traceback.format_exc()))
            raise
        self.logger.debug("Finished transaction %s successfully" % self)

    class Element(base.Base):
        title = None

        def prepare(self):
            """Is expected to be short running and not changing anything
            """
            pass

        def commit(self):
            """Is expected to run and change stuff
            """
            pass

        def abort(self):
            """Is run in case that one commit of a transaction fails.
            """
            pass

        def __repr__(self):
            return "<%s '%s'>" % (self.__class__.__name__, self.title)

        def __call__(self):
            self.prepare()
            self.commit()


class Timer(base.Base):
    started = 0
    ended = 0

    def __enter__(self):
        """Create backups when starting
        """
        self.started = time.time()
        self.logger.debug("Starting timer at %s" % self.started)
        return self

    def __exit__(self, a, b, c):
        """Remove all backups when done
        """
        self.stopped = time.time()

    def duration(self):
        return self.stopped - self.started

    def __str__(self):
        return "<Timer duration='%s'>" % self.duration()
