#!/usr/bin/make
#
# Makefile for SchoolTool
#

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
	@PYTHONPATH=src $(PYTHON) $(PWD)/src/schooltool/main.py -m -c test.conf & \
	pid=$$! ; \
	sleep 2 ; \
	$(PYTHON) test.py -f $(TESTFLAGS) ; \
	kill $$pid

run: build
	PYTHONPATH=src $(PYTHON) src/schooltool/main.py

runclient: build
	PYTHONPATH=src $(PYTHON) src/schooltool/client.py

runwxclient: build
	PYTHONPATH=src $(PYTHON) src/schooltool/wxclient.py

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


.PHONY: all build clean test ftest run coverage
