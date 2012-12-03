#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# storage.py - Copyright (C) 2012 Red Hat, Inc.
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

from ovirt.node import base


class iSCSI(base.Base):
    """A class to deal with some external iSCSI related functionality
    """
    def initiator_name(self, initiator_name=None):
        import ovirtnode.iscsi as oiscsi
        if initiator_name:
            oiscsi.set_iscsi_initiator(initiator_name)
        return oiscsi.get_current_iscsi_initiator_name()


class NFSv4(base.Base):
    """A class to deal some external NFSv4 related functionality
    """
    def domain(self, domain=None):
        import ovirtnode.network as onet
        if domain:
            onet.set_nfsv4_domain(domain)
        return onet.get_current_nfsv4_domain()
