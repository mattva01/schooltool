#!/usr/bin/make
#
# Makefile for SchoolTool
#

PYTHON=python2.3
TESTFLAGS=-pv

all: build

build:
	$(PYTHON) setup.py build_ext -i

clean:
	find . \( -name '*.o' -o -name '*.py[co]' \) -exec rm -f {} \;
	rm -rf build

realclean: clean
	find . \( -name '*.so' -o -name '*.dll' \) -exec rm -f {} \;

test: build
	$(PYTHON) test.py $(TESTFLAGS)

ftest: build
	@PYTHONPATH=src $(PYTHON) src/schooltool/main.py & pid=$$! ; \
	sleep 2 ; \
	$(PYTHON) test.py -f $(TESTFLAGS) ; \
	kill $$pid

run: build
	PYTHONPATH=src $(PYTHON) src/schooltool/main.py


.PHONY: all build clean test ftest run
