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

title = "TUI Installer Boot Device Page"

story = [
    # P. 3: Enter boot device selection
    # Press ENTER wait 4 seconds and expect "booting …"
    (None,      10, "booting (oVirt Node|RHEV Hypervisor)"),

    # P. 4: Enter installation device selection
    (["\n"],    0, None),
]

if __name__ == "__main__":
    common.input.Storyboard(title, story).run_and_exit()
