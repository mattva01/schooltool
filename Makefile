#!/usr/bin/make
#
# Makefile for SchoolTool
#
# $Id$

PYTHON=python2.3
PYTHONDIR=/usr/lib/python2.3
TESTFLAGS=-w
PO=$(wildcard src/schooltool/translation/*/LC_MESSAGES/*.po)
MO=$(PO:.po=.mo)
PYTHONPATH=src:Zope3/src


%.mo : %.po
	msgfmt -o $@ $<


all: build

build: build-translations
	$(PYTHON) setup.py build_ext -i
	cd Zope3 && $(PYTHON) setup.py build_ext -i
	$(PYTHON) remove-stale-bytecode.py

extract-translations:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) \
                        src/schooltool/translation/i18nextract.py \
			-d schooltool -o src/schooltool/translation/ \
			src/schooltool *.py
	$(MAKE) update-translations

update-translations:
	for f in `find src/schooltool/translation/ -name '*.po'`; \
	do								   \
	     msgmerge -U $$f src/schooltool/translation/schooltool.pot;	   \
	     msgfmt -o $${f%.po}.mo $$f;				   \
	done

build-translations: $(MO)

clean:
	find . \( -path './src/schooltool/*.mo' -o -name '*.o' \
	         -o -name '*.py[co]' \) -exec rm -f {} \;
	rm -rf build
	[ ! -d debian ] || debian/rules debdirclean

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

sampledata persons.csv groups.csv resources.csv timetable.csv roster.txt:
	$(PYTHON) generate-sampleschool.py

sampleschool: build persons.csv groups.csv resources.csv timetable.csv roster.txt
	@$(PYTHON) schooltool-server.py -d && \
	($(PYTHON) import-sampleschool.py ; \
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
