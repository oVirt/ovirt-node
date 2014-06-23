#!/usr/bin/env python2
#
# Copyright (C) 2014, Red Hat, Inc.
# Written by Ryan Barry <rbarry@redhat.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Convenience wrapper around doctest
import argparse
import doctest
import sys
import re
import os

def test():
    parser = argparse.ArgumentParser(description="Runs doctests on a file")
    parser.add_argument('FILE')
    arguments = parser.parse_args()

    testable = False
    for line in open(arguments.FILE):
        if ">>>" in line:
            testable = True

    if not testable:
        return 0

    else:
        mod = re.sub(r'\/', r'.', os.path.splitext(arguments.FILE)[0])
        try:
            test =  __import__(mod, globals(), locals(), ['object'], -1)
            failures,tests = doctest.testmod(test)
            if failures > 0:
                print "Failures from %s: %s" % (mod, failures)
                return -1
            else:
                return 0
        except ImportError:
            print "Failed to import %s" % arguments.FILE
            return -1


if __name__ == "__main__":
    sys.exit(test())
