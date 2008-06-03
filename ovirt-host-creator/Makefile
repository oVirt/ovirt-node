VERSION		= $(shell echo `awk '{ print $$1 }' version`)
RELEASE		= $(shell echo `awk '{ print $$2 }' version`)
NEWRELEASE	= $(shell echo $$(($(RELEASE) + 1)))
X		= $(shell echo `awk '{ if (split($$2,r,".") >= 2) { if (r[1]=="0") {print r[2]+1} else print 1 } else print 1 }' version`)
GITRELEASE	= $(shell echo 0.$(X).`date --utc +%Y%m%d%H%M`git`git show-ref --heads --hash=7 $$(git branch|awk '$$1="*" {print $$2}')`)
DIST		= $(shell rpm --eval '%{dist}')
ARCH		= $(shell uname -i)

SPEC_FILE	= ovirt-host-image.spec
NAME		= ovirt-host-image

NV		= $(NAME)-$(VERSION)
RPM_FLAGS	=	--define "_topdir	%(pwd)/rpm-build" \
			--define "_builddir	%{_topdir}" \
			--define "_rpmdir	%{_topdir}" \
			--define "_srcrpmdir	%{_topdir}" \
			--define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
			--define "_specdir	%{_topdir}" \
			--define "_sourcedir	%{_topdir}"

all: rpms

bumpgit:
	-echo "$(VERSION) $(GITRELEASE)" > version

bumprelease:
	-echo "$(VERSION) $(NEWRELEASE)" > version

setversion:
	-echo "$(VERSION) $(RELEASE)" > version

clean:
	-rm -rf ovirt-host-image-* ovirt-pxe.log

build: ovirt-$(ARCH).ks common-install.ks common-pkgs.ks common-post.ks repos.ks
	-rm -rf tftpboot/
	./ovirt-pxe.sh > ovirt-pxe.log 2>&1

tar: clean build
	mv $(shell cat iso-file) ovirt.iso
	mkdir -p $(NV)
	cp -a ovirt-host-image.spec ovirt.iso tftpboot/* $(NV)
	mkdir -p rpm-build
	tar zcvf rpm-build/$(NV).tar $(NV)
	cp version rpm-build/
	rm -rf $(NV)

new-rpms: bumprelease rpms

rpms: tar
	rpmbuild $(RPM_FLAGS) -ba $(SPEC_FILE)

