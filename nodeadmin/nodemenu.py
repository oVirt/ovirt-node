# mainmenu.py - Copyright (C) 2009 Red Hat, Inc.
# Written by Darryl L. Pierce <dpierce@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.

from snack import *
import traceback

from menuscreen     import MenuScreen
from configscreen   import ConfigScreen
from definedomain   import DefineDomain
from createdomain   import CreateDomain
from destroydomain  import DestroyDomain
from undefinedomain import UndefineDomain
from listdomains    import ListDomains
from createuser     import CreateUser

import utils
import logging

DEFINE_DOMAIN    = 1
CREATE_DOMAIN    = 2
DESTROY_DOMAIN   = 3
UNDEFINE_DOMAIN  = 4
LIST_DOMAINS     = 5
CREATE_USER      = 6

class NodeMenuScreen(MenuScreen):
    def __init__(self):
        MenuScreen.__init__(self, "Node Administration")

    def get_menu_items(self):
        return (("Define A Domain",        DEFINE_DOMAIN),
                ("Create A Domain",        CREATE_DOMAIN),
                ("Destroy A Domain",       DESTROY_DOMAIN),
                ("Undefine A Domain",      UNDEFINE_DOMAIN),
                ("List All Domains",       LIST_DOMAINS),
                ("Create A User",          CREATE_USER))

    def handle_selection(self, item):
            if   item is DEFINE_DOMAIN:   DefineDomain()
            elif item is CREATE_DOMAIN:   CreateDomain()
            elif item is DESTROY_DOMAIN:  DestroyDomain()
            elif item is UNDEFINE_DOMAIN: UndefineDomain()
            elif item is LIST_DOMAINS:    ListDomains()
            elif item is CREATE_USER:     CreateUser()

def NodeMenu():
    screen = NodeMenuScreen()
    screen.start()
