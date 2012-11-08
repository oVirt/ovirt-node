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

# Tab sequence: Password - Confirm Password - Quit - Back - Install

story = [
    # P. 5: Enter password dialog
    (None,                  10, "Require a password"),
]

# Check if the Caps Lock hint appears
story += [
    # Actiavte Caps Lock and change the field, hint appears
    ([common.input.uinput.KEY_CAPSLOCK, "\t"],    5,  "Hint: Caps lock is on"),
    # Deactivate Caps Lock and tab until back in password field
    ([common.input.uinput.KEY_CAPSLOCK, "\t\t\t\t"],    0,  None) # FIXME negative case
]

story += [
    # Set a default password
    (["ovirt\tovirt\t"],    2, "a weak password"),

    # P. 6: Start installation, and give it at most 240 seconds to complete
    (["\t\t\n"],            0, None),
]

if __name__ == "__main__":
    common.input.Storyboard(title, story).run_and_exit()
