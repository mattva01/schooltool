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


%.mo : %.po
	msgfmt -o $@ $<


all: build

build: build-translations
	$(PYTHON) setup.py build_ext -i
	$(PYTHON) remove-stale-bytecode.py

extract-translations:
	PYTHONPATH=src $(PYTHON) src/schooltool/translation/i18nextract.py \
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
	[ -x debian/rules ] && debian/rules debdirclean

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

sampledata persons.csv groups.csv resources.csv:
	$(PYTHON) generate-sampleschool.py

sampleschool: build groups.csv persons.csv resources.csv
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

schooltooltar: realclean
	[ ! -d .svn ] || { echo Error: This is a working copy, export it first; exit 1;}
	builddir=`echo "$$PWD" | sed 's/.*\///'` 			&&\
	[ ztool == z`echo "$$builddir"| grep -o tool` ]		  	||\
	{ echo Error: The directory has the wrong name; exit 1;}	&&\
	cd .. 								&&\
	tar -czf "$$builddir.tar.gz" 					\
		    --exclude=CVS 					\
		    "$$builddir"

schoolbelltar: realclean
	[ ! -d .svn ] || { echo Error: This is a working copy, export it first; exit 1;}
	builddir=`echo "$$PWD" | sed 's/.*\///'` 			&&\
	[ zbell == z`echo "$$builddir"| grep -o bell` ]		  	||\
	{ echo Error: The directory has the wrong name; exit 1;}	&&\
	cd .. 								&&\
	tar -czf "$$builddir.tar.gz"					\
		    --exclude=schooltool.conf.in			\
		    --exclude=schooltool-grapher.py			\
		    --exclude=schooltool-client.py			\
		    --exclude=schooltool-server.py			\
		    --exclude=wxschooltool.py				\
		    --exclude=import-sampleschool.py			\
		    --exclude=generate-sampleschool.py			\
		    --exclude=clients					\
		    --exclude=debian 					\
		    --exclude=CVS 					\
		    "$$builddir"

.PHONY: all build clean test ftest run coverage sampleschool deb
