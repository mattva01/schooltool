#!/usr/bin/make
#
# Makefile for SchoolTool
#
# $Id$

PYTHON=python2.3
PYTHONDIR=/usr/lib/python2.3
TESTFLAGS=-w
PYTHONPATH=src:Zope3/src

all: build

build:
	$(PYTHON) setup.py schoolbell build_ext -i
	cd Zope3 && $(PYTHON) setup.py build_ext -i
	$(PYTHON) remove-stale-bytecode.py

realclean: clean
	find . \( -name '*.so' -o -name '*.pyd' \) -exec rm -f {} \;
	rm -f Data.fs* *.csv tags ID *.log
	rm -f scripts/import-sampleschool
	rm -f MANIFEST.schoolbell
	rm -f MANIFEST.schooltool
	rm -rf dist

test: build
	LC_ALL="C" $(PYTHON) test.py $(TESTFLAGS) schoolbell

ftest: build
	$(PYTHON) test.py -f $(TESTFLAGS) schoolbell 

run: build
	$(PYTHON) schoolbell-server.py

.PHONY: schoolbelldist
schoolbelldist: realclean
	rm -rf dist
	find . -name '*.py[dco]' -exec rm -f {} \;
	fakeroot ./debian/rules clean
	./setup.py schoolbell sdist

.PHONY: signtar
signtar: dist
	md5sum dist/school*.{tar.gz,zip} > dist/md5sum
	gpg --clearsign dist/md5sum
	mv dist/md5sum.asc dist/md5sum

.PHONY: all build clean test ftest run coverage sampleschool
