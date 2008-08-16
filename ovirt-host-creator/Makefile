YUMCACHE=$$(pwd)/../tmp/cache

pkg_name = ovirt-host-image

all: rpms
include ../common/release.mk

clean:
	rm -rf ovirt-host-image-* ovirt-cd.log

distclean: clean
	rm -rf *.iso repos.ks rpm-build

repos.ks: repos.ks.in
	cp repos.ks.in repos.ks

ovirt.iso: ovirt.ks common-install.ks common-pkgs.ks common-post.ks repos.ks
	../common/rpm-compare.py GE 0 livecd-tools 017.1 1
	livecd-creator --cache=$(YUMCACHE) --skip-minimize -c ovirt.ks -f ovirt

tar: clean ovirt.iso
	mkdir -p $(NV)
	cp -a ovirt-host-image.spec ovirt-pxe ovirt-flash ovirt-flash-static ovirt.iso $(NV)
	mkdir -p rpm-build
	tar zcvf rpm-build/$(NV).tar $(NV)
	cp version rpm-build/
	rm -rf $(NV)

.PHONY: all clean tar distclean
