# Copyright (C) 2010, Red Hat, Inc.
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

PACKAGE           = ovirt-node-image
RECIPE            = $(PACKAGE).ks
PRODUCT           = oVirt Node Hypervisor
PRODUCT_SHORT     ?= $(PRODUCT)
PKG_FMT           = iso
FEDORA            = @FEDORA@
RHEL              = @RHEL@
DISTRO            = @DISTRO@
ARCH              = $(shell rpm --eval '%{_arch}')
NODE_CREATOR      = $(shell test -e node-creator && echo "./node-creator" || echo "/usr/sbin/node-creator")

FEDORA_MIRROR     = http://mirrors.fedoraproject.org/mirrorlist
OVIRT_URL		  = http://ovirt.org/releases/stable/fedora
CUR_RAWHIDE       = 17
CUR_DEVEL         = 17

OVIRT_NODE_TOOLSdir = $(datadir)/ovirt-node-tools
OVIRT_NODE_TOOLS_DATA =         \
        repos.ks                \
        *-install.ks     \
        *-pkgs.ks        \
        *-post.ks        \
        *-minimizer.ks   \
        common-nochroot.ks \
        common-manifest.ks \
        $(PACKAGE).ks

EXTRA_DIST =                    \
        *-install.ks     \
        *-pkgs.ks        \
        *-post.ks        \
        *-minimizer.ks   \
        common-nochroot.ks \
        common-manifest.ks \
        image-minimizer.ks.in   \
        $(PACKAGE).ks.in        \
        $(PACKAGE).ks

dist_sbin_SCRIPTS = node-creator

$(PACKAGE).ks: repos.ks version.ks

repos.ks:
	( \
	  if [ -n "$(FEDORA)" ]; then \
	    if [ 0$(FEDORA) == 0$(CUR_RAWHIDE) ]; then \
	        FEDORA_REPO=rawhide ;\
	        FEDORA_REPO_LOC="$(if $(FEDORA_URL),--baseurl=$(FEDORA_URL)/development/rawhide/$(ARCH)/os,--mirrorlist=$(FEDORA_MIRROR)?repo=rawhide&arch=$(ARCH))" ;\
			OVIRT_REPO_LINE="repo --name=ovirt-repo --baseurl=$(OVIRT_URL)/$(FEDORA)\n" ;\
	    elif [ 0$(FEDORA) == 0$(CUR_DEVEL) ]; then \
	        FEDORA_REPO=f$(FEDORA) ;\
	        FEDORA_REPO_LOC="$(if $(FEDORA_URL),--baseurl=$(FEDORA_URL)/development/$(FEDORA)/$(ARCH)/os,--mirrorlist=$(FEDORA_MIRROR)?repo=fedora-$(FEDORA)&arch=$(ARCH))" ;\
	        UPDATE_REPO_LINE="repo --name=$${FEDORA_REPO}-updates-testing $(if $(FEDORA_URL),--baseurl=$(FEDORA_URL)/updates/testing/$(FEDORA)/${ARCH},--mirrorlist=$(FEDORA_MIRROR)?repo=updates-testing-f$(FEDORA)&arch=$(ARCH))\n" ;\
			OVIRT_REPO_LINE="repo --name=ovirt-repo --baseurl=$(OVIRT_URL)/$(FEDORA)\n" ;\
	    else \
	        FEDORA_REPO=f$(FEDORA) ;\
	        FEDORA_REPO_LOC="$(if $(FEDORA_URL),--baseurl=$(FEDORA_URL)/releases/$(FEDORA)/Everything/${ARCH}/os,--mirrorlist=$(FEDORA_MIRROR)?repo=fedora-$(FEDORA)&arch=$(ARCH))" ;\
	        UPDATE_REPO_LINE="repo --name=$${FEDORA_REPO}-updates $(if $(FEDORA_URL),--baseurl=$(FEDORA_URL)/updates/$(FEDORA)/${ARCH},--mirrorlist=$(FEDORA_MIRROR)?repo=updates-released-f$(FEDORA)&arch=$(ARCH))\n" ;\
			OVIRT_REPO_LINE="repo --name=ovirt-repo --baseurl=$(OVIRT_URL)/$(FEDORA)\n" ;\
	    fi ;\
	    echo "repo --name=$${FEDORA_REPO} $${FEDORA_REPO_LOC}" > repos.ks ;\
	    printf "$${UPDATE_REPO_LINE}" >> repos.ks ;\
	    printf "$${OVIRT_REPO_LINE}" >> repos.ks ;\
	  else \
	    echo "# OVIRT_REPO_URL=$(OVIRT_REPO_URL)" > $@ ;\
	    for repo in $(OVIRT_REPO_URL); do \
	       echo "repo --name=repo$${i} --baseurl=$${repo}" >> $@ ;\
	       i=$${i}_ ;\
	    done ;\
	  fi ;\
	)

RELEASE := $(shell rpm -q --qf "%{RELEASE}\n" --specfile ../ovirt-node.spec | head -n1)
version.ks:
	( \
	    echo "PRODUCT='"$(PRODUCT)"'" ;\
	    echo "PRODUCT_SHORT='"$(PRODUCT_SHORT)"'" ;\
	    echo "PACKAGE=$(PACKAGE)" ;\
	    echo "VERSION=$(VERSION)" ;\
	    echo "RELEASE=$(RELEASE)" ;\
	) > $@

$(PACKAGE).$(PKG_FMT) node: version.ks
	$(NODE_CREATOR) $(RECIPE)

.PHONY: repos.ks version.ks $(PACKAGE).ks
