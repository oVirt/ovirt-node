#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# network_config.py - Copyright (C) 2013 Red Hat, Inc.
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
from mock import patch
from ovirt.node.config import defaults
from ovirt.node.utils import fs
from ovirt.node.utils.fs import ShellVarFile
from ovirt.node.utils.network import UdevNICInfo, SysfsNICInfo
import StringIO
import os
import tempfile
import logging

# http://ivory.idyll.org/articles/nose-intro.html

class MemFile(StringIO.StringIO):
    def contents(self):
        self.seek(0)
        return self.read()

    def clear(self):
        self.truncate(0)

def test_memfile():
    val = "Ha!"
    f = MemFile()
    f.write(val)
    assert f.contents() == val

    f.clear()
    assert f.contents() == ""


class TemporaryChroot(object):
    old_cwd = None
    old_fd = None
    tmpdir = None

    def __init__(self, remove=True):
        self.remove = remove

    def __enter__(self):
        self.old_cwd = os.getcwd()
        self.old_fd = os.open(self.old_cwd, os.O_DIRECTORY)
        self.tmpdir = tempfile.mkdtemp()
        logging.info("TemporaryChroot in %s" % self.tmpdir)
        os.chroot(self.tmpdir)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for _ in range(1024):
            os.chdir('..')
        os.chroot(".")
        os.fchdir(self.old_fd)
        os.close(self.old_fd)
        if self.remove:
            os.removedirs(self.tmpdir)


def test_bridged_w_dhcp():
    """Test BridgedNIC with DHCP
    """
    with TemporaryChroot(remove=False):
        # FIXME I'd actually like to get rid of the chroot

        # Prepare fs layout
        os.makedirs("/etc/default")
        os.makedirs("/etc/sysconfig/network-scripts")
        fs.truncate(defaults.OVIRT_NODE_DEFAULTS_FILENAME)

        # Write default file through model
        m = defaults.Network()
        m.configure_dhcp("eth0")

        @patch.object(UdevNICInfo, "vendor")
        @patch.object(UdevNICInfo, "devtype")
        @patch.object(SysfsNICInfo, "hwaddr", "th:em:ac:ad:dr")
        def func(*args):
            txs = m.transaction()
            for tx in txs:
                if tx.__class__.__name__ == "WriteConfiguration":
                    tx()
        func()

        assert_ifcfg_has_items("eth0",
                                [('BRIDGE', 'breth0'), ('DEVICE', 'eth0'),
                                 ('HWADDR', 'th:em:ac:ad:dr'),
                                 ('ONBOOT', 'yes')])

        assert_ifcfg_has_items("breth0",
                                [('BOOTPROTO', 'dhcp'), ('DELAY', '0'),
                                 ('DEVICE', 'breth0'), ('ONBOOT', 'yes'),
                                 ('PEERNTP', 'yes'), ('TYPE', 'Bridge')])

def assert_ifcfg_has_items(ifname, expected_items):
    ifcfg = ShellVarFile("/etc/sysconfig/network-scripts/ifcfg-" + ifname)
    ifcfg_items = sorted(ifcfg.get_dict().items())
    logging.info("ifcfg : %s" % ifname)
    logging.info("expect: %s" % expected_items)
    logging.info("got   : %s" % ifcfg_items)
    assert ifcfg_items == expected_items
