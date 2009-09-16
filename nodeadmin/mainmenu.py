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
from nodemenu       import NodeMenu
from netmenu        import NetworkMenu

import utils
import logging

NODE_MENU    = 1
NETWORK_MENU = 2
EXIT_CONSOLE = 99

class MainMenuScreen(MenuScreen):
    def __init__(self):
        MenuScreen.__init__(self, "Main Menu")

    def get_menu_items(self):
        return (("Node Administration", NODE_MENU),
                ("Network Administration", NETWORK_MENU))

    def handle_selection(self, page):
        if   page is NODE_MENU:    NodeMenu()
        elif page is NETWORK_MENU: NetworkMenu()

def MainMenu():
    screen = MainMenuScreen()
    screen.start()
