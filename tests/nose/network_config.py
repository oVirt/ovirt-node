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
import pprint

# http://ivory.idyll.org/articles/nose-intro.html


def patch_common(cls):
    @patch("ovirt.node.utils.fs.File", FakeFs.File)
    @patch("os.listdir", FakeFs.listdir)
    @patch("ovirt.node.utils.process.call")
    @patch.object(UdevNICInfo, "vendor")
    @patch.object(UdevNICInfo, "devtype")
    @patch.object(SysfsNICInfo, "hwaddr", "th:em:ac:ad:dr")
    class TestWrapperClass(cls):
        pass
    TestWrapperClass.__name__ = cls.__name__
    return TestWrapperClass


class TestFakeFs():
    def setUp(self):
        FakeFs.erase()

    def tearDown(self):
        FakeFs.erase()

    def test_basic(self):
        FakeFs.erase()
        with patch("ovirt.node.utils.fs.File", FakeFs.File):
            f = fs.File("new-file")
            f.touch()
            assert "new-file" in FakeFs.filemap

            f.delete()
            print FakeFs.filemap
            assert FakeFs.filemap == {}


@patch_common
class TestBridgedNIC():
    """Test the bridged/legacy configuration
    """
    def setUp(self):
        FakeFs.erase()
        FakeFs.File("/etc/default/ovirt").touch()

    def tearDown(self):
        FakeFs.erase()

    def test_dhcp(self, *args, **kwargs):
        m = defaults.Network()
        mt = defaults.NetworkLayout()

        mt.configure_bridged()
        m.configure_dhcp("eth0")

        run_tx_by_name(m.transaction(), "WriteConfiguration")

        assert ifcfg_has_items("eth0",
                               [('BRIDGE', 'breth0'), ('DEVICE', 'eth0'),
                                ('HWADDR', 'th:em:ac:ad:dr'),
                                ('ONBOOT', 'yes')])
        assert ifcfg_has_items("breth0",
                               [('BOOTPROTO', 'dhcp'), ('DELAY', '0'),
                                ('DEVICE', 'breth0'), ('ONBOOT', 'yes'),
                                ('PEERNTP', 'yes'), ('TYPE', 'Bridge')])

    def test_static(self, *args, **kwargs):
        m = defaults.Network()
        mt = defaults.NetworkLayout()

        mt.configure_bridged()
        m.configure_static("ens1", "192.168.122.42", "255.255.255.0",
                           "192.168.122.1", None)

        run_tx_by_name(m.transaction(), "WriteConfiguration")

        assert ifcfg_has_items("ens1",
                               [('BRIDGE', 'brens1'), ('DEVICE', 'ens1'),
                                ('HWADDR', 'th:em:ac:ad:dr'),
                                ('ONBOOT', 'yes')])
        assert ifcfg_has_items("brens1",
                               [('DELAY', '0'),
                                ('DEVICE', 'brens1'),
                                ('GATEWAY', '192.168.122.1'),
                                ('IPADDR', '192.168.122.42'),
                                ('NETMASK', '255.255.255.0'),
                                ('ONBOOT', 'yes'),
                                ('PEERNTP', 'yes'),
                                ('TYPE', 'Bridge')])


@patch_common
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
        mt = defaults.NetworkLayout()
        m = defaults.Network()

        mt.configure_direct()
        m.configure_dhcp("eth0")

        run_tx_by_name(m.transaction(), "WriteConfiguration")

        assert ifcfg_has_items("eth0",
                               [('BOOTPROTO', 'dhcp'), ('DEVICE', 'eth0'),
                               ('HWADDR', 'th:em:ac:ad:dr'), ('ONBOOT', 'yes'),
                               ('PEERNTP', 'yes')])

        assert "breth0" not in FakeFs.filemap

    def test_static(self, *args, **kwargs):
        """Test bridgeless with static IP configuration file creation
        """
        mt = defaults.NetworkLayout()
        m = defaults.Network()

        mt.configure_direct()
        m.configure_static("ens1", "192.168.122.42", "255.255.255.0",
                           "192.168.122.1", None)

        run_tx_by_name(m.transaction(), "WriteConfiguration")

        assert ifcfg_has_items("ens1",
                               [('DEVICE', 'ens1'),
                                ('GATEWAY', '192.168.122.1'),
                                ('HWADDR', 'th:em:ac:ad:dr'),
                                ('IPADDR', '192.168.122.42'),
                                ('NETMASK', '255.255.255.0'),
                                ('ONBOOT', 'yes'),
                                ('PEERNTP', 'yes')])

        assert "brens1" not in FakeFs.filemap


