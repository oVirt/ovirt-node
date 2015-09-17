#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# hooks.py - Copyright (C) 2014 Red Hat, Inc.
# Written by Ryan Barry <rbarry@redhat.com>
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
Manage running installer hooks
"""
import logging
import os

from ovirt.node import base
from ovirt.node.utils import process

LOGGER = logging.getLogger(__name__)


class Hooks(base.Base):
    """A utility class which executes files for additional configuration
    beyond the normal install
    """

    known = ["pre-upgrade", "post-upgrade", "rollback", "on-boot",
             "on-changed-boot-image"]

    legacy_hooks_directory = "/etc/ovirt-config-boot.d/"
    hooks_path_tpl = "/usr/libexec/ovirt-node/hooks/{name}"

    @staticmethod
    def post_auto_install():
        Hooks.__run(Hooks.legacy_hooks_directory)

    @staticmethod
    def emit(name):
        """Signal that a specific event appeared, and trigger the hook handlers

        Args:
            name: Name of the hook (bust be in Hooks.known)
        """
        assert name in Hooks.known
        path = Hooks.hooks_path_tpl.format(name=name)
        Hooks.__run(path)

    @staticmethod
    def __run(hooks_directory):
        for hook in os.listdir(hooks_directory):
            script = os.path.join(hooks_directory, hook)

            if script.endswith(".pyc") or script.endswith(".pyo"):
                continue

            LOGGER.debug("Running hook %s" % script)
            if script.endswith(".py"):
                output = process.check_output(["python", script])
            else:
                output = process.check_output("%s &> /dev/null" % script,
                                              shell=True)

            [LOGGER.debug("%s: %s" % (script, line)) for line in output]
