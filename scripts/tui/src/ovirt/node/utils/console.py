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
import traceback
import sys


def writeln(txts):
    """Write something to stdout
    A wrapper if we want to do this differently in future
    """
    if type(txts) is not list:
        txts = [txts]

    sys.stdout.write("\n".join(txts))
    sys.stdout.write("\n")


def wait_for_keypress():
    sys.stdin.read(1)


class TransactionProgress(base.Base):
    """Display the progress of a transaction on a console
    """
    def __init__(self, transaction, plugin, initial_text=""):
        self.transaction = transaction
        self.plugin = plugin
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
            self.transaction.prepare()  # Just to display something in dry mode
            for idx, e in enumerate(self.transaction):
                txt = "(%s/%s) %s" % (idx + 1, len(self.transaction), e.title)
                self.add_update(txt)
                self.plugin.dry_or(lambda: e.commit())
            self.add_update("\nAll changes were applied successfully.")
        except Exception as e:
            self.add_update(("\nAn error occurred while applying the changes:")
            self.add_update("%s" % e)
            self.logger.warning("'%s' on transaction '%s': %s - %s" %
                                (type(e), self.transaction, e, e.message))
            self.logger.debug(str(traceback.format_exc()))
