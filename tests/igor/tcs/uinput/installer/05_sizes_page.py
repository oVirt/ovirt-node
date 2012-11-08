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

title = "TUI Installer Sizes Page"

story = [
    # Expect sizes page
    (None,                  10, "Please enter the sizes for"),
]

story += [
    # Keep default values
    (["\t\t\t\t\t\t\n"],            0, None),
]

if __name__ == "__main__":
    common.input.Storyboard(title, story).run_and_exit()
