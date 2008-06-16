pkg_name = ovirt-wui

all: rpms
include ../common/release.mk

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

# convience method to simulate make install, not for production use
install: rpms
	rpm -Uvh rpm-build/ovirt-wui-$(VERSION)-$(RELEASE)$(DIST).$(ARCH).rpm --force

.PHONY: all clean genlangs tar install
