#!/usr/bin/make
#
# Makefile for SchoolTool
#
# $Id$

PYTHON=python2.3
PYTHONDIR=/usr/lib/python2.3
TESTFLAGS=-w

all: build

build:
	$(PYTHON) setup.py build_ext -i
	$(PYTHON) remove-stale-bytecode.py

extract-translations:
	PYTHONPATH=src $(PYTHON) src/schooltool/translation/i18nextract.py \
			-d schooltool -o src/schooltool/translation/ \
			src/schooltool *.py -u schooltool.uris
	$(MAKE) update-translations

update-translations:
	for f in `find src/schooltool/translation/ -name 'schooltool.po'`; \
	do								   \
	     msgmerge -U $$f src/schooltool/translation/schooltool.pot;	   \
	     msgfmt -o $${f%.po}.mo $$f;				   \
	done

clean:
	find . \( -name '*.o' -o -name '*.py[co]' \) -exec rm -f {} \;
	rm -rf build
	rm -rf debian/schooltool-server debian/schooltool-clients
	rm -f debian/schooltool-clients.substvars
	rm -f debian/schooltool-clients.postinst.debhelper
	rm -f debian/schooltool-clients.prerm.debhelper
	rm -f debian/schooltool-server.substvars
	rm -f debian/schooltool-server.postinst.debhelper
	rm -f debian/schooltool-server.postrm.debhelper
	rm -f debian/schooltool-server.prerm.debhelper
	rm -f debian/import-sampleschool
	rm -f debian/files
	rm -f build-stamp install-stamp

realclean: clean
	find . \( -name '*.so' -o -name '*.pyd' \) -exec rm -f {} \;
	rm -f Data.fs* *.csv tags ID *.log

test: build
	LC_ALL="C" $(PYTHON) test.py $(TESTFLAGS) schooltool

testall: build
	LC_ALL="C" $(PYTHON) test.py $(TESTFLAGS)

ftest: build
	@LC_ALL="C" $(PYTHON) schooltool-server.py -c test.conf -d \
	&& ($(PYTHON) test.py -f $(TESTFLAGS) ; \
	kill `cat testserver.pid`)

run: build
	$(PYTHON) schooltool-server.py

runtestserver: build
	LC_ALL="C" $(PYTHON) schooltool-server.py -c test.conf

runclient: build
	$(PYTHON) schooltool-client.py

runwxclient: build
	$(PYTHON) wxschooltool.py

sampledata teachers.csv groups.csv pupils.csv resources.csv:
	$(PYTHON) generate-sampleschool.py

sampleschool: build teachers.csv groups.csv pupils.csv resources.csv
	@$(PYTHON) schooltool-server.py -d \
	&& ($(PYTHON) import-sampleschool.py ; \
	kill `cat schooltool.pid`)

coverage: build
	rm -rf coverage
	LC_ALL="C" $(PYTHON) test.py $(TESTFLAGS) --coverage schooltool

coverage-report:
	@cd coverage && ls schooltool* | grep -v tests | xargs grep -c '^>>>>>>' | grep -v ':0$$'

coverage-report-list:
	@cd coverage && ls schooltool* | grep -v tests | xargs grep -l '^>>>>>>'

edit-coverage-reports:
	@cd coverage && $(EDITOR) `ls schooltool* | grep -v tests | xargs grep -l '^>>>>>>'`

vi-coverage-reports:
	@cd coverage && vi '+/^>>>>>>/' `ls schooltool* | grep -v tests | xargs grep -l '^>>>>>>'`

deb:
	dpkg-buildpackage -uc -b -rfakeroot


.PHONY: all build clean test ftest run coverage sampleschool deb
