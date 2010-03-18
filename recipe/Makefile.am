FEDORA_MIRROR     = http://mirrors.fedoraproject.org/mirrorlist
CUR_RAWHIDE       = 14
CUR_DEVEL         = 13
CUR_PREVIEW       = 12
PREVIEW_URL      ?= http://jforbes.fedorapeople.org/virt-preview/f$(CUR_PREVIEW)/$(ARCH)

FEDORA            = $(shell rpm --eval '%{fedora}')
ARCH              = $(shell rpm --eval '%{_arch}')

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
	        if [ 0$(FEDORA) == 0$(CUR_PREVIEW) ]; then \
	            UPDATE_REPO_LINE="$${UPDATE_REPO_LINE}repo --name=preview --baseurl=$(PREVIEW_URL)\n" ;\
	        fi ;\
	    fi ;\
	    echo "repo --name=$${FEDORA_REPO} $${FEDORA_REPO_LOC}" > repos.ks ;\
	    printf "$${UPDATE_REPO_LINE}" >> repos.ks ;\
	)

ovirt-node-recipe.ks:
	ksflatten ovirt-node-image.ks --output $@
# XXX broken ksflatten leaves %include
	sed -i 's/^%include /#&/' $@

.PHONY: ovirt-node-recipe.ks repos.ks
