"""
Some convenience functions
"""

import subprocess
import logging
import shutil
import os

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


def copy_contents(src, dst):
    assert all([os.path.isfile(f) for f in [src, dst]]), \
           "Source and destination need to exist"
    with open(src, "r") as srcf, open(dst, "wb") as dstf:
        dstf.write(srcf.read())


class BackupedFiles(object):
    """This context manager can be used to keep backup of files while messing
    with them.

    >>> txt = "Hello World!"
    >>> dst = "example.txt"
    >>> with open(dst, "w") as f:
    ...     f.write(txt)
    >>> txt == open(dst).read()
    True

    >>> with BackupedFiles([dst]) as backup:
    ...     b = backup.of(dst)
    ...     txt == open(b).read()
    True

    >>> with BackupedFiles([dst]) as backup:
    ...     try:
    ...         open(dst, "w").write("Argh ...").close()
    ...         raise Exception("Something goes wrong ...")
    ...     except:
    ...         backup.restore(dst)
    >>> txt == open(dst).read()
    True

    >>> os.remove(dst)
    """

    files = []
    backups = {}
    suffix = ".backup"

    def __init__(self, files, suffix=".backup"):
        assert type(files) is list, "A list of files is required"
        assert all([os.path.isfile(f) for f in files]), \
               "Not all files exist: %s" % files
        self.files = files
        self.suffix = suffix

    def __enter__(self):
        """Create backups when starting
        """
        for fn in self.files:
            backup = "%s%s" % (fn, self.suffix)
            assert not os.path.exists(backup)
            shutil.copy(fn, backup)
            self.backups[fn] = backup
        return self

    def __exit__(self, a, b, c):
        """Remove all backups when done
        """
        for fn in self.files:
            backup = self.backups[fn]
            os.remove(backup)

    def of(self, fn):
        """Returns the backup file for the given file
        """
        assert fn in self.backups, "No backup for '%s'" % fn
        return self.backups[fn]

    def restore(self, fn):
        """Restore contens of a previously backupe file
        """
        copy_contents(self.of(fn), fn)