@patch_common
class TestBond():
    """Test bonding configuration
    """
    def setUp(self):
        FakeFs.erase()
        FakeFs.File("/etc/default/ovirt").touch()

    def tearDown(self):
        FakeFs.erase()

    def test_direct_dhcp(self, *args, **kwargs):
        mb = defaults.NicBonding()
        mt = defaults.NetworkLayout()
        m = defaults.Network()

        mb.configure_8023ad("bond0", ["ens1", "ens2", "ens3"])
        m.configure_dhcp("bond0")
        mt.configure_direct()

        run_tx_by_name(m.transaction(), "WriteConfiguration")

        assert ifcfg_has_items("bond0",
                               [('BONDING_OPTS', 'mode=4'),
                                ('BOOTPROTO', 'dhcp'),
                                ('DEVICE', 'bond0'),
                                ('HWADDR', 'th:em:ac:ad:dr'),
                                ('ONBOOT', 'yes'), ('PEERNTP', 'yes')])

        assert ifcfg_has_items("ens1",
                               [('DEVICE', 'ens1'), ('MASTER', 'bond0'),
                                ('ONBOOT', 'yes'), ('SLAVE', 'yes')])

        assert ifcfg_has_items("ens2",
                               [('DEVICE', 'ens2'), ('MASTER', 'bond0'),
                                ('ONBOOT', 'yes'), ('SLAVE', 'yes')])

        assert ifcfg_has_items("ens3",
                               [('DEVICE', 'ens3'), ('MASTER', 'bond0'),
                                ('ONBOOT', 'yes'), ('SLAVE', 'yes')])

        assert len(FakeFs.filemap) == (1 + 1 + 3)

    def test_bridged_dhcp(self, *args, **kwargs):
        mb = defaults.NicBonding()
        mt = defaults.NetworkLayout()
        m = defaults.Network()

        mb.configure_8023ad("bond0", ["ens1", "ens2", "ens3"])
        m.configure_dhcp("bond0")
        mt.configure_bridged()

        run_tx_by_name(m.transaction(), "WriteConfiguration")

        assert ifcfg_has_items("bond0",
                               [('BONDING_OPTS', 'mode=4'),
                                ('BRIDGE', 'brbond0'),
                                ('DEVICE', 'bond0'),
                                ('HWADDR', 'th:em:ac:ad:dr'),
                                ('ONBOOT', 'yes')])

        assert ifcfg_has_items("ens1",
                               [('DEVICE', 'ens1'), ('MASTER', 'bond0'),
                                ('ONBOOT', 'yes'), ('SLAVE', 'yes')])

        assert ifcfg_has_items("ens2",
                               [('DEVICE', 'ens2'), ('MASTER', 'bond0'),
                                ('ONBOOT', 'yes'), ('SLAVE', 'yes')])

        assert ifcfg_has_items("ens3",
                               [('DEVICE', 'ens3'), ('MASTER', 'bond0'),
                                ('ONBOOT', 'yes'), ('SLAVE', 'yes')])

        assert ifcfg_has_items("brbond0",
                               [('BONDING_OPTS', 'mode=4'),
                                ('BOOTPROTO', 'dhcp'),
                                ('DELAY', '0'),
                                ('DEVICE', 'brbond0'),
                                ('ONBOOT', 'yes'),
                                ('PEERNTP', 'yes'),
                                ('TYPE', 'Bridge')])

        assert len(FakeFs.filemap) == (1 + 1 + 3 + 1)

    def test_bond_slave_as_primary(self, *args, **kwargs):
        mb = defaults.NicBonding()
        m = defaults.Network()

        # ens1 is used as a slave, but then also as a primary device
        # this doesn't work
        mb.configure_8023ad("bond0", ["ens1", "ens2", "ens3"])
        m.configure_dhcp("ens1")

        had_exception = False
        try:
            run_tx_by_name(m.transaction(), "WriteConfiguration")
        except RuntimeError as e:
            had_exception = True
            assert e.message == ("Bond slave can not be used as " +
                                 "primary device")
        assert had_exception

    def test_unused_bond(self, *args, **kwargs):
        mb = defaults.NicBonding()
        m = defaults.Network()

        # bond0 is created, but ens42 is used
        mb.configure_8023ad("bond0", ["ens1", "ens2", "ens3"])
        m.configure_dhcp("ens42")

        try:
            run_tx_by_name(m.transaction(), "WriteConfiguration")
        except RuntimeError as e:
            assert e.message == "Bond configured but not used"

    def test_no_bond_and_clean(self, *args, **kwargs):
        mb = defaults.NicBonding()

        self.test_unused_bond()

        # bond0 is created, but ens42 is used
        mb.configure_no_bond()
        mb.transaction().run()

        pprint.pprint(FakeFs.filemap)

        assert ifcfgfilename("bond0") not in FakeFs.filemap
        assert ifcfg_has_items("ens1", [('DEVICE', 'ens1'),
                                        ('ONBOOT', 'yes')])
        assert ifcfg_has_items("ens2", [('DEVICE', 'ens2'),
                                        ('ONBOOT', 'yes')])
        assert ifcfg_has_items("ens3", [('DEVICE', 'ens3'),
                                        ('ONBOOT', 'yes')])


def run_tx_by_name(txs, name):
    """Run a Transaction.Element by it's classname
    """
    tx = None
    for _tx in txs:
        if _tx.__class__.__name__ == name:
            tx = _tx
            break
    assert tx
    tx()


def ifcfgfilename(ifname):
    """Return the path to an ifcfg file usign the ifname
    """
    return "/etc/sysconfig/network-scripts/ifcfg-" + ifname


def ifcfg_has_items(ifname, expected_items):
    """Check if the items in an ifcfg file are equal the expected_items
    """
    ifcfg = ShellVarFile(ifcfgfilename(ifname))
    ifcfg_items = sorted(ifcfg.get_dict().items())
    logging.info("ifcfg : %s" % ifname)
    logging.info("expect: %s" % expected_items)
    logging.info("got   : %s" % ifcfg_items)
    return ifcfg_items == expected_items
