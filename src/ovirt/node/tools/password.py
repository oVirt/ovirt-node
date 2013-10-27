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
import cmd
import getpass
import logging
import optparse
import sys

logging.basicConfig(format='[%(levelname)s] %(message)s')

from ovirt.node.utils import security
from ovirt.node.utils.security import password_check


class PasswordTool(cmd.Cmd):
    intro = "\n\n Password Configuration\n\n"
    prompt = "> "
    is_debug = False

    def __init__(self, debug=False):
        cmd.Cmd.__init__(self)
        self.logger = logging.getLogger()
        self.is_debug = debug

    def preloop(self):
        print(self.intro)
        print("Possible commands:")
        self.do_help("")
        print("")
        self.do_get_ssh_password_authentication("")
        print("")
        self.intro = None

    def emptyline(self):
        pass

    def do_help(self, line=None):
        """Show this help. [`help --all` to show all available functions]
        """
        show_all = line.strip() == "--all"
        funcs = []
        for name in sorted(self.get_names()):
            if name.startswith("do_"):
                doc = getattr(self, name).__doc__
                doc = doc or ""
                doc = doc.strip()
                if not (name[3:], doc) in funcs:
                    funcs.append((name[3:], doc))

        max_name_len = max(len(n) for n, d in funcs if d)

        def print_doc(name, doc):
            print("%s  %s" % (name.ljust(max_name_len), doc))

        if line in (n for n, _ in funcs):
            print_doc(line, dict(funcs)[line])
        else:
            for name, doc in ((n, d) for n, d in funcs if d):
                print_doc(name, doc)

            if show_all:
                print("\nCommands without help")
                for name, doc in ((n, d) for n, d in funcs if not d):
                    print_doc(name, "")

    def do_root(self, line):
        """Set the password of the user 'root'
        """
        return self.do_set_root_password(line)

    def do_admin(self, line):
        """Set the password of the user 'admin'
        """
        return self.do_set_admin_password(line)

    def do_ssh(self, line):
        """Enable or disable the SSH password authentication
        """
        self.do_get_ssh_password_authentication(line)
        prompt = "Do you want to change this?"
        if self.__ask_yes_or_no(prompt):
            self.do_set_ssh_password_authentication(line)

    def do_set_root_password(self, line):
        self.__ask_and_set_user_pasword("root")

    def do_set_admin_password(self, line):
        self.__ask_and_set_user_pasword("admin")

    def do_get_ssh_password_authentication(self, line):
        is_enabled = security.Ssh().password_authentication()
        status = "enabled" if is_enabled else "disabled"
        self.logger.info("SSH password authentication is currently %s" %
                         status)

    def do_set_ssh_password_authentication(self, line):
        print("\n SSH password authentication\n")
        self.do_get_ssh_password_authentication(line)
        prompt = "Enable SSH password authentication?"
        do_enable = self.__ask_yes_or_no(prompt)
        self.logger.debug("Setting SSH password authentication")
        is_enabled = security.Ssh().password_authentication(do_enable)
        state = ("enabled" if is_enabled else "disabled")
        self.logger.info("SSH password authentication is "
                         "currently %s." % state)

    def do_q(self, line):
        """Quit this tool
        """
        return self.do_quit(line)

    def do_quit(self, line):
        """Quit this tool
        """
        return True

    def __ask_yes_or_no(self, prompt):
        self.logger.debug("Asking for yes and no")
        sys.stdout.write(prompt + " ([Y]es/[N]o)")
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
    logging.getLogger().setLevel(lvl)

    # Setup CLI
    cli = PasswordTool(namespace.verbose)

    cli.cmdloop()
