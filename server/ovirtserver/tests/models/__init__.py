# Copyright (C) 2010, Red Hat, Inc.
# Written by Darryl L. Pierce
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""Unit test suite for the models of the application."""
from nose.tools import assert_equals

from ovirtserver.model import DBSession
from ovirtserver.tests import setup_db, teardown_db

__all__ = ['ModelTest']

#Create an empty database before we start our tests for this module
def setup():
    """Function called by nose on module load"""
    setup_db()

#Teardown that database
def teardown():
    """Function called by nose after all tests in this module ran"""
    teardown_db()

class ModelTest(object):
    """Base unit test case for the models."""

    klass = None
    attrs = {}

    def setup(self):
        try:
            new_attrs = {}
            new_attrs.update(self.attrs)
            new_attrs.update(self.do_get_dependencies())
            self.obj = self.klass(**new_attrs)
            DBSession.add(self.obj)
            DBSession.flush()
            return self.obj
        except:
            DBSession.rollback()
            raise

    def tearDown(self):
        DBSession.rollback()

    def do_get_dependencies(self):
        """Use this method to pull in other objects that need to be created for this object to be build properly"""
        return {}

    def test_create_obj(self):
        pass

    def test_query_obj(self):
        obj = DBSession.query(self.klass).one()
        for key, value in self.attrs.iteritems():
            assert_equals(getattr(obj, key), value)
