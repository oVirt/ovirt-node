#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# base.py - Copyright (C) 2012 Red Hat, Inc.
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
Base for all classes
"""

import logging


class Base(object):
    """Base class for all objects.
    With a logger and a simple signaling mechanism - see Gtk+
    """

    _signal_cbs = None

    @property
    def logger(self):
        """Logger."""
        return self._logger

    def __init__(self):
        """Contructor."""
        self._logger = logging.getLogger(self.__module__)

    @staticmethod
    def signal_change(func):
        """A decorator for methods which should emit signals
        """
        def wrapper(self, userdata=None, *args, **kwargs):
            signame = func.__name__
            self.register_signal(signame)
            self.emit_signal(signame, userdata)
            return func(self, userdata)
        return wrapper

    def register_signals(self, names):
        self.logger.debug("Registering signals: %s" % names)
        sigs = []
        for name in names:
            sigs.append(self.register_signal(name))
        return sigs

    def register_signal(self, name):
        """Each signal that get's emitted must be registered using this
        function.

        This is just to have an overview over the signals.
        """
        if self._signal_cbs is None:
            self._signal_cbs = {}
        if name not in self._signal_cbs:
            self._signal_cbs[name] = []
            self.logger.debug("Registered new signal '%s' for '%s'" % (name,
                                                                       self))
        return Base.Signal(self, name)

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
        self.logger.debug("Emitting '%s'" % name)
        for cb in self._signal_cbs[name]:
            self.logger.debug("... %s" % cb)
            cb(self, userdata)

    class Signal(object):
        """A convenience class for easier access to signals
        """
        def __init__(self, base, name):
            self.name = name
            self.base = base

        def emit(self, userdata=None):
            return self.base.emit_signal(self.name, userdata)

        def connect(self, cb):
            return self.base.connect_signal(self.name, cb)
