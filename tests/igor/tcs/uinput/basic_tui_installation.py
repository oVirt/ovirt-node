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

from common.input.uinput import KEY_ENTER, KEY_UP, KEY_RIGHT, KEY_TAB


logger = logging.getLogger(__name__)

def wait_for_last_page():
    """We poll to see when the installation has finished, it's done this way
    to avoid a niave sleep for 240 seconds
    """
    return common.input.wait_for_regex_on_screen("5/5",
                                                 240)

story = [
    # P. 1 Welcome
    # Press nothing, wait 0 seconds, expect "Install …"
    (None,
     0,
     "Install Hypervisor"),

    # P. 2: Enter keyboard selection
    # Press ENTER, wait 4 seconds, expect "Keyboard …"
    ([KEY_ENTER],
     10,
     "Keyboard Layout Selection"),

    # P. 2: Select german keyboard layout
    # Press 53 times UP, wait 0 seconds and expect "German"
    (39 * [KEY_UP],
     20,
     "German"),

    # P. 3: Enter boot device selection
    # Press ENTER wait 4 seconds and expect "booting …"
    ([KEY_ENTER],
     10,
     "booting (oVirt Node|RHEV Hypervisor)"),

    # P. 4: Enter installation device selection
    (KEY_ENTER,
     10,
     "installation of (oVirt Node|RHEV Hypervisor)"),

    # P. 5: Enter sizes dialog
    ([KEY_TAB] + 2 * [KEY_RIGHT] + [KEY_ENTER],
     10,
     "enter the sizes for"),

    # P. 6: Enter volume sizes
    (4 * [KEY_TAB] + 2 * [KEY_RIGHT] + [KEY_ENTER],
     10,
     "Require a password"),

    # P. 7: Enter password
    (["ovirt", KEY_TAB, "ovirt", KEY_TAB],
     10,
     None),

    # P. 7: Start installation, and give it at most 240 seconds to complete
    (2 * [KEY_RIGHT] + [KEY_ENTER],
     wait_for_last_page,
     None),
]

reboot_seq = [
    # P. 7: Reboot
    [KEY_ENTER]
]

if __name__ == "__main__":
    passed = common.input.Storyboard("Basic TUI installation", story).run()

    if passed:
        common.common.set_reboot_marker()
        common.common.step_succeeded()
        common.input.play(reboot_seq)

        # Now block (because we are rebooting)
        time.sleep(60)

    sys.exit(1)
