#!/usr/bin/python -tt
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""
NAME
       getsrpms.py - stripped-down pungi-1.2.18.1 which downloads SRPMs only

SYNOPSIS
       getsrpms.py kickstart.cfg yum_cache

       kickstart.cfg - kickstart with repo commands and %package section
       yum_cache - YUM cache directory
"""

import pypungi.config
import pypungi.gather
import pykickstart.parser
import pykickstart.version
import sys

config = pypungi.config.Config()

# Set up the kickstart parser and pass in the kickstart file we were handed
ksparser = pykickstart.parser.KickstartParser(pykickstart.version.makeVersion())
ksparser.readKickstart(sys.argv[1])

config.set('default', 'version', '')
config.set('default', 'cachedir', sys.argv[2])
mygather = pypungi.gather.Gather(config, ksparser)
mygather.getPackageObjects()
mygather.getSRPMList()
mygather.downloadSRPMs()
