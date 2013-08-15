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

import log


class Base(object):
    """Base class for all objects.
    With a logger and a simple signaling mechanism - see Gtk+
    """

    @property
    def logger(self):
        """Logger."""
        return self._logger

    def __init__(self):
        """Contructor."""
        self._logger = log.getLogger(self.__module__)

    def _super(self):
        """Return the parent class of this obj
        """
        return super(self.__class__, self)

    def new_signal(self):
        return Base.Signal(self)

    def list_signals(self):
        return [(k, v) for k, v in self.__dict__.items()
                if issubclass(type(v), Base.Signal)]

    def build_str(self, attributes=[], additional_pairs={}, name=None):
        assert type(attributes) is list
        name = name or self.__class__.__name__
        attrs = dict((k, self.__dict__[k]) for k in attributes)
        attrs.update(additional_pairs)
        attrs = " ".join(["%s='%s'" % i for i in sorted(attrs.items())])
        addr = hex(id(self))
        return ("<%s>" % " ".join(v for v in [name, attrs, "at", addr] if v))

    class Signal(object):
        """A convenience class for easier access to signals
        """
        callbacks = None

        def __init__(self, target):
            self.target = target
            self.callbacks = []
            self.logger = log.getLogger(self.__module__)

        def emit(self, userdata=None):
            """Emit a signal
            """
            #self.logger.debug("%s: %s" % (self, self.callbacks))
            for idx, cb in enumerate(self.callbacks):
                self.logger.debug("%s (%d/%d) %s" %
                                  (self, idx + 1, len(self.callbacks), cb))
                if cb(self.target, userdata) is False:
                    self.logger.debug("Breaking callback sequence")
                    break
            return self

        def connect(self, cb):
            #self.logger.debug("Connecting %s with %s" % (self, cb))
            self.callbacks.append(cb)
            return self

        def clear(self):
            self.logger.debug("Clearing callbacks on %s" % self)
            self.callbacks = []

        def target_property(self):
            return dict((v, k) for k, v in self.target.list_signals())[self]

        def __call__(self, userdata=None):
            self.emit(userdata)

        def __str__(self):
            return "<%s %s target='%s' at %s>" % \
                (self.__class__.__name__, self.target_property(),
                 self.target, hex(id(self)))
