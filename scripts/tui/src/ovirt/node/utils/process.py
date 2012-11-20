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

"""
Some convenience functions related to processes
"""

import subprocess
import logging

LOGGER = logging.getLogger(__name__)


def popen(*args, **kwargs):
    """subprocess.Popen wrapper to not leak file descriptors

    Args:
        cmd: Cmdline to be run

    Returns:
        Popen object
    """
    kwargs.update({
        "close_fds": True
    })
    return subprocess.Popen(*args, **kwargs)


def system(cmd):
    """Run a non-interactive command, or where the user shall input something

    Args:
        cmd: Cmdline to be run

    Returns:
        retval of the process
    """
    return popen(cmd, shell=True).wait()


def pipe(cmd, stdin=None, without_retval=False):
    """Run a command interactively and cath it's output.
    This functions allows to pass smoe input to a running command.

    >>> r = pipe("echo -n Hi")
    >>> type(r[1])
    <type 'str'>

    >>> r
    (True, 'Hi')

    Args:
        cmd: Commandline to be run
        stdin: Optional string passed as stdin
        without_retval: Optional if no retval should be passed

    Returns:
        A tuple (success, stdout)
    """

    LOGGER.debug("run '%s'" % cmd)
    system_cmd = popen(cmd, shell=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    stdout, stderr = system_cmd.communicate(stdin)
    if stdout:
        LOGGER.debug("out '%s'" % stdout)
    if stderr:
        LOGGER.warning("error '%s'" % stderr)
    if without_retval:
        return stdout
    return (system_cmd.returncode == 0, stdout)


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
    LOGGER.debug("run async '%s'" % cmd)
    process = popen(cmd, shell=True, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, stdin=stdin)
    if stdin:
        process.stdin.write(stdin)
    while process.poll() != 0:
        yield process.stdout.readline()
