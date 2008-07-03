# Release/version-related Makefile variables and rules.
# This Makefile snippet is included by both ../wui/Makefile and
# ../ovirt-host-creator/Makefile.  It expects the including Makefile
# to define the "pkg_name" variable, as well as a file named "version"
# in the current directory.

ARCH		:= $(shell uname -i)
VERSION		:= $(shell awk '{ print $$1 }' version)
RELEASE		:= $(shell awk '{ print $$2 }' version)
NEWVERSION	= $$(awk 'BEGIN { printf "%.2f", $(VERSION) + .01 }')
NEWRELEASE	= $$(($(RELEASE) + 1))
X		= $$(awk '{ split($$2,r,"."); \
                            printf("%d.%d\n", r[1], r[2]+1) }' version)
git_head	= $$(git log -1 --pretty=format:%h)
GITRELEASE	= $(X).$$(date --utc +%Y%m%d%H%M)git$(git_head)
DIST		= $$(rpm --eval '%{dist}')

SPEC_FILE	= $(pkg_name).spec

NV		= $(pkg_name)-$(VERSION)
RPM_FLAGS	= \
  --define "_topdir	%(pwd)/rpm-build" \
  --define "_builddir	%{_topdir}" \
  --define "_rpmdir	%{_topdir}" \
  --define "_srcrpmdir	%{_topdir}" \
  --define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
  --define "_specdir	%{_topdir}" \
  --define "_sourcedir	%{_topdir}"

bumpgit:
	echo "$(VERSION) $(GITRELEASE)" > version

bumprelease:
	echo "$(VERSION) $(NEWRELEASE)" > version

bumpversion:
	echo "$(NEWVERSION) 0" > version

setversion:
	echo "$(VERSION) $(RELEASE)" > version

new-rpms: bumprelease rpms

rpms: tar
	rpmbuild $(RPM_FLAGS) -ba $(SPEC_FILE)

.PHONY: rpms new-rpms setversion bumprelease bumpversion bumpgit
