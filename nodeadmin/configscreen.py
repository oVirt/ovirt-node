# configscreen.py - Copyright (C) 2009 Red Hat, Inc.
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
from halworker import HALWorker
from libvirtworker import LibvirtWorker
import traceback

BACK_BUTTON   = "back"
NEXT_BUTTON   = "next"
CANCEL_BUTTON = "cancel"
FINISH_BUTTON = "finish"

class ConfigScreen:
    '''Enables the creation of navigable, multi-paged configuration screens.'''

    def __init__(self, title):
        self.__title = title
        self.__current_page = 1
        self.__finished = False
        self.__hal = HALWorker()
        self.__libvirt = LibvirtWorker()

    def get_hal(self):
        return self.__hal

    def get_libvirt(self):
        return self.__libvirt

    def set_finished(self):
        self.__finished = True

    def get_elements_for_page(self, screen, page):
        return []

    def page_has_next(self, page):
        return False

    def page_has_finish(self, page):
        return False

    def get_back_page(self, page):
        if page > 1: return page - 1
        return page

    def go_back(self):
        self.__current_page = self.get_back_page(self.__current_page)

    def get_next_page(self, page):
        return page + 1

    def go_next(self):
        self.__current_page = self.get_next_page(self.__current_page)

    def validate_input(self, page, errors):
        return True

    def process_input(self, page):
        return

    def start(self):
        active = True
        while active and (self.__finished == False):
            screen = SnackScreen()
            gridform = GridForm(screen, self.__title, 1, 4)
            elements = self.get_elements_for_page(screen, self.__current_page)
            current_element = 0
            for element in elements:
                gridform.add(element, 0, current_element)
                current_element += 1
            # create the navigation buttons
            buttons = []
            if self.__current_page > 1: buttons.append(["Back", BACK_BUTTON, "F11"])
            if self.page_has_next(self.__current_page): buttons.append(["Next", NEXT_BUTTON, "F12"])
            if self.page_has_finish(self.__current_page): buttons.append(["Finish", FINISH_BUTTON, "F10"])
            buttons.append(["Cancel", CANCEL_BUTTON, "ESC"])
            buttonbar = ButtonBar(screen, buttons)
            gridform.add(buttonbar, 0, current_element, growx = 1)
            current_element += 1
            try:
                result = gridform.runOnce()
                pressed = buttonbar.buttonPressed(result)
                if pressed == BACK_BUTTON:
                    self.go_back()
                elif pressed == NEXT_BUTTON or pressed == FINISH_BUTTON:
                    errors = []
                    if self.validate_input(self.__current_page, errors):
                        self.process_input(self.__current_page)
                        self.go_next()
                    else:
                        error_text = ""
                        for error in errors:
                            error_text += "%s\n" % error
                            ButtonChoiceWindow(screen,
                                               "There Were Errors",
                                               error_text,
                                               buttons = ["OK"])
                elif pressed == CANCEL_BUTTON:
                    active = False
            except Exception, error:
                ButtonChoiceWindow(screen,
                                   "An Exception Has Occurred",
                                   str(error) + "\n" + traceback.format_exc(),
                                   buttons = ["OK"])
            screen.popWindow()
            screen.finish()

class DomainListConfigScreen(ConfigScreen):
    '''Provides a base class for all config screens that require a domain list.'''

    def __init__(self, title):
        ConfigScreen.__init__(self, title)

    def get_domain_list_page(self, screen, defined=True, created=True):
        domains = self.get_libvirt().list_domains(defined, created)
        result = None

        if len(domains) > 0:
            self.__has_domains = True
            self.__domain_list = Listbox(0)
            for name in self.get_libvirt().list_domains(defined, created):
                self.__domain_list.append(name, name)
            result = [self.__domain_list]
        else:
            self.__has_domains = False
            grid = Grid(1, 1)
            grid.setField(Label("There are no domains available."), 0, 0)
            result = [grid]
        return result

    def get_selected_domain(self):
        return self.__domain_list.current()

    def has_selectable_domains(self):
        return self.__has_domains
