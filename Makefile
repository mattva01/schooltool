#!/usr/bin/make
#
# Makefile for SchoolTool
#

BOOTSTRAP_PYTHON=python2.4

.PHONY: all
all: build

.PHONY: build
build:
	test -f bin/buildout || $(MAKE) BOOTSTRAP_PYTHON=$(BOOTSTRAP_PYTHON) bootstrap
	test -f bin/test || $(MAKE) buildout
	test -d instance || $(MAKE) build-schooltool-instance

.PHONY: bootstrap
bootstrap:
	$(BOOTSTRAP_PYTHON) bootstrap.py

.PHONY: buildout
buildout:
	bin/buildout

.PHONY: update
update: build
	bin/buildout -n

.PHONY: test
test: build
	bin/test -u

.PHONY: testall
testall: build
	bin/test

.PHONY: ftest
ftest: build
	bin/test -f

.PHONY: build-schooltool-instance
build-schooltool-instance:
	bin/make-schooltool-instance instance instance_type=schooltool.stapp2007

.PHONY: run
run: build
	bin/start-schooltool-instance instance

.PHONY: release
release: compile-translations
	echo -n `sed -e 's/\n//' version.txt.in` > version.txt
	echo -n "_r" >> version.txt
	bzr revno >> version.txt
	bin/buildout setup setup.py sdist

.PHONY: move-release
move-release:
	 mv dist/schooltool-*.tar.gz /home/ftp/pub/schooltool/releases/nightly

.PHONY: coverage
coverage: build
	test -d coverage && rm -rf coverage
	bin/test -u --coverage=coverage
	mv parts/test/coverage .
	@cd coverage && ls | grep -v tests | xargs grep -c '^>>>>>>' | grep -v ':0$$'

.PHONY: coverage-reports-html
coverage-reports-html:
	test -d coverage/reports && rm -rf coverage/reports
	mkdir coverage/reports
	bin/coverage
	ln -s schooltool.html coverage/reports/index.html

.PHONY: clean
clean:
	test -d bin && rm -rf bin
	test -d develop-eggs && rm -rf develop-eggs
	test -d parts && rm -rf parts
	test -d python && rm -rf python
	test -f .installed.cfg && rm .installed.cfg
	test -f ID && rm ID
	test -f TAGS && rm TAGS
	test -f tags && rm tags
	test -d src/lyceum.egg-info/ && rm -rf src/lyceum.egg-info/
	find . \( -path './src/*.mo' -o -name '*.o' \
	         -o -name '*.py[co]' \) -exec rm -f {} \;
