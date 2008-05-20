VERSION		= $(shell echo `awk '{ print $$1 }' version`)
RELEASE		= $(shell echo `awk '{ print $$2 }' version`)
NEWRELEASE	= $(shell echo $$(($(RELEASE) + 1)))
X		= $(shell echo `awk '{ if (split($$2,r,".") >= 2) { if (r[1]=="0") {print r[2]+1} else print 1 } else print 1 }' version`)
GITRELEASE	= $(shell echo 0.$(X).`date --utc +%Y%m%d%H%M`git`git show-ref --heads --hash=7 $$(git branch|awk '$$1="*" {print $$2}')`)
DIST		= $(shell rpm --eval '%{dist}')
ARCH		= $(shell uname -i)

SPEC_FILE	= ovirt-wui.spec
NAME		= ovirt-wui

NV		= $(NAME)-$(VERSION)
RPM_FLAGS	=	--define "_topdir	%(pwd)/rpm-build" \
			--define "_builddir	%{_topdir}" \
			--define "_rpmdir	%{_topdir}" \
			--define "_srcrpmdir	%{_topdir}" \
			--define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
			--define "_specdir	%{_topdir}" \
			--define "_sourcedir	%{_topdir}"

DATADIR		= $(shell rpm --eval "%{_datadir}")

all: rpms

bumpgit:
	-echo "$(VERSION) $(GITRELEASE)" > version

bumprelease:	
	-echo "$(VERSION) $(NEWRELEASE)" > version

setversion: 
	-echo "$(VERSION) $(RELEASE)" > version


clean:
	-rm -f ovirt*.gz ovirt*.rpm 
	-rm -rf ovirt-wui-* dist build

genlangs:
	cd src; rake updatepo; rake makemo

tar: clean
	mkdir -p $(NV)
	cp -a src conf scripts $(NV)
	find $(NV) \( -name '*~' -o -name '#*#' \) -print0 | xargs --no-run-if-empty --null rm -vf
	find $(NV)/src/tmp -type f -print0 | xargs --no-run-if-empty --null rm -vf
	mkdir -p rpm-build
	tar zcvf rpm-build/$(NV).tar.gz $(NV)
	cp version rpm-build/
	rm -rf $(NV)

new-rpms: bumprelease rpms

rpms: tar	
	rpmbuild $(RPM_FLAGS) -ba $(SPEC_FILE)

# convience method to simulate make install, not for production use
install: rpms
	rpm -Uvh rpm-build/ovirt-wui-$(VERSION)-$(RELEASE)$(DIST).$(ARCH).rpm --force
	/sbin/service ovirt-wui restart	
