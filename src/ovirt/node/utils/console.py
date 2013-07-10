#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# console.py - Copyright (C) 2013 Red Hat, Inc.
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
from ovirt.node import base
from ovirt.node.utils import Transaction, process
import StringIO
import sys
import termios
import tty


def reset():
    process.call(["reset"])


def writeln(txts):
    """Write something to stdout
    A wrapper if we want to do this differently in future
    """
    if type(txts) is not list:
        txts = [txts]

    sys.stdout.write("\n".join(txts))
    sys.stdout.write("\n")


def wait_for_keypress():
    """Waits until the user presses any key

    Returns:
        The key pressed by the user
    """
    return getch()


class TransactionProgress(base.Base):
    """Display the progress of a transaction on a console
    """
    transaction = None
    texts = None
    is_dry = False

    def __init__(self, transaction, is_dry, initial_text=""):
        assert type(transaction) is Transaction
        self.transaction = transaction
        self.is_dry = is_dry
        self.texts = [initial_text, ""]
        super(TransactionProgress, self).__init__()

    def add_update(self, txt):
        self.texts.append(txt)
        self.logger.debug(txt)
        self._print_func(txt)

    def _print_func(self, txt):
        writeln(txt)

    def run(self):
        if self.transaction:
            self.logger.debug("Initiating transaction")
            self.__run_transaction()
        else:
            self.add_update("There were no changes, nothing to do.")

    def __print_title(self):
        writeln([self.transaction.title,
                 "-" * len(self.transaction.title)])

    def __run_transaction(self):
        try:
            self.__print_title()
            self.logger.debug("Preparing transaction for console %s" %
                              self.transaction)
            self.add_update("Checking pre-conditions ...")
            self.transaction.prepare()  # Just to display something in dry mode
            for idx, e in enumerate(self.transaction):
                txt = "(%s/%s) %s" % (idx + 1, len(self.transaction), e.title)
                self.add_update(txt)
                with CaptureOutput() as captured:
                    # Sometimes a tx_element is wrapping some code that
                    # writes to stdout/stderr which scrambles the screen,
                    # therefore we are capturing this
                    if self.is_dry:
                        self.logger.debug("In dry mode: %s" % e)
                    else:
                        e.commit()
            self.add_update("\nAll changes were applied successfully.")
        except Exception as e:
            self.add_update("\nAn error occurred while applying the changes:")
            self.add_update("%s" % e)
            self.logger.exception("'%s' on transaction '%s': %s - %s" %
                                  (type(e), self.transaction,
                                   e, e.message))
            raise

        if captured.stderr.getvalue():
            se = captured.stderr.getvalue()
            if se:
                self.add_update("Stderr: %s" % se)


def getch():
    """getch() -> key character

    Read a single keypress from stdin and return the resulting character.
    Nothing is echoed to the console. This call will block if a keypress
    is not already available, but will not wait for Enter to be pressed.

    If the pressed key was a modifier key, nothing will be detected; if
    it were a special function key, it may return the first character of
    of an escape sequence, leaving additional characters in the buffer.

    source: http://code.activestate.com/recipes/577977-get-single-keypress/
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


class CaptureOutput(base.Base):
    """This context manager can be used to capture any output (from e.g. a
    subprocess or wrongly configured loggers) to different streams

    >>> import sys
    >>> with CaptureOutput() as captured:
    ...     sys.stdout.write("Hey!")
    ...     sys.stderr.write("There!")
    >>> captured.stdout.getvalue()
    'Hey!'
    >>> captured.stderr.getvalue()
    'There!'
    """

    def __init__(self, stdout=None, stderr=None):
        super(CaptureOutput, self).__init__()
        self.stdout = stdout or StringIO.StringIO()
        self.stderr = stderr or StringIO.StringIO()

    def __enter__(self):
        """Create redirections
        """
        self.logger.debug("Redirecting %s to %s" % (sys.stdout, self.stdout))
        self.logger.debug("Redirecting %s to %s" % (sys.stderr, self.stderr))
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        return self

    def __exit__(self, a, b, c):
        """Remove all redirections
        """
        sys.stdout = self._stdout
        sys.stderr = self._stderr
        self.logger.debug("Removed redirections")
        so = self.stdout.getvalue()
        se = self.stderr.getvalue()
        if so or se:
            self.logger.info("Captured:")
        else:
            self.logger.info("Captured nothing")
        if se:
            self.logger.info("stderr: %s" % se)
        if so:
            self.logger.info("stdout: %s" % so)
