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

def wait_for_last_page():
    """We poll to see when the installation has finished, it's done this way
    to avoid a niave sleep for 240 seconds
    """
    return common.input.wait_for_regex_on_screen("Installation Finished", 240)

story = [
    # P. 1 Welcome
    # Press nothing, wait 0 seconds, expect "Install …"
    (None,                  0, "Install Hypervisor"),

    # P. 2: Enter keyboard selection
    # Press ENTER, wait 4 seconds, expect "Keyboard …"
    (["\n"],                10, "Keyboard Layout Selection"),

    # P. 2: Select german keyboard layout
    # Press 53 times UP, wait 0 seconds and expect "German"
    (39 * [common.input.uinput.KEY_UP], 10, "German"),

    # P. 3: Enter boot device selection
    # Press ENTER wait 4 seconds and expect "booting …"
    (["\n"],               10, "booting oVirt Node"),

    # P. 4: Enter installation device selection
    (["\n"],               10, "installation of oVirt Node"),

    # P. 5: Enter sizes dialog
    (["\t\t\t\n"],         10, "enter the sizes for"),

    # P. 6: Enter password dialog
    (["\t\t\t\t\t\t\n"],   10, "Require a password"),
    # P. 6: Enter password
    (["ovirt\tovirt\t"],   10, "a weak password"),

    # P. 7: Start installation, and give it at most 240 seconds to complete
    (["\t\t\n"],   wait_for_last_page, "Installation Finished"),
]

reboot_seq = [
    # P. 7: Reboot
    "\n"
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
