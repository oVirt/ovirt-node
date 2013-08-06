#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# password.py - Copyright (C) 2013 Red Hat, Inc.
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
from ovirt.node.utils import security
from ovirt.node.utils.security import password_check
import cmd
import getpass
import logging
import optparse
import sys


class PasswordTool(cmd.Cmd):
    intro = "\n\n Password Configuration\n\n Enter ? for help.\n"
    prompt = "> "
    is_debug = False

    def __init__(self, debug=False):
        cmd.Cmd.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.is_debug = debug

    def do_set_root_password(self, line):
        """Set root password
        """
        self.__ask_and_set_user_pasword("root")

    def do_set_admin_password(self, line):
        """Set admin user password
        """
        self.__ask_and_set_user_pasword("admin")

    def do_set_ssh_password_authentication(self, line):
        """Toggle SSH password authentication
        """
        print("\n SSH password authentication\n")
        prompt = "Enable SSH password authentication ([Y]es/[N]o)?"
        do_enable = self.__ask_yes_or_no(prompt)
        self.logger.debug("Setting SSH password authentication")
        is_enabled = security.Ssh().password_authentication(do_enable)
        state = ("enabled" if is_enabled else "disabled")
        self.logger.info("SSH password authentication is "
                         "currently %s." % state)

    def do_quit(self, line):
        """Quit
        """
        return True

    def __ask_yes_or_no(self, prompt):
        self.logger.debug("Asking for yes and no")
        sys.stdout.write(prompt)
        response = sys.stdin.readline()
        return response and response.lower()[0] == "y"

    def __ask_and_set_user_pasword(self, username):
        min_pw_length = 1

        print("\n Password Configuration\n")
        print("System Administrator (%s):\n" % username)
        print("Changing password for user '%s'." % username)
        pw = getpass.getpass("New password: ")
        pwc = getpass.getpass("Retype new Password: ")

        try:
            all_args = (pw, pwc, min_pw_length, username)
            self.logger.debug("Running password check")
            msg = password_check(pw, pwc, min_pw_length)
            if msg:
                self.logger.warn(msg)
            self.logger.debug("Setting password: %s" % str(all_args))
            security.Passwd().set_password(username, pw)
            self.logger.info("Password updated successfully.")
        except ValueError as e:
            if self.is_debug:
                self.logger.exception("Exception:")
            self.logger.error("Password update failed: %s" % e.message)


if __name__ == "__main__":
    # Parse args
    parser = optparse.OptionParser(description="Node Password Tool")
    parser.add_option("-v", "--verbose", action="store_true",
                      help="Be verbose")
    namespace, rest = parser.parse_args()

    # Configure logging
    lvl = logging.DEBUG if namespace.verbose else logging.INFO
    logging.basicConfig(level=lvl, format='[%(levelname)s] %(message)s')

    # Setup CLI
    cli = PasswordTool(namespace.verbose)

    #if namespace.command:
    #    for command in namespace.command:
    #        if command.strip():
    #            cli.onecmd(command)
    #else:
    cli.cmdloop()
