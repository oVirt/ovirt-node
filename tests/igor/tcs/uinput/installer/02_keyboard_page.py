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

title = "TUI Installer Keyboard Page"

story = [
    # P. 2: Enter keyboard selection
    # Press ENTER, wait 4 seconds, expect "Keyboard …"
    (None,      10, "Keyboard Layout Selection"),

    # P. 2: Select german keyboard layout
    # Press 53 times UP, wait 0 seconds and expect "German"
    (39 * [common.input.uinput.KEY_UP], 10, "German"),

    # P. 3: Enter boot device selection
    # Press ENTER wait 4 seconds and expect "booting …"
    (["\n"],    0, None),
]

if __name__ == "__main__":
    common.input.Storyboard(title, story).run_and_exit()
