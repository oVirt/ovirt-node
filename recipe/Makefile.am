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
PKG_FMT           = iso

FEDORA_MIRROR     = http://mirrors.fedoraproject.org/mirrorlist
CUR_RAWHIDE       = 16
CUR_DEVEL         = 15
CUR_PREVIEW       = 12
PREVIEW_URL       ?= http://jforbes.fedorapeople.org/virt-preview/f$(CUR_PREVIEW)/$(ARCH)

FEDORA            = $(shell rpm --eval '%{fedora}' |grep [0-9])
ARCH              = $(shell rpm --eval '%{_arch}')

AUTH_KEYS         ?= $(HOME)/.ssh/authorized_keys

OVIRT_NODE_TOOLSdir = $(datadir)/ovirt-node-tools
OVIRT_NODE_TOOLS_DATA =         \
        repos.ks                \
        common-blacklist.ks     \
        common-manifest-post.ks \
        common-install.ks       \
        common-minimizer.ks     \
        common-el6.ks           \
        common-pkgs.ks          \
        common-post.ks          \
        common-post-nochroot.ks \
        $(PACKAGE).ks

EXTRA_DIST =                    \
        common-blacklist.ks     \
        common-manifest-post.ks \
        common-install.ks       \
        common-minimizer.ks     \
        common-el6.ks           \
        common-pkgs.ks          \
        common-post.ks          \
        common-post-nochroot.ks \
        $(PACKAGE).ks

dist_sbin_SCRIPTS = node-creator

repos.ks:
	( \
	  if [ -n "$(FEDORA)" ]; then \
	    if [ 0$(FEDORA) == 0$(CUR_RAWHIDE) ]; then \
	        FEDORA_REPO=rawhide ;\
	        FEDORA_REPO_LOC="$(if $(FEDORA_URL),--baseurl=$(FEDORA_URL)/development/rawhide/$(ARCH)/os,--mirrorlist=$(FEDORA_MIRROR)?repo=rawhide&arch=$(ARCH))" ;\
	    elif [ 0$(FEDORA) == 0$(CUR_DEVEL) ]; then \
	        FEDORA_REPO=f$(FEDORA) ;\
	        FEDORA_REPO_LOC="$(if $(FEDORA_URL),--baseurl=$(FEDORA_URL)/development/$(FEDORA)/$(ARCH)/os,--mirrorlist=$(FEDORA_MIRROR)?repo=fedora-$(FEDORA)&arch=$(ARCH))" ;\
	    else \
	        FEDORA_REPO=f$(FEDORA) ;\
	        FEDORA_REPO_LOC="$(if $(FEDORA_URL),--baseurl=$(FEDORA_URL)/releases/$(FEDORA)/Everything/${ARCH}/os,--mirrorlist=$(FEDORA_MIRROR)?repo=fedora-$(FEDORA)&arch=$(ARCH))" ;\
	        UPDATE_REPO_LINE="repo --name=$${FEDORA_REPO}-updates $(if $(FEDORA_URL),--baseurl=$(FEDORA_URL)/updates/$(FEDORA)/${ARCH},--mirrorlist=$(FEDORA_MIRROR)?repo=updates-released-f$(FEDORA)&arch=$(ARCH))\n" ;\
	        if [ 0$(FEDORA)remove == 0$(CUR_PREVIEW)me ]; then \
	            UPDATE_REPO_LINE="$${UPDATE_REPO_LINE}repo --name=preview --baseurl=$(PREVIEW_URL)\n" ;\
	        fi ;\
	    fi ;\
	    echo "repo --name=$${FEDORA_REPO} $${FEDORA_REPO_LOC}" > repos.ks ;\
	    printf "$${UPDATE_REPO_LINE}" >> repos.ks ;\
	  else \
	    echo "repo --name=dist-ovirt --baseurl=$(OVIRT_REPO_URL)" > $@ ;\
	  fi ;\
	)

keys:
	if [ "$(_ovirt_dev)" = 1 -a -f $(AUTH_KEYS) ]; then \
	    cp -va $(AUTH_KEYS) ovirt-authorized_keys ;\
	fi

# For Release: 0..., set _ovirt_dev=1 so that we get extra_release.GIT-
# annotated rpm version strings.
_ovirt_dev = \
 $(shell grep -q '^[[:space:]]*Release:[[:space:]]*0' \
   $(top_srcdir)/*.spec.in && echo 1 || :)

version.ks:
	( \
	    echo "PRODUCT='"$(PRODUCT)"'" ;\
	    echo "PACKAGE=$(PACKAGE)" ;\
	    echo "VERSION=$(VERSION)" ;\
	    echo "RELEASE=$(RELEASE)" ;\
	) > $@

$(PACKAGE).$(PKG_FMT) node: version.ks
	node-creator $(RECIPE)

.PHONY: repos.ks version.ks
