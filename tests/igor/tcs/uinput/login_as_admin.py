#!/bin/env python
# -*- coding: utf-8 -*
# vim: set sw=4:

import sys
import os
import logging
import time

sys.path.append(os.environ["IGOR_LIBDIR"])
import common.input


story = [
    # Enter Nothing, wait 0 seconds, expect "Please Login" on screen
#    (None,                0, "Please login"), # Ignore this for now.

    # Enter …, wait … seconds, expect … on screen
    (["admin\n"],           2, "Password:"),

    # Password (taken from set admin password)
    (["ovirt\n"],           5, "Networking:")
]


if __name__ == "__main__":
    common.input.Storyboard("TUI login", story).run_and_exit()
