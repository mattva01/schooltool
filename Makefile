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

clean:
	find . \( -name '*.o' -o -name '*.py[co]' \) -exec rm -f {} \;
	rm -rf build

realclean: clean
	find . \( -name '*.so' -o -name '*.dll' \) -exec rm -f {} \;

test: build
	$(PYTHON) test.py $(TESTFLAGS) schooltool

testall: build
	$(PYTHON) test.py $(TESTFLAGS)

ftest: build
	@PYTHONPATH=src $(PYTHON) src/schooltool/main.py -c test.conf & \
	pid=$$! ; \
	sleep 2 ; \
	ps -p $$pid > /dev/null && (\
	$(PYTHON) test.py -f $(TESTFLAGS) ; \
	kill $$pid )

run: build
	PYTHONPATH=src $(PYTHON) src/schooltool/main.py

runmockup: build
	PYTHONPATH=src $(PYTHON) src/schooltool/main.py -m

runtestserver: build
	PYTHONPATH=src $(PYTHON) src/schooltool/main.py -c test.conf

runclient: build
	PYTHONPATH=src $(PYTHON) src/schooltool/client.py

runwxclient: build
	PYTHONPATH=src $(PYTHON) src/schooltool/wxclient.py

sampledata teachers.csv groups.csv pupils.csv:
	PYTHONPATH=src $(PYTHON) src/schooltool/datagen.py schooltool-m2

sampleschool: teachers.csv groups.csv pupils.csv
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


.PHONY: all build clean test ftest run coverage sampleschool
