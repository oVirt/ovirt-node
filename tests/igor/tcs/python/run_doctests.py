#!/bin/env python
# -*- coding: utf-8 -*
# vim: set sw=4:

import sys
import os
import logging

import doctest

sys.path.append(os.environ["IGOR_LIBDIR"])
import common.common

logger = logging.getLogger(__name__)


modules_to_test = [
    "ovirtnode.ovirtfunctions"
]



def debug(msg):
    logger.debug(msg)

def run_doctest():
    # look at doctest.py
    for mname in modules_to_test:
        debug("Testing doctests of '%s'" % mname)
        m = __import__(mname)
        failures, _ = doctest.testmod(m)
        if failures:
            return False
    return True

def main():
    debug("Starting %s" % __name__)
    passed = False
    try:
        passed = run_doctest()
    except Exception as e:
        debug(e.message)
    debug("Finished %s" % __name__)

    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(main())
