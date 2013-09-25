#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# log.py - Copyright (C) 2013 Red Hat, Inc.
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
from StringIO import StringIO
import logging  # @UnusedImport
import logging.config
import os.path

"""
Representing the whole application (not just the TUI).
Basically the application consists of two parts: Page-Plugins and the UI
which communicate with each other.
"""

RUNTIME_LOG_CONF_FILENAME = "/etc/ovirt-node/logging.conf"
RUNTIME_DEBUG_LOG_CONF_FILENAME = "/etc/ovirt-node/logging.debug.conf"


def configure_logging(is_debug=False):
    mixedfile = RUNTIME_LOG_CONF_FILENAME
    if is_debug:
        mixedfile = RUNTIME_DEBUG_LOG_CONF_FILENAME
    if not os.path.exists(mixedfile):
        mixedfile = StringIO("""
[loggers]
keys=root

[handlers]
keys=debug,error

[formatters]
keys=verbose

[logger_root]
level=NOTSET
handlers=debug,error

[handler_error]
class=StreamHandler
level=ERROR
args=()

[handler_debug]
class=FileHandler
level=DEBUG
formatter=verbose
args=('/tmp/ovirt-node.debug.log', 'w')

[formatter_verbose]
format=%(levelname)10s %(asctime)s %(pathname)s:%(lineno)s:%(funcName)s: \
%(message)s
        """)
    logging.debug("Setting log config to: %s" % mixedfile)
    logging.config.fileConfig(mixedfile)


def getLogger(name=None):
    if not getLogger._logger:
        if not logging.getLogger().handlers:
            configure_logging()
        getLogger._logger = logging.getLogger()
    fullname = ".".join([getLogger._logger.name, name]) if name else name
    return logging.getLogger(fullname)
getLogger._logger = None
