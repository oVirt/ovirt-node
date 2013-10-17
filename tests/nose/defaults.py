#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# defaults.py - Copyright (C) 2013 Red Hat, Inc.
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

from mock import patch

from ovirt.node.config.defaults import NodeConfigFileSection
from ovirt.node.utils import Transaction
from ovirt.node.utils.fs import FakeFs


class DummyNodeConfigFileSection(NodeConfigFileSection):
    keys = ("DUMMY_KEY",)
    txe_counter = 0

    @NodeConfigFileSection.map_and_update_defaults_decorator
    def update(self, key):
        pass

    def transaction(self, secret):
        tx = Transaction("Dummy TX")

        obj = self

        obj.secret = secret

        class DummyTXE(Transaction.Element):
            def commit(self):
                obj.txe_counter += 1

        tx.append(DummyTXE())

        return tx

    def configure_dummy(self):
        return self.update(key="default")


@patch("ovirt.node.utils.fs.File", FakeFs.File)
class TestSanity():
    """A class to test the basic features of the defaults module
    """

    defaults_file = FakeFs.File("/etc/default/ovirt")

    def setUp(self):
        FakeFs.erase()
        self.defaults_file.touch()
        logging.basicConfig()

    def test_chaining(self):
        cfg = DummyNodeConfigFileSection()

        cfg.update("bar").commit("secret")

        assert cfg.txe_counter == 1
        assert self.defaults_file.read() == 'DUMMY_KEY="bar"\n'
        assert cfg.secret == "secret"

        cfg.configure_dummy().commit("baz")

        assert cfg.txe_counter == 2
        assert cfg.secret == "baz"
        assert self.defaults_file.read() == 'DUMMY_KEY="default"\n'
