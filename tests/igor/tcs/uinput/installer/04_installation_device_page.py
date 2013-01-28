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

title = "TUI Installer Installation Device Page"

story = [
    # P. 4: Enter installation device selection
    (None,          10, "installation of (oVirt Node|RHEV Hypervisor)"),

    # P. 5: Enter password dialog
    (["\t\t\t\n"],  0, None),
]

if __name__ == "__main__":
    common.input.Storyboard(title, story).run_and_exit()
