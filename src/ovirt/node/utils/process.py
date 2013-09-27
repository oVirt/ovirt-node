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
from ovirt.node import log
import subprocess
import sys

"""
Some convenience functions related to processes
"""


LOGGER = log.getLogger(__name__)

COMMON_POPEN_ARGS = {
    "close_fds": True
}

CalledProcessError = subprocess.CalledProcessError


def __update_kwargs(kwargs):
    new_kwargs = dict(COMMON_POPEN_ARGS)
    new_kwargs.update(kwargs)
    return new_kwargs


def __check_for_problems(args, kwargs):
    """This checks for one well known problem.

    If a string is used as the cmd, then shell=True needs to be passed
    >>> __check_for_problems(["true"], {"shell": True})

    When the cmd is a list, then shell must be False (which it is by default)
    >>> __check_for_problems([["true"]], {"shell": False})
    >>> __check_for_problems([["true"]], {})

    If a list is used as the cmd, then shell is not allowed.
    >>> __check_for_problems([["true"]],
    ... {"shell": True}) #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ...
    RuntimeError:
    """
    if ("shell" in kwargs and kwargs["shell"] is True) and \
            (args and type(args[0]) is list):
        raise RuntimeError("Combining shell=True and a command list does " +
                           "not work. With shell=True the first argument" +
                           "must be a string. A list otherwise.")


def popen(*args, **kwargs):
    """subprocess.Popen wrapper to not leak file descriptors
    """
    kwargs = __update_kwargs(kwargs)
    LOGGER.debug("Popen with: %s %s" % (args, kwargs))
    # Intentionally no check for common problems
    return subprocess.Popen(*args, **kwargs)


def call(*args, **kwargs):
    """subprocess.call wrapper to not leak file descriptors

    >>> call(["true"])
    0
    >>> call(["false"])
    1
    >>> call(["echo", "42"], stdout=PIPE)
    0
    >>> call("echo 42", shell=True, stdout=PIPE)
    0
    """
    kwargs = __update_kwargs(kwargs)
    LOGGER.debug("Calling with: %s %s" % (args, kwargs))
    __check_for_problems(args, kwargs)
    return int(subprocess.call(*args, **kwargs))


def check_call(*args, **kwargs):
    """subprocess.check_call wrapper to not leak file descriptors
    """
    kwargs = __update_kwargs(kwargs)
    LOGGER.debug("Checking call with: %s %s" % (args, kwargs))
    __check_for_problems(args, kwargs)
    return int(subprocess.check_call(*args, **kwargs))


def check_output(*args, **kwargs):
    """subprocess.check_output wrapper to not leak file descriptors

    >>> check_output(["echo", "-n", "42"])
    u'42'
    >>> check_output("echo -n 42", shell=True)
    u'42'
    >>> check_output("false", shell=True)
    Traceback (most recent call last):
    ...
    CalledProcessError: Command 'false' returned non-zero exit status 1
    """
    kwargs = __update_kwargs(kwargs)
    LOGGER.debug("Checking output with: %s %s" % (args, kwargs))
    __check_for_problems(args, kwargs)
    try:
        return unicode(subprocess.check_output(*args, **kwargs),
                       encoding=sys.stdin.encoding or "utf-8")
    except AttributeError:
        # We're probably on Python 2.6, which doesn't have check_output
        # http://docs.python.org/2.6/library/subprocess.html#module-subprocess
        # Working around by using pipe with it's check feature
        return pipe(*args, check=True, **kwargs)

    return stdout


def pipe(cmd, stdin=None, check=False, **kwargs):
    """Run a non-interactive command and return it's output

    Args:
        cmd: Cmdline to be run
        stdin: (optional) Data passed to stdin
        check: Raise an CalledProcessException if the cmd fails

    Returns:
        stdout, stderr of the process (as one blob)

    >>> pipe("echo 1")
    u'1\\n'
    >>> pipe("false ; echo -n 42")
    u'42'
    >>> pipe("true")
    u''
    >>> pipe("false")
    u''

    When asked, pipe() can also throw Exceptions
    >>> pipe("false", check=True)
    Traceback (most recent call last):
    ...
    CalledProcessError: Command 'false' returned non-zero exit status 1

    This is how pipe is used in check_output as a fallback, so let's check
    it here too:
    >>> args = ["false"]
    >>> kwargs = {}
    >>> pipe(*args, check=True, **kwargs)
    Traceback (most recent call last):
    ...
    CalledProcessError: Command 'false' returned non-zero exit status 1
    """
    kwargs.update({"stdin": PIPE,
                   "stdout": PIPE,
                   "stderr": STDOUT})
    if type(cmd) in [str, unicode]:
        kwargs["shell"] = True
    __check_for_problems(cmd, kwargs)
    proc = popen(cmd, **kwargs)
    stdout, stderr = proc.communicate(stdin)

    #
    # We need to handle the checking ourselfs, mainly for el6 comapatability
    # as a fallback for check_output
    #
    if check and proc.returncode != 0:
        err = CalledProcessError(proc.returncode, cmd)
        err.output = stderr
        raise err

    return unicode(stdout)
