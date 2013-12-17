#!/usr/bin/python
# puppet_autoinstall.py - Copyright (C) 2013 Red Hat, Inc.
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

from ovirt.node.setup.puppet.puppet_page import *
import ovirtnode.ovirtfunctions as _functions
from ovirt.node.plugins import Changeset
import re

args = _functions.get_cmdline_args()
keys = ["puppet_enabled", "puppet_server", "puppet_certname"]
changes = dict((re.sub(r'_', r'.', key), args[key]) for key in keys
               if key in args)
cfg = Puppet().retrieve()
effective_model = Changeset({
    "puppet.enabled": True if cfg["enabled"] else False,
    "puppet.server": cfg["server"] or "puppet",
    "puppet.certname": cfg["certname"] or socket.gethostname()
})
if changes:
    effective_model.update(changes)
    real_keys = [re.sub(r'_', r'.', key) for key in keys]
    Puppet().update(*effective_model.values_for(real_keys))
if "puppet_enabled" in args and (re.compile(r'y', re.I).match(args[
        "puppet_enabled"]) or args["puppet_enabled"] == "1"):
        ActivatePuppet().enable_puppet()
