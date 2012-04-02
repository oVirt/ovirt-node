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

OVIRT_CACHE_DIR	?= $(HOME)/ovirt-cache

SUBDIRS =   \
  dracut \
  images \
  kinit \
  recipe \
  scripts \
  tools

EXTRA_DIST = \
  ovirt-qla4xxx.conf \
  vlan.modules \
  libvirtd.service \
  libvirtd.upstart \
  ovirt-node.spec \
  ovirt-node.spec.in \
  logrotate/ovirt-logrotate \
  logrotate/ovirt-logrotate.conf

DISTCLEANFILES = $(PACKAGE)-$(VERSION).tar.gz

# For Release: 0..., set _ovirt_dev=1 so that we get extra_release.GIT-
# annotated rpm version strings.
_ovirt_dev = \
 $(shell grep -q '^[[:space:]]*Release:[[:space:]]*999' \
   $(srcdir)/*.spec.in && echo 1 || :)

git_head	= $$(git log -1 --pretty=format:%h)
GIT_RELEASE	= $$(date --utc +%Y%m%d%H%M%S)git$(git_head)
RPMDIR		= $$(rpm --eval '%{_rpmdir}')
RPM_FLAGS	= --define "ovirt_cache_dir $(OVIRT_CACHE_DIR)"
RPM_FLAGS	+= $(if $(_ovirt_dev),--define "extra_release .$(GIT_RELEASE)")

rpms: dist
	rpmbuild $(RPM_FLAGS) -ta $(distdir).tar.gz

srpms: dist
	rpmbuild $(RPM_FLAGS) -ts $(distdir).tar.gz

publish: rpms
	mkdir -p $(OVIRT_CACHE_DIR)
	rsync -aq $(shell rpm --eval '%{_rpmdir}')/ $(OVIRT_CACHE_DIR)/ovirt/
	rsync -aq $(shell rpm --eval '%{_srcrpmdir}')/ $(OVIRT_CACHE_DIR)/ovirt/src
	createrepo $(OVIRT_CACHE_DIR)/ovirt

iso: publish
	cd recipe
	make node

.PHONY: rpms publish srpms
