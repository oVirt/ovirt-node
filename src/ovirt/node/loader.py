#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# plugins.py - Copyright (C) 2013 Red Hat, Inc.
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
import logging
import pkgutil

"""
This contains much stuff related to plugins
"""


logger = logging.getLogger(__name__)


def plugin_groups_iterator(basepackage, attrname):
    """High-level function to retrieve a specific function from a package
    """
    for group in load_plugin_groups(basepackage):
        attr = None
        if hasattr(group, attrname):
            attr = getattr(group, attrname)
        yield group, attr


def load_plugin_groups(basepackage):
    """Load all plugin groups (which can the contain plugins)

    Args:
        basepackage: The package where to look for packages
    """
    modules = []
    logger.debug("Loading plugin-groups from package: %s" % basepackage)
    for groupmodule in get_packages_in_package(basepackage):
        logger.debug("Found plugin-group package: %s" % groupmodule)
        modules.append(groupmodule)
    logger.debug("Loading loading plugin-group modules")
    return modules


def get_packages_in_package(basepackage):
    """Find, import and yield all packages below basepackage

    Args:
        basepackage: Where to look for other packages
    Yields:
        Yields all packages found below basepackage
    """
    for importer, modname, ispkg in pkgutil.iter_modules(basepackage.__path__):
        if ispkg:
            fullmodpath = basepackage.__name__ + "." + modname
            yield importer.find_module(modname).load_module(fullmodpath)


def get_modules_in_package(package, filter_cb=lambda n: True):
    """Get and load all modules in a package

    Args:
        package: Where to look for modules
        filter_cb: (Optional) callback to filter out modules to be loaded
                   the module name is passed to the cb, True indicates to load
                   the module.
    """
    if type(package) in [str, unicode]:
        package = pkgutil.get_loader(package).load_module(package)
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        if filter_cb(modname):
            fullmodpath = package.__name__ + "." + modname
            yield importer.find_module(modname).load_module(fullmodpath)
