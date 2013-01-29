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

    @property
    def logger(self):
        """Logger."""
        return self._logger

    def __init__(self):
        """Contructor."""
        self._logger = logging.getLogger(self.__module__)

    def _super(self):
        """Return the parent class of this obj
        """
        return super(self.__class__, self)

    def new_signal(self):
        return Base.Signal(self)

    def list_signals(self):
        return [(k, v) for k, v in self.__dict__.items()
                if isinstance(v, Base.Signal)]

    class Signal(object):
        """A convenience class for easier access to signals
        """
        callbacks = None

        def __init__(self, target):
            self.target = target
            self.callbacks = []
            self.logger = logging.getLogger(self.__module__)

        def emit(self, userdata=None):
            """Emit a signal
            """
            target = self.target
            for idx, cb in enumerate(self.callbacks):
                self.logger.debug("(%d/%d) Emitting from %s: %s" %
                                  (idx + 1, len(self.callbacks), self, cb))
                cb(target, userdata)
            return self

        def connect(self, cb):
            self.logger.debug("Connecting %s with %s" % (self, cb))
            self.callbacks.append(cb)
            return self

        def clear(self):
            self.logger.debug("Clearing callbacks on %s" % self)
            self.callbacks = []

        def target_property(self):
            return dict(self.target.list_signals())[self][0]

        def __call__(self, userdata=None):
            self.emit(userdata)

        def __str__(self):
            return "<%s target='%s' at %s>" % \
                (self.__class__.__name__, self.target, hex(id(self)))
