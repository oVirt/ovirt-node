#!/usr/bin/python
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# copyright (c) 2008 Red Hat, Inc - written by Seth Vidal


# take list of pkgs
# resolve deps
# for pkg in list return size_archive
# total it up
# convert to human-readable numbers, etc
# output info:
#  #pkgs, avg size, total size... what else?

import sys, os
import yum
from urlgrabber.progress import format_number
import pykickstart
import pykickstart.parser



def handle_kickstart(filename):
    #FIXME XXX - check this out for dealing with negations or whatever oddness that
    # that ks will accept that yum may not
    myparser = pykickstart.parser.KickstartParser(pykickstart.version.makeVersion())
    myparser.readKickstart(filename)
    pkglist = []
    pkglist.extend(myparser.handler.packages.packageList)
    grouplist = [group.name for group in myparser.handler.packages.groupList]
    return pkglist, grouplist

def do_installed_size_stats(pkglist=[],grouplist=[]):
    my = yum.YumBase()
    my.conf.installroot=yum.misc.getCacheDir()
    my.conf.cachedir=yum.misc.getCacheDir()
    my.repos.setCacheDir(my.conf.cachedir)
    for pkgname in pkglist:
        try:
            my.install(pattern=pkgname)
        except yum.Errors.InstallError, e:
            print >> sys.stderr, 'Package name: %s - %s' % (pkgname, str(e))
            #FIXME XXX - make it handle groups, too
    my.resolveDeps()
    pkgs = []
    for pkg in my.tsInfo:
        pkgs.append(pkg.po)
    return pkgs

def main():
    if len(sys.argv) < 2:
        print 'You must give a list of pkgs to process'
    
    # FIXME XXX - needs to take ks.cfg as an option and an alternate yum.conf, etc
    pkgs = do_installed_size_stats(pkglist=sys.argv[1:])
    numpkgs = len(pkgs)
    if numpkgs == 0:
        print >> sys.stderr, 'No packages in chroot, nothing to do'
        sys.exit(1)

    for pkg in pkgs:
        print '%s\t%s.%s' % (pkg.size_archive, pkg.name, pkg.arch)

if __name__ == '__main__':
    main()
