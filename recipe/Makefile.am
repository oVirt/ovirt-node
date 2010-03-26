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

FEDORA_MIRROR     = http://mirrors.fedoraproject.org/mirrorlist
CUR_RAWHIDE       = 14
CUR_DEVEL         = 13
CUR_PREVIEW       = 12
PREVIEW_URL       ?= http://jforbes.fedorapeople.org/virt-preview/f$(CUR_PREVIEW)/$(ARCH)
OVIRT_REPO_URL    ?= http://ovirt.org/repos/ovirt/$(FEDORA)/$(ARCH)

FEDORA            = $(shell rpm --eval '%{fedora}')
ARCH              = $(shell rpm --eval '%{_arch}')
OVIRT_NODE_RECIPE = ovirt-node-recipe.ks
PKG_FMT           = iso
PACKAGE           = ovirt-node-image
OVIRT_CACHE_DIR   ? =$(HOME)/ovirt-cache
NODE_TMP          = $(OVIRT_CACHE_DIR)/$(PACKAGE)-$(ARCH)-tmp
OVIRT_LOCAL_REPO  ?= file://$(OVIRT_CACHE_DIR)/ovirt
NODE_KS           = $(NODE_TMP)/node.ks
NVR               = $(PACKAGE)-$(VERSION)-$(ARCH)
SUM               ?= sha1sum
AUTH_KEYS         ?= $(HOME)/.ssh/authorized_keys

OVIRT_NODE_TOOLSdir = $(datadir)/ovirt-node-tools
OVIRT_NODE_TOOLS_DATA = 	\
        repos.ks        	\
        common-blacklist.ks     \
        common-install.ks       \
        common-pkgs.ks  	\
        common-post.ks  	\
        ovirt-node-image.ks	\
        ovirt-node-recipe.ks

EXTRA_DIST= 			\
	common-blacklist.ks	\
	common-install.ks	\
	common-pkgs.ks		\
	common-post.ks		\
	ovirt-node-image.ks

repos.ks:
	( \
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
	    UPDATE_REPO_LINE="$${UPDATE_REPO_LINE}repo --name=ovirt --baseurl=$(OVIRT_REPO_URL)\n" ;\
	    echo "repo --name=$${FEDORA_REPO} $${FEDORA_REPO_LOC}" > repos.ks ;\
	    printf "$${UPDATE_REPO_LINE}" >> repos.ks ;\
	)

ovirt-node-recipe.ks:
	ksflatten ovirt-node-image.ks --output $@
# XXX broken ksflatten leaves %include
	sed -i 's/^%include /#&/' $@

keys:
	if [ "$(_ovirt_dev)" = 1 -a -f $(AUTH_KEYS) ]; then \
	    cp -va $(AUTH_KEYS) ovirt-authorized_keys ;\
	fi

no_nscd:
	if pgrep -xl nscd; then \
	    echo "Please stop nscd" ;\
	    exit 1 ;\
	fi

# For Release: 0..., set _ovirt_dev=1 so that we get extra_release.GIT-
# annotated rpm version strings.
_ovirt_dev = \
 $(shell grep -q '^[[:space:]]*Release:[[:space:]]*0' \
   $(top_srcdir)/*.spec.in && echo 1 || :)

SELINUX_ENFORCING=$(shell /usr/sbin/getenforce)
$(NVR).$(PKG_FMT): no_nscd keys
	mkdir -p $(NODE_TMP)
	mkdir -p $(OVIRT_CACHE_DIR)/yum-$(ARCH)
	( \
	    case $(SELINUX_ENFORCING) in \
		Enforcing) sudo /usr/sbin/setenforce Permissive ;; \
		Permissive) ;; \
		*) if grep -q '^selinux --disabled' $(OVIRT_NODE_RECIPE); \
		   then \
		       echo WARNING: SELinux disabled in kickstart ;\
		   else \
		       echo ERROR: SELinux enabled in kickstart, \
		       but disabled on the build machine ;\
		       exit 1 ;\
		   fi ;; \
	    esac ;\
	)
	rm -f $(NODE_KS)
	if [ "$(_ovirt_dev)" = 1 ]; then \
	    echo "repo --name=ovirt-local --baseurl=$(OVIRT_LOCAL_REPO)" > $(NODE_KS) ;\
	fi
	cat $(OVIRT_NODE_RECIPE) >> $(NODE_KS)
	sudo livecd-creator --skip-minimize -c  $(NODE_KS)\
	    -f $(PACKAGE) \
	    --tmpdir='$(NODE_TMP)' \
	    --cache='$(OVIRT_CACHE_DIR)/yum-$(ARCH)'
	sudo chown $${USER} $(PACKAGE).$(PKG_FMT)
	( \
	    if [ $(SELINUX_ENFORCING) = Enforcing ]; then \
		sudo /usr/sbin/setenforce Enforcing || exit 1 ;\
	    fi \
	)

	ln -nf $(PACKAGE).$(PKG_FMT) $(NVR).$(PKG_FMT)

$(NVR).$(PKG_FMT).$(SUM): $(NVR).$(PKG_FMT)
	$(SUM) $(NVR).$(PKG_FMT) > $(NVR).$(PKG_FMT).$(SUM)

$(PACKAGE).$(PKG_FMT) node: ovirt-node-recipe.ks $(NVR).$(PKG_FMT).$(SUM)

PUNGI = $(NODE_TMP)/tree/pungi

.PHONY: ovirt-node-recipe.ks repos.ks
