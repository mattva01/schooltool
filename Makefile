#!/usr/bin/make
#
# Makefile for SchoolTool
#

BOOTSTRAP_PYTHON = python2.5
INSTANCE_TYPE = schooltool

BUILDOUT_FLAGS =

.DEFAULT_GOAL = build

.PHONY: build
build: buildout instance

.PHONY: update
update: bin/buildout
	test ! -f versions.cfg.in || rm versions.cfg.in
	bzr up || true
	$(MAKE) buildout BUILDOUT_FLAGS=-n

.PHONY: test
test: build
	bin/test -u

.PHONY: testall
testall: build
	bin/test

.PHONY: ftest
ftest: build
	bin/test -f

.PHONY: run
run: build
	bin/start-schooltool-instance instance

instance:
	$(MAKE) buildout
	bin/make-schooltool-instance instance instance_type=$(INSTANCE_TYPE)

.PHONY: bootstrap
bootstrap:
	$(MAKE) buildout.cfg
	$(BOOTSTRAP_PYTHON) bootstrap.py

bin/buildout:
	$(MAKE) bootstrap

.PHONY: buildout
buildout: .run.buildout

.run.buildout: bin/buildout version.txt setup.py versions.cfg base.cfg buildout.cfg
	bin/buildout $(BUILDOUT_FLAGS)
	touch .run.buildout

buildout.cfg:
	$(MAKE) versions.cfg
	cp buildout.cfg.in buildout.cfg
	touch buildout.cfg

versions.cfg.in:
	wget http://ftp.schooltool.org/schooltool/1.2/versions.cfg -O versions.cfg.in
	test -s versions.cfg.in && touch versions.cfg.in

versions.cfg: versions.cfg.in
	# test if versions.cfg exists or it can be created.
	test -f versions.cfg || test -s versions.cfg.in && touch versions.cfg
	# update version.cfg only if it changed on server
	@if [ -s versions.cfg.in ] && [ "`diff versions.cfg versions.cfg.in`" ]; \
	then \
	    cp versions.cfg.in versions.cfg; \
	    touch versions.cfg; \
	fi

version.txt: version.txt.in .bzr/branch/last-revision
	echo -n `cat version.txt.in`_r`bzr revno` >> version.txt

.PHONY: release
release: version.txt.in
	bin/buildout setup setup.py sdist

.PHONY: coverage
coverage: build
	test -d parts/test/coverage && ! test -d coverage && mv parts/test/coverage . || true
	rm -rf coverage
	bin/test --at-level 2 -u --coverage=coverage
	mv parts/test/coverage .

.PHONY: coverage-reports-html
coverage-reports-html coverage/reports:
	test -d parts/test/coverage && ! test -d coverage && mv parts/test/coverage . || true
	rm -rf coverage/reports
	mkdir coverage/reports
	bin/coverage coverage coverage/reports
	ln -s schooltool.html coverage/reports/index.html

.PHONY: ftest-coverage
ftest-coverage: build
	test -d parts/test/ftest-coverage && ! test -d ftest-coverage && mv parts/test/ftest-coverage . || true
	rm -rf ftest-coverage
	bin/test --at-level 2 -f --coverage=ftest-coverage
	mv parts/test/ftest-coverage .

.PHONY: ftest-coverage-reports-html
ftest-coverage-reports-html ftest-coverage/reports:
	test -d parts/test/ftest-coverage && ! test -d ftest-coverage && mv parts/test/ftest-coverage . || true
	rm -rf ftest-coverage/reports
	mkdir ftest-coverage/reports
	bin/coverage ftest-coverage ftest-coverage/reports
	ln -s schooltool.html ftest-coverage/reports/index.html

.PHONY: clean
clean:
	test ! -f .run.buildout || rm .run.buildout
	test ! -f versions.cfg || rm versions.cfg
	test ! -f versions.cfg.in || rm versions.cfg.in
	test ! -f version.txt || rm version.txt
	rm -rf bin develop-eggs parts python
	rm -rf build dist
	rm -f .installed.cfg
	rm -f ID TAGS tags
	find . -name '*.py[co]' -exec rm -f {} \;
	find . -name '*.mo' -exec rm -f {} +
	find . -name 'LC_MESSAGES' -exec rmdir -p --ignore-fail-on-non-empty {} +

.PHONY: extract-translations
extract-translations: build
	bin/i18nextract --egg schooltool \
	                --domain schooltool \
	                --zcml schooltool/common/translations.zcml \
	                --output-file src/schooltool/locales/schooltool.pot
	bin/i18nextract --egg schooltool \
	                --domain schooltool.commendation \
	                --zcml schooltool/commendation/translations.zcml \
	                --output-file src/schooltool/commendation/locales/schooltool.commendation.pot

.PHONY: compile-translations
compile-translations:
	set -e; \
	locales=src/schooltool/locales; \
	for f in $${locales}/*.po; do \
	    mkdir -p $${f%.po}/LC_MESSAGES; \
	    msgfmt -o $${f%.po}/LC_MESSAGES/schooltool.mo $$f;\
	done
	locales=src/schooltool/commendation/locales; \
	for f in $${locales}/*.po; do \
	    mkdir -p $${f%.po}/LC_MESSAGES; \
	    msgfmt -o $${f%.po}/LC_MESSAGES/schooltool.commendation.mo $$f;\
	done

.PHONY: update-translations
update-translations: extract-translations
	set -e; \
	locales=src/schooltool/locales; \
	for f in $${locales}/*.po; do \
	    msgmerge -qU $$f $${locales}/schooltool.pot ;\
	done
	locales=src/schooltool/commendation/locales; \
	for f in $${locales}/*.po; do \
	    msgmerge -qU $$f $${locales}/schooltool.commendation.pot ;\
	done
	$(MAKE) PYTHON=$(PYTHON) compile-translations

.PHONY: ubuntu-environment
ubuntu-environment:
	@if [ `whoami` != "root" ]; then { \
	 echo "You must be root to create an environment."; \
	 echo "I am running as $(shell whoami)"; \
	 exit 3; \
	} else { \
	 apt-get install bzr build-essential python-all python-all-dev libc6-dev libicu-dev; \
	 apt-get build-dep python-imaging; \
	 echo "Installation Complete: Next... Run 'make'."; \
	} fi
