#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# core.py - Copyright (C) 2013 Red Hat, Inc.
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
Core Setup Plugins
"""
from ovirt.node import loader


#
# Magic function to register all plugins to be used
#
def all_modules():
    for plugin in loader.get_modules_in_package(__package__):
        yield plugin


def createPlugins(application):
    # Lazy load all plugins in this package
    for plugin in all_modules():
        plugin.Plugin(application)
