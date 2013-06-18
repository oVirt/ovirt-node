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

systemunitdir=$(prefix)/lib/systemd/system
initddir=$(sysconfdir)/rc.d/init.d

if TARGET_SYSTEMD
dist_systemunit_DATA = \
  ovirt-awake.service \
  ovirt-early.service \
  ovirt.service \
  ovirt-post.service \
  ovirt-firstboot.service \
  ovirt-cim.service \
  ovirt-kdump.service \
  ovirt-node-igor-slave.service
else
dist_initd_SCRIPTS = \
  init.d/ovirt-awake \
  init.d/ovirt-early \
  init.d/ovirt-kdump \
  init.d/ovirt \
  init.d/ovirt-post \
  init.d/ovirt-firstboot \
  init.d/ovirt-cim \
  init.d/ovirt-node-igor-slave
endif

# vim: ts=2
