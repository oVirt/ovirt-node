#!/usr/bin/python

import sys
import re
import os

include_regex = re.compile("^%include\s+(.*)")

def usage():
    print "Usage: ks_fold_include.py <kickstart>"
    sys.exit(1)

def replace_lines(filename):
    try:
        file = open(filename)
        for line in file.readlines():
            matched = include_regex.match(line)
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

dirname = os.path.dirname(sys.argv[1])
basename = os.path.basename(sys.argv[1])

# if the user passes an argument like 'ks_fold_include.py foo.ks', then
# dirname returns a blank string; assume we are already in the right directory
# and do nothing
if dirname != '':
	os.chdir(dirname)

replace_lines(basename)
