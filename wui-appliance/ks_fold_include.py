#!/usr/bin/python

import sys
import re
import os

def usage():
    print "Usage: ks_fold_include.py <kickstart>"
    sys.exit(1)

def replace_lines(filename):
    try:
        file = open(filename)
        for line in file.readlines():
            matched = re.compile("^%include\s+(.*)").match(line)
            if matched:
                replace_lines(matched.group(1))
            else:
                sys.stdout.write(line)

        file.close()
    except IOError, detail:
        print detail
        sys.exit(2)

if len(sys.argv) != 2:
    usage()

os.chdir(os.path.dirname(sys.argv[1]))

replace_lines(os.path.basename(sys.argv[1]))
