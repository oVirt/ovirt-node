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

SHELL := /bin/bash

SUBDIRS =   \
  data \
  dracut \
  images \
  recipe \
  scripts \
  src \
  services \
  logrotate \
  plugins \
  modules \
  registration \
  tools \
  tests

EXTRA_DIST = \
  ovirt-node.spec \
  ovirt-node.spec.in \
  semodule

DISTCLEANFILES = $(PACKAGE)-$(VERSION).tar.gz

TMPREPOS = tmp.repos
RPMBUILD_ARGS :=
RPMBUILD_ARGS += --define "ovirt_cache_dir $(OVIRT_CACHE_DIR)"
RPMBUILD_ARGS += --define="_topdir `pwd`/$(TMPREPOS)"
RPMBUILD_ARGS += $(if $(RELEASE_SUFFIX), --define="release_suffix $$RELEASE_SUFFIX")

srpm:	dist
	rm -fr "$(TMPREPOS)"
	mkdir -p $(TMPREPOS)/{SPECS,RPMS,SRPMS,SOURCES}
	$(RPMBUILD) $(RPMBUILD_ARGS) -ts "$(PACKAGE_TARNAME)-$(PACKAGE_VERSION).tar.gz"
	@echo
	@echo "srpm available at '$(TMPREPOS)'"
	@echo

rpm:	srpm
	$(RPMBUILD) $(RPMBUILD_ARGS) --rebuild "$(TMPREPOS)"/SRPMS/*.src.rpm
	@echo
	@echo "rpm(s) available at '$(TMPREPOS)'"
	@echo

publish:
	$(MAKE) rpm
	$(MAKE) create-repo

create-repo:
	mkdir -p $(OVIRT_CACHE_DIR)
	rsync -aq $(TMPREPOS)/ $(OVIRT_CACHE_DIR)/ovirt
	createrepo $(OVIRT_CACHE_DIR)/ovirt

iso: publish
	cd recipe
	make node

.PHONY: rpms publish srpms


check-local: static-checks unittests
	@echo Passed $@

static-checks:
	$(MAKE) -C src/ check-local

unittests:
	$(MAKE) -C tests/ check-local

snapshot-rpm:
	make rpm RELEASE_SUFFIX=".$$(date --utc +%Y%m%d).git$$(git rev-parse --short HEAD)"

snapshot:
	eval export $$(grep ^PACKAGE_ configure) ; \
	git archive \
		-o $$PACKAGE_NAME-$$PACKAGE_VERSION.$$(date +%Y%m%d)git$$(git log -n1 --format=%h).tar \
		--format=tar \
		--prefix=$$PACKAGE_NAME-$$PACKAGE_VERSION/ master

# vim: ts=2
