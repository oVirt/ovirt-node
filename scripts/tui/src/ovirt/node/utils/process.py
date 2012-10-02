"""
Some convenience functions related to processes
"""

import subprocess
import logging

LOGGER = logging.getLogger(__name__)


def popen_closefds(*args, **kwargs):
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
    return popen_closefds(cmd, shell=True).wait()


def pipe(cmd, stdin=None):
    """Run a command interactively and cath it's output.
    This functions allows to pass smoe input to a running command.

    Args:
        cmd: Commandline to be run

    Returns:
        A tuple (success, stdout)
    """

    LOGGER.debug("run '%s'" % cmd)
    system_cmd = popen_closefds(cmd, shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    stdout, stderr = system_cmd.communicate(stdin)
    if stdout:
        LOGGER.debug("out '%s'" % stdout)
    if stderr:
        LOGGER.warning("error '%s'" % stderr)
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
    LOGGER.debug("run async '%s'" % cmd)
    process = popen_closefds(cmd, shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    if stdin:
        process.stdin.write(stdin)
    while process.poll() != 0:
        yield process.stdout.readline()
