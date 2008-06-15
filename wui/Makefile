VERSION		:= $(shell awk '{ print $$1 }' version)
RELEASE		:= $(shell awk '{ print $$2 }' version)
NEWVERSION	= $$(awk 'BEGIN { printf "%.2f", $(VERSION) + .01 }')
NEWRELEASE	= $$(($(RELEASE) + 1))
X		= $$(awk '{ split($$2,r,"."); \
                            printf("%d.%d\n", r[1], r[2]+1) }' version)
git_head	= $$(git show-ref --hash=7 HEAD)
GITRELEASE	= $(X).$$(date --utc +%Y%m%d%H%M)git$(git_head)
DIST		= $$(rpm --eval '%{dist}')
ARCH		:= $(shell uname -i)

NAME		= ovirt-wui
SPEC_FILE	= $(NAME).spec

NV		= $(NAME)-$(VERSION)
RPM_FLAGS	= \
  --define "_topdir	%(pwd)/rpm-build" \
  --define "_builddir	%{_topdir}" \
  --define "_rpmdir	%{_topdir}" \
  --define "_srcrpmdir	%{_topdir}" \
  --define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
  --define "_specdir	%{_topdir}" \
  --define "_sourcedir	%{_topdir}"

all: rpms

bumpgit:
	echo "$(VERSION) $(GITRELEASE)" > version

bumprelease:
	echo "$(VERSION) $(NEWRELEASE)" > version

bumpversion:
	echo "$(NEWVERSION) 0" > version

setversion:
	echo "$(VERSION) $(RELEASE)" > version

clean:
	rm -f ovirt*.gz ovirt*.rpm
	rm -rf ovirt-wui-* dist build

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
