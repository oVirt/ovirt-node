#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# ovirt-node-setup.py - Copyright (C) 2012 Red Hat, Inc.
# Written by Fabian Deutsch <fabiand@redhat.com>
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

"""
Create an setup application instance an start it.
"""

from ovirt.node import app, setup, log, ui


def quit(instance):
    def ui_quit(dialog, changes):
        instance.ui.quit()
    txt = "Are you sure you want to quit?"
    dialog = ui.ConfirmationDialog("dialog.exit", "Exit", txt,
                                   [ui.Button("dialog.exit.yes", "Yes"),
                                    ui.CloseButton("dialog.exit.close", "No")]
                                   )

    dialog.buttons[0].on_activate.clear()
    dialog.buttons[0].on_activate.connect(ui.CloseAction())
    dialog.buttons[0].on_activate.connect(ui_quit)
    instance.show(dialog)


if __name__ == '__main__':
    args, _ = app.parse_cmdline()
    log.configure_logging(args.debug)
    instance = app.Application(setup, args, quit=quit)
    instance.run()
