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

realclean: clean
	find . \( -name '*.so' -o -name '*.dll' \) -exec rm -f {} \;

test: build
	LC_ALL="C" $(PYTHON) test.py $(TESTFLAGS) schooltool

testall: build
	LC_ALL="C" $(PYTHON) test.py $(TESTFLAGS)

ftest: build
	@PYTHONPATH=src LC_ALL="C" $(PYTHON) src/schooltool/main.py -c test.conf & \
	pid=$$! ; \
	sleep 2 ; \
	ps -p $$pid > /dev/null && (\
	$(PYTHON) test.py -f $(TESTFLAGS) ; \
	kill $$pid )

run: build
	$(PYTHON) schooltool-server.py

runtestserver: build
	LC_ALL="C" $(PYTHON) schooltool-server.py -c test.conf

runclient: build
	$(PYTHON) schooltool-client.py

runwxclient: build
	$(PYTHON) wxschooltool.py

sampledata teachers.csv groups.csv pupils.csv:
	PYTHONPATH=src $(PYTHON) src/schooltool/clients/datagen.py schooltool-m4

sampleschool: build teachers.csv groups.csv pupils.csv
	PYTHONPATH=src $(PYTHON) runimport.py

coverage: build
	rm -rf coverage
	$(PYTHON) test.py $(TESTFLAGS) --coverage schooltool

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
