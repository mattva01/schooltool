#!/usr/bin/make
#
# Makefile for SchoolBell
#
# $Id$

PYTHON=python2.3
TESTFLAGS=-w1
PYTHONPATH=src:Zope3/src

.PHONY: all
all: build

.PHONY: build
build:
	cd Zope3 && $(PYTHON) setup.py build_ext -i
	$(PYTHON) remove-stale-bytecode.py

.PHONY: realclean
realclean: clean
	find . \( -name '*.so' -o -name '*.pyd' \) -exec rm -f {} \;
	rm -f Data.fs* tags ID *.log
	rm -f MANIFEST
	rm -rf dist

.PHONY: build
test: build
	LC_ALL="C" $(PYTHON) test.py $(TESTFLAGS)

.PHONY: ftest
ftest: build
	$(PYTHON) test.py -f $(TESTFLAGS)

.PHONY: run
run: build
	$(PYTHON) schoolbell-server.py

.PHONY: schoolbelldist
schoolbelldist: realclean
	rm -rf dist
	find . -name '*.py[dco]' -exec rm -f {} \;
	fakeroot ./debian/rules clean
	./setup.py schoolbell sdist --formats=gztar,zip

.PHONY: signtar
signtar: dist
	md5sum dist/school*.{tar.gz,zip} > dist/md5sum
	gpg --clearsign dist/md5sum
	mv dist/md5sum.asc dist/md5sum
