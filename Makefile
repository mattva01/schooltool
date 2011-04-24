#!/usr/bin/make

PACKAGE=schooltool

DIST=/home/ftp/pub/schooltool/trunk
BOOTSTRAP_PYTHON=python2.6

INSTANCE_TYPE=schooltool
BUILDOUT_FLAGS=

.PHONY: all
all: build

.PHONY: build
build: .installed.cfg

.PHONY: bootstrap
bootstrap bin/buildout python:
	$(BOOTSTRAP_PYTHON) bootstrap.py

.PHONY: buildout
buildout .installed.cfg: python bin/buildout buildout.cfg base.cfg setup.py
	bin/buildout $(BUILDOUT_FLAGS)

.PHONY: update
update:
	bzr up
	$(MAKE) buildout BUILDOUT_FLAGS=-n

instance:
	bin/make-schooltool-instance instance instance_type=$(INSTANCE_TYPE)

.PHONY: run
run: build instance
	bin/start-schooltool-instance instance

.PHONY: tags
tags: build
	bin/tags

.PHONY: clean
clean:
	rm -rf python
	rm -rf bin develop-eggs parts .installed.cfg
	rm -rf build
	rm -f ID TAGS tags
	rm -rf coverage
	find . -name '*.py[co]' -delete
	find . -name '*.mo' -delete
	find . -name 'LC_MESSAGES' -exec rmdir -p --ignore-fail-on-non-empty {} +

.PHONY: realclean
realclean:
	rm -rf eggs
	rm -rf dist
	rm -rf instance
	$(MAKE) clean

# Tests

.PHONY: test
test: build
	bin/test -u

.PHONY: ftest
ftest: build
	bin/test -f

.PHONY: testall
testall: build
	bin/test --at-level 2

# Coverage

.PHONY: coverage
coverage: build
	test -d parts/test/coverage && ! test -d coverage && mv parts/test/coverage . || true
	rm -rf coverage
	bin/test --at-level 2 -u --coverage=coverage
	mv parts/test/coverage .

.PHONY: coverage-reports-html
coverage-reports-html coverage/reports: coverage
	test -d parts/test/coverage && ! test -d coverage && mv parts/test/coverage . || true
	rm -rf coverage/reports
	mkdir coverage/reports
	bin/coverage coverage coverage/reports
	ln -s $(PACKAGE).html coverage/reports/index.html

.PHONY: ftest-coverage
ftest-coverage: build
	test -d parts/test/ftest-coverage && ! test -d ftest-coverage && mv parts/test/ftest-coverage . || true
	rm -rf ftest-coverage
	bin/test --at-level 2 -f --coverage=ftest-coverage
	mv parts/test/ftest-coverage .

.PHONY: ftest-coverage-reports-html
ftest-coverage-reports-html ftest-coverage/reports: ftest-coverage
	test -d parts/test/ftest-coverage && ! test -d ftest-coverage && mv parts/test/ftest-coverage . || true
	rm -rf ftest-coverage/reports
	mkdir ftest-coverage/reports
	bin/coverage ftest-coverage ftest-coverage/reports
	ln -s $(PACKAGE).html ftest-coverage/reports/index.html

# Translations

.PHONY: extract-translations
extract-translations: build
	bin/i18nextract --egg $(PACKAGE) \
	                --domain $(PACKAGE) \
	                --zcml schooltool/common/translations.zcml \
	                --output-file src/schooltool/locales/schooltool.pot

.PHONY: compile-translations
compile-translations:
	set -e; \
	locales=src/schooltool/locales; \
	for f in $${locales}/*.po; do \
	    mkdir -p $${f%.po}/LC_MESSAGES; \
	    msgfmt -o $${f%.po}/LC_MESSAGES/$(PACKAGE).mo $$f;\
	done

.PHONY: update-translations
update-translations:
	set -e; \
	locales=src/schooltool/locales; \
	for f in $${locales}/*.po; do \
	    msgmerge -qUN $$f $${locales}/$(PACKAGE).pot ;\
	done
	$(MAKE) compile-translations

# Docs

docs: build
	bin/docs

# Release

.PHONY: release
release: bin/buildout compile-translations
	grep -qv 'dev' version.txt.in || echo -n `cat version.txt.in`-r`bzr revno` > version.txt
	bin/buildout setup setup.py sdist
	rm -f version.txt

.PHONY: move-release
move-release:
	mv -v dist/$(PACKAGE)-*.tar.gz $(DIST)/dev

# Helpers

.PHONY: ubuntu-environment
ubuntu-environment:
	sudo apt-get install bzr build-essential gettext enscript ttf-liberation \
	    python-all-dev libc6-dev libicu-dev libxslt1-dev libfreetype6-dev libjpeg62-dev 

