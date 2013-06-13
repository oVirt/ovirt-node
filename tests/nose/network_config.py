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
from ovirt.node.utils.fs import ShellVarFile, FakeFs
from ovirt.node.utils.network import UdevNICInfo, SysfsNICInfo
import logging

# http://ivory.idyll.org/articles/nose-intro.html


class TestFakeFs():
    def setUp(self):
        FakeFs.erase()

    def tearDown(self):
        FakeFs.erase()

    def test_basic(self):
        """Ensure that FakeFs is working
        """
        FakeFs.erase()
        with patch("ovirt.node.utils.fs.File", FakeFs.File):
            f = fs.File("new-file")
            f.touch()
            assert "new-file" in FakeFs.filemap

            f.delete()
            print FakeFs.filemap
            assert FakeFs.filemap == {}


@patch("ovirt.node.utils.fs.File", FakeFs.File)
@patch.object(UdevNICInfo, "vendor")
@patch.object(UdevNICInfo, "devtype")
@patch.object(SysfsNICInfo, "hwaddr", "th:em:ac:ad:dr")
class TestBridgedNIC():
    """Test the bridged/legacy configuration
    """
    def setUp(self):
        FakeFs.erase()
        FakeFs.File("/etc/default/ovirt").touch()

    def tearDown(self):
        FakeFs.erase()

    def test_dhcp(self, *args, **kwargs):
        """Test BridgedNIC with DHCP configuration file creation
        """
        m = defaults.Network()

        m.configure_dhcp("eth0")

        run_tx_by_name(m.transaction(), "WriteConfiguration")

        assert_ifcfg_has_items("eth0",
                               [('BRIDGE', 'breth0'), ('DEVICE', 'eth0'),
                                ('HWADDR', 'th:em:ac:ad:dr'),
                                ('ONBOOT', 'yes')])
        assert_ifcfg_has_items("breth0",
                               [('BOOTPROTO', 'dhcp'), ('DELAY', '0'),
                                ('DEVICE', 'breth0'), ('ONBOOT', 'yes'),
                                ('PEERNTP', 'yes'), ('TYPE', 'Bridge')])

    def test_static(self, *args, **kwargs):
        """Test BridgedNIC with static IP configuration file creation
        """
        m = defaults.Network()

        m.configure_static("ens1", "192.168.122.42", "255.255.255.0",
                           "192.168.122.1", None)

        run_tx_by_name(m.transaction(), "WriteConfiguration")

        assert_ifcfg_has_items("ens1",
                               [('BRIDGE', 'brens1'), ('DEVICE', 'ens1'),
                                ('HWADDR', 'th:em:ac:ad:dr'),
                                ('ONBOOT', 'yes')])
        assert_ifcfg_has_items("brens1",
                               [('DELAY', '0'),
                                ('DEVICE', 'brens1'),
                                ('GATEWAY', '192.168.122.1'),
                                ('IPADDR', '192.168.122.42'),
                                ('NETMASK', '255.255.255.0'),
                                ('ONBOOT', 'yes'),
                                ('PEERNTP', 'yes'),
                                ('TYPE', 'Bridge')])


@patch("ovirt.node.utils.fs.File", FakeFs.File)
@patch.object(UdevNICInfo, "vendor")
@patch.object(UdevNICInfo, "devtype")
@patch.object(SysfsNICInfo, "hwaddr", "th:em:ac:ad:dr")
class TestDirectNIC():
    """Test the bridgeless configuration
    """
    def setUp(self):
        FakeFs.erase()
        FakeFs.File("/etc/default/ovirt").touch()

    def tearDown(self):
        FakeFs.erase()

    def test_dhcp(self, *args, **kwargs):
        """Test bridgeless with DHCP configuration file creation
        """
        mt = defaults.NetworkTopology()
        mt.configure_direct()

        m = defaults.Network()

        m.configure_dhcp("eth0")

        run_tx_by_name(m.transaction(), "WriteConfiguration")

        assert_ifcfg_has_items("eth0",
                               [('BOOTPROTO', 'dhcp'), ('DEVICE', 'eth0'),
                               ('HWADDR', 'th:em:ac:ad:dr'), ('ONBOOT', 'yes'),
                               ('PEERNTP', 'yes')])

        assert "breth0" not in FakeFs.filemap

    def test_static(self, *args, **kwargs):
        """Test bridgeless with static IP configuration file creation
        """
        mt = defaults.NetworkTopology()
        mt.configure_direct()

        m = defaults.Network()

        m.configure_static("ens1", "192.168.122.42", "255.255.255.0",
                           "192.168.122.1", None)

        run_tx_by_name(m.transaction(), "WriteConfiguration")

        assert_ifcfg_has_items("ens1",
                               [('DEVICE', 'ens1'),
                                ('GATEWAY', '192.168.122.1'),
                                ('HWADDR', 'th:em:ac:ad:dr'),
                                ('IPADDR', '192.168.122.42'),
                                ('NETMASK', '255.255.255.0'),
                                ('ONBOOT', 'yes'),
                                ('PEERNTP', 'yes')])

        assert "brens1" not in FakeFs.filemap


def run_tx_by_name(txs, name):
    tx = None
    for _tx in txs:
        if _tx.__class__.__name__ == name:
            tx = _tx
            break
    assert tx
    tx()


def assert_ifcfg_has_items(ifname, expected_items):
    ifcfg = ShellVarFile("/etc/sysconfig/network-scripts/ifcfg-" + ifname)
    ifcfg_items = sorted(ifcfg.get_dict().items())
    logging.info("ifcfg : %s" % ifname)
    logging.info("expect: %s" % expected_items)
    logging.info("got   : %s" % ifcfg_items)
    assert ifcfg_items == expected_items
