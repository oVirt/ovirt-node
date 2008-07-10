#!/usr/bin/python
#
# rpm-compare.py - return 0 if installed package version satisfies condition

import sys
import rpm
import rpmUtils.miscutils as rpmutils
# pkgTupleFromHeader(hdr) -> (name, arch, epoch, ver, rel)
# rangeCheck(reqtuple, pkgtuple) reqtuple := (reqn, reqf, (reqe, reqv, reqr))

def usage():
  print "usage: %s {GE|GT|EQ|LE|LT} epoch name ver rel \n" % sys.argv[0]
  sys.exit(1)

if len(sys.argv) < 6:
  usage()

cond = sys.argv[1]
epoch = sys.argv[2]
name = sys.argv[3]
ver = sys.argv[4]
rel = sys.argv[5]

if cond not in ('GE','GT','EQ','LE','LT'):
  usage()

#broken from pkgs with - in the name
#name, ver, rel, epoch, arch = rpmutils.splitFilename(rpmname)
##print "epoch %s name %s ver %s rel %s" % (epoch, name, ver, rel)

ts = rpm.TransactionSet()
for hdr in ts.dbMatch('name', name):
  (n, a, e, v, r) = rpmutils.pkgTupleFromHeader(hdr)
  ##print (n, a, e, v, r)
  if rpmutils.rangeCheck((name, cond, (epoch, ver, rel)), (n, a, e, v, r)) == 1:
    exit(0)
print 'RPM condition not satisfied'
exit(1)

