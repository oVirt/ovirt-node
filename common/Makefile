pkg_name = ovirt-release
FILES = ovirt-release.spec ovirt.repo version

all: rpms
include ../common/release.mk

clean:
	rm -rf rpm-build

tar: clean
	mkdir -p rpm-build
	cp $(FILES) rpm-build/

.PHONY: all clean tar
