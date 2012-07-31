#!/bin/env python
# -*- coding: utf-8 -*
# vim: set sw=4:

import sys
import os
import logging
import time
import re
import random

import common

logger = logging.getLogger(__name__)

#
# Import python-uinput
#
version = "%d.%d" % sys.version_info[0:2]
uinput_include_path = "uinput/dst/lib64/python%s/site-packages/" % version
UINPUTPYDIR = os.path.join(common.igor.libdir, uinput_include_path)

if not os.path.exists(UINPUTPYDIR):
    raise Exception("No uinput for this python version: %s" % UINPUTPYDIR)
common.run("modprobe uinput")
common.add_searchpath(UINPUTPYDIR)
import uinput


# Map a char to a key
charmap = {
    ".": "dot",
    "-": "minus",
    "+": "plus",
    " ": "space",
    "\t": "tab",
    "\n": "enter"
}


def _all_keys():
    """Fetches all key related capabilities.
    """
    keys = []
    for k in uinput.__dict__:
        if re.match("^KEY_", k):
            keys.append(uinput.__dict__[k])
    return keys

device = uinput.Device(_all_keys())


class PressedKey(object):
    key = None

    def __init__(self, k):
        self.key = k

    def __enter__(self):
        device.emit(self.key, 1)

    def __exit__(self, type, value, traceback):
        device.emit(self.key, 0)


def char_to_key(char):
    """Maps a character to a key-code
    """
    if char in charmap:
        char = charmap[char]
    key_key = "KEY_%s" % char.upper()
    return uinput.__dict__[key_key]


def press_key(key, delay=12):
    """Simulates a key stroke
    """
    with PressedKey(key):
        time.sleep(1.0 / 100 * delay * random.uniform(0.5, 1.5))


def send_input(txt):
    """Send the string as keystrokes to uinput
    """
    logger.debug("Inputing: %s" % txt)
    for char in txt:
        if char.isupper():
            with PressedKey(uinput.KEY_LEFTSHIFT):
                press_key(char_to_key(char.lower()))
        else:
            press_key(char_to_key(char.lower()))


def play(seq):
    """Plays a sequence of text, single keys and callables
    """
    if type(seq) is not list:
        raise Exception("seq is expected to be a list of text, KEY_ " + \
                        "and callables")
    for item in seq:
        if callable(item):
            item()
        elif type(item) is tuple:
            # Expected to be a uinput.KEY_
            press_key(item)
        elif type(item) in [str, unicode]:
            send_input(item)
        else:
            logger.warning("Unknown sequence type: %s (%s)" % (type(item), \
                                                               item))


def screen_content(vcsn=1):
    vcs = "/dev/vcs%s" % vcsn
    logger.debug("Grabbing content from '%s'" % vcs)
    # setterm -dump $N
    content = open(vcs, "r").read()
    return content


def is_regex_on_screen(expr, vcsn=1):
    """Check if the given expression appears on the screen.
    """
    content = screen_content(vcsn)
    logger.debug("Looking for '%s' on '%s'" % (expr, vcsn))
    regex = re.compile(expr)
    return regex.search(content) is not None

def wait_for_regex_on_screen(expr, timeout, vcsn=1):
    """Check for at max timeout seconds if expr appears on the screen
    """
    found = False
    while timeout > 0:
        time.sleep(1)
        if is_regex_on_screen(expr, vcsn):
            found = True
            break
        timeout -= 1
    return found

class Storyboard(object):
    title = None
    story = None

    def __init__(self, title, story):
        self.title = title
        self.story = story

    def check(self):
        """Checks a "storyboard", so if the system behaves as the story tells
        A storyboard is expected to be in the form of:
        story = [
            (input_for_play, output_for_is_regex_on_screen_or_callable),
            .
            .
            .
        ]
        """
        passed = True
        for storyline in self.story:
            logger.info("Testing: %s" % str(storyline))

            input, wait, output = storyline

            if input is None:
                logger.debug("No input to send")
            else:
                play(input)

            if callable(wait):
                wait()
            else:
                time.sleep(wait)

            if output is None:
                logger.debug("No output expected")
            elif callable(output):
                passed = output(input)
            else:
                passed = is_regex_on_screen(output)

            if passed == False:
                content = screen_content()
                raise Exception("Response is not as expected.\n" + \
                                "Sent: %s\nExpected: %s\nGot: %s" % (input, \
                                                                     output, \
                                                                     content))
        msg = "passed" if passed else "failed"
        logger.info("Storyboard ended, finished: %s" % msg)
        return passed

    def run(self):
        """Run the story and eitehr return 0 on success or 1 on failure
        """
        logger.info("Starting simulated %s" % self.title)
        passed = False
        try:
            passed = self.check()
        except Exception as e:
            logger.warning("An exception: %s" % e.message)
            passed = False
        logger.info("Finished simulated %s" % self.title)

        return passed

    def run_and_exit(self):
        """Run the story and exit
        """
        sys.exit(0 if self.run() else 1)
