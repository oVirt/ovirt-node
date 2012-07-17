#!/bin/env python
# -*- coding: utf-8 -*
# vim: set sw=4:

import sys
import os
import logging
import time

sys.path.append(os.environ["IGOR_LIBDIR"])
import common.common
import common.input


logger = logging.getLogger(__name__)

title = "TUI Installer Password Page"

story = [
    # P. 5: Enter password dialog
    (None,                  4, "Require a password"),
    (["ovirt\tovirt\t"],    2, "a weak password"),

    # P. 6: Start installation, and give it at most 240 seconds to complete
    (["\t\t\n"],            0, None),
]

if __name__ == "__main__":
    common.input.Storyboard(title, story).run_and_exit()
