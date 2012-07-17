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

title = "TUI Installer Last/Progress Page"

story = [
    # P. 6: Start installation, and give it at most 240 seconds to complete
    (None, 180, "Installation Finished"),
]

if __name__ == "__main__":
    common.input.Storyboard(title, story).run_and_exit()
