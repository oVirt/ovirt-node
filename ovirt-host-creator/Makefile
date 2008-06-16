pkg_name = ovirt-host-image

all: rpms
include ../common/release.mk

clean:
	rm -rf ovirt-host-image-* ovirt-pxe.log

repos.ks: repos.ks.in
	cp repos.ks.in repos.ks

build: ovirt-$(ARCH).ks common-install.ks common-pkgs.ks common-post.ks repos.ks
	rm -rf tftpboot/
	./ovirt-pxe.sh > ovirt-pxe.log 2>&1

tar: clean build
	mv $$(cat iso-file) ovirt.iso
	mkdir -p $(NV)
	cp -a ovirt-host-image.spec ovirt.iso tftpboot/* $(NV)
	mkdir -p rpm-build
	tar zcvf rpm-build/$(NV).tar $(NV)
	cp version rpm-build/
	rm -rf $(NV)

.PHONY: all clean build tar
