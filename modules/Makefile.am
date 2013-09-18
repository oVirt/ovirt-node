# Copyright (C) 2012 Red Hat, Inc.
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

modulesdir=$(sysconfdir)/sysconfig/modules
modprobedir=$(sysconfdir)/modprobe.d

# load vlan module
dist_modules_SCRIPTS = \
  vlan.modules

# qla4xxx iscsi hba workaround: rhbz#742433#c32
dist_modprobe_DATA = \
  ovirt-qla4xxx.conf \
  bonding.conf

# vim: ts=2
