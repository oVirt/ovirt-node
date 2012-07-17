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

title = "TUI Installer Welcome Page"

story = [
    # P. 1 Welcome
    # Press nothing, wait 0 seconds, expect "Install …"
    (None,                  0, "Install Hypervisor"),

    # P. 2: Enter keyboard selection
    # Press ENTER, wait 4 seconds, expect "Keyboard …"
    (["\n"],                0, None)
]

if __name__ == "__main__":
    common.input.Storyboard(title, story).run_and_exit()
