

NAME=ovirt-node-molch-plugin

HASH=$(shell git describe --always)
DATE=$(shell date '+%Y%m%d%H%M%S')
VERSION=git$(HASH)

DISTARCHIVE=$(NAME)-$(VERSION).tar.gz

ifndef python
        python := "python"
endif


.PHONY: rpm scm_hash.txt


all:
	@echo targets: rpm, build, dist, install


rpm: clean dist check
	rpmbuild -ta dist/$(DISTARCHIVE)

scm_hash.txt:
	echo "$(HASH)" > scm_hash.txt

check: scm_hash.txt
	rpmlint -v *.spec

dist: clean-dist scm_hash.txt
	${python} setup.py sdist --format=tar
	tar rvf dist/*.tar scm_hash.txt *.spec
	gzip dist/*.tar
	cd dist ; ln -s *.tar.gz $(DISTARCHIVE)

build:
	${python} setup.py build

install:
	${python} setup.py install --prefix=$(prefix) --root=$(root)

clean: clean-dist
	-rm -f *~ scm_hash.txt

clean-dist:
	-rm -f dist/*
