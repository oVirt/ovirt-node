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

def wait_for_last_page():
    """We poll to see when the installation has finished, it's done this way
    to avoid a niave sleep for 240 seconds
    """
    return common.input.wait_for_regex_on_screen("Installation Finished", 240)

story = [
    # P. 6: Start installation, and give it at most 240 seconds to complete
    (None, wait_for_last_page, "Installation Finished"),
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
