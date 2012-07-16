#!/bin/env python
# -*- coding: utf-8 -*
# vim: set sw=4:

import sys
import os
import logging
import time

sys.path.append(os.environ["IGOR_LIBDIR"])
import common.input

KEY_DOWN = common.input.uinput.KEY_DOWN
KEY_UP = common.input.uinput.KEY_UP


story = [
    # First page, expect "Power Off" to be on the screen
    (None,                0, "<Power Off>"),
]

keywords = ["System Identification",        # Network page
            "Remote Access",                # Security page
            "Keyboard Layout Selection",    # Keyboard page
            "Enable SNMP",                  # SNMP page
            "Logrotate",                    # Logging page
            "NFS Location",                 # Kernel Dump page
            "iSCSI",                        # Remote Storage page
            "CIM Access",                   # CIM page
            "Monitoring Configuration",     # Monitoring
            "Management Server"             # oVirt Engine Page
        ]

# Now press key down, and expext $txt to be on the screen for all keywords
for txt in keywords:
    story.append(([KEY_DOWN], 2, txt))

# Now go back up and don't expect anythiong special (None)
for txt in keywords:
    story.append(([KEY_UP], 2, None))

# At last expect "<Power Off>" to be on the screen again
story.append((None, 0, "<Power Off>"))

if __name__ == "__main__":
    common.input.Storyboard("Enter all top menus and go back", \
                            story).run_and_exit()
