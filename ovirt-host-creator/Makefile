pkg_name = ovirt-host-image

all: rpms
include ../common/release.mk

clean:
	rm -rf ovirt-host-image-* ovirt-cd.log

distclean: clean
	rm -rf *.iso repos.ks rpm-build iso-file

repos.ks: repos.ks.in
	sed "s/@@ARCH@@/$(ARCH)/" repos.ks.in > repos.ks

build: ovirt.ks common-install.ks common-pkgs.ks common-post.ks repos.ks
	./rpm-compare.py GE 0 livecd-tools 017.1 1
	./ovirt-cd > ovirt-cd.log 2>&1

tar: clean build
	mv $$(cat iso-file) ovirt.iso
	mkdir -p $(NV)
	cp -a ovirt-host-image.spec ovirt-pxe ovirt-flash ovirt-flash-static ovirt.iso $(NV)
	mkdir -p rpm-build
	tar zcvf rpm-build/$(NV).tar $(NV)
	cp version rpm-build/
	rm -rf $(NV)

.PHONY: all clean build tar distclean
