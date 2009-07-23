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
EXIT_CONSOLE     = 99

def MainMenu():
    finished = False
    while finished == False:
        screen = SnackScreen()
        menu = Listbox(height = 0, width = 0, returnExit = 1)
        menu.append("Define A Domain",     DEFINE_DOMAIN)
        menu.append("Create A Domain",     CREATE_DOMAIN)
        menu.append("Destroy A Domain",    DESTROY_DOMAIN)
        menu.append("Undefine A Domain",   UNDEFINE_DOMAIN)
        menu.append("List All Domains",    LIST_DOMAINS)
        menu.append("Create A User",       CREATE_USER)
        menu.append("Exit Administration", EXIT_CONSOLE)
        gridform = GridForm(screen, "Node Administration Console", 1, 4)
        gridform.add(menu, 0, 0)
        result = gridform.run();
        screen.popWindow()
        screen.finish()

        try:
            if   result.current() == DEFINE_DOMAIN:   DefineDomain()
            elif result.current() == CREATE_DOMAIN:   CreateDomain()
            elif result.current() == DESTROY_DOMAIN:  DestroyDomain()
            elif result.current() == UNDEFINE_DOMAIN: UndefineDomain()
            elif result.current() == LIST_DOMAINS:    ListDomains()
            elif result.current() == CREATE_USER:     CreateUser()
            elif result.current() == EXIT_CONSOLE:    finished = True
        except Exception, error:
            screen = SnackScreen()
            logging.info("An exception occurred: %s" % str(error))
            ButtonChoiceWindow(screen,
                               "An Exception Has Occurred",
                               str(error) + "\n" + traceback.format_exc(),
                               buttons = ["OK"])
            screen.popWindow()
            screen.finish()
            finished = True
