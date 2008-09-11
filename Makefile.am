# Copyright (C) 2008 Red Hat, Inc.
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

SUBDIRS = ovirt-identify-node ovirt-listen-awake

EXTRA_DIST =			\
  .gitignore			\
  ovirt-node.spec		\
  release.mk			\
  version			\
  scripts/collectd		\
  scripts/collectd.conf.in	\
  scripts/dhclient-exit-hooks	\
  scripts/kvm-ifup		\
  scripts/ovirt			\
  scripts/ovirt-awake		\
  scripts/ovirt-early		\
  scripts/ovirt-functions	\
  scripts/ovirt-post		\
  logrotate/ovirt-logrotate	\
  logrotate/ovirt-logrotate.conf

include release.mk

pkg_name = $(PACKAGE_NAME)
.PHONY: tar
tar: dist
	mkdir -p rpm-build/BUILDROOT
	cp version $(distdir).tar.gz rpm-build
