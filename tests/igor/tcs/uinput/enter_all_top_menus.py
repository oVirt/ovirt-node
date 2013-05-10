#!/bin/env python
# -*- coding: utf-8 -*
# vim: set sw=4:

import sys
import os
import logging
import time

sys.path.append(os.environ["IGOR_LIBDIR"])
import common.input

from common.input.uinput import KEY_DOWN, KEY_UP

seconds_between_pages = 5

story = [
    # First page, expect "Power Off" to be on the screen
    (None,
     0,
     "<Power Off>"),
]

keywords = ["System Identification",        # Network page
            "Remote Access",                # Security page
            "Keyboard Layout Selection",    # Keyboard page
            "Logrotate",                    # Logging page
            "NFS Location",                 # Kernel Dump page
            "iSCSI",                        # Remote Storage page
            "Monitoring Configuration",     # Monitoring
        ]

# Now press key down, and expext $txt to be on the screen for all keywords
for txt in keywords:
    story.append(([KEY_DOWN], seconds_between_pages, txt))

# Now go back up and don't expect anythiong special (None)
for txt in keywords:
    story.append(([KEY_UP], 1, None))

# At last expect "<Power Off>" to be on the screen again
story.append((None, 0, "<Restart>"))

if __name__ == "__main__":
    common.input.Storyboard("Enter all top menus and go back", \
                            story).run_and_exit()
