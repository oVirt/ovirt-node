#!/bin/env python
# -*- coding: utf-8 -*
# vim: set sw=4:

"""
Set the password of $USERNAME to $PASSWORD using the ovirt node specififc
functions
"""

import sys
import logging

import ovirtnode.password


LOGGER = logging.getLogger(__name__)


USERNAME = "admin"
PASSWORD = "ovirt"


def main():
    LOGGER.debug("Setting password of %s to %s" % (USERNAME, PASSWORD))

    passed = ovirtnode.password.set_password(PASSWORD, USERNAME)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
