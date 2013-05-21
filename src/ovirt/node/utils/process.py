#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# process.py - Copyright (C) 2012 Red Hat, Inc.
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
from subprocess import STDOUT, PIPE
import logging
import subprocess
import sys

"""
Some convenience functions related to processes
"""


LOGGER = logging.getLogger(__name__)

COMMON_POPEN_ARGS = {
    "close_fds": True,
    "shell": True
}

CalledProcessError = subprocess.CalledProcessError


def popen(*args, **kwargs):
    """subprocess.Popen wrapper to not leak file descriptors
    """
    kwargs.update(COMMON_POPEN_ARGS)
    LOGGER.debug("Popen with: %s %s" % (args, kwargs))
    return subprocess.Popen(*args, **kwargs)


def call(*args, **kwargs):
    """subprocess.call wrapper to not leak file descriptors
    """
    kwargs.update(COMMON_POPEN_ARGS)
    LOGGER.debug("Calling with: %s %s" % (args, kwargs))
    return int(subprocess.call(*args, **kwargs))


def check_call(*args, **kwargs):
    """subprocess.check_call wrapper to not leak file descriptors
    """
    kwargs.update(COMMON_POPEN_ARGS)
    LOGGER.debug("Checking call with: %s %s" % (args, kwargs))
    return int(subprocess.check_call(*args, **kwargs))


def check_output(*args, **kwargs):
    """subprocess.check_output wrapper to not leak file descriptors
    """
    kwargs.update(COMMON_POPEN_ARGS)
    LOGGER.debug("Checking output with: %s %s" % (args, kwargs))
    return unicode(subprocess.check_output(*args, **kwargs),
                   encoding=sys.stdin.encoding)


def pipe(cmd, stdin=None):
    """Run a non-interactive command and return it's output

    Args:
        cmd: Cmdline to be run
        stdin: (optional) Data passed to stdin

    Returns:
        stdout, stderr of the process (as one blob)
    """
    return unicode(popen(cmd, shell=True,
                         stdin=PIPE,
                         stdout=PIPE,
                         stderr=STDOUT).communicate(stdin)[0])


def pipe_async(cmd, stdin=None):
    """Run a command interactively and yields the process output.
    This functions allows to pass smoe input to a running command.

    Args:
        cmd: Commandline to be run
        stdin: Data to be written to cmd's stdin

    Yields:
        Lines read from stdout
    """
    # https://github.com/wardi/urwid/blob/master/examples/subproc.py
    LOGGER.debug("Piping async '%s'" % cmd)
    process = popen(cmd, shell=True, stdout=PIPE,
                    stderr=PIPE, stdin=stdin)
    # pylint: disable-msg=E1101
    if stdin:
        process.stdin.write(stdin)
    while process.poll() != 0:
        yield process.stdout.readline()
    # pylint: enable-msg=E1101
