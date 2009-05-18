#!/usr/bin/make
#
# Makefile for SchoolTool
#

BOOTSTRAP_PYTHON=python2.5

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
	rm -rf coverage
	bin/test -u --coverage=coverage
	mv parts/test/coverage .
	@cd coverage && ls | grep -v tests | xargs grep -c '^>>>>>>' | grep -v ':0$$'

.PHONY: coverage-reports-html
coverage-reports-html:
	rm -rf coverage/reports
	mkdir coverage/reports
	bin/coverage
	ln -s schooltool.html coverage/reports/index.html

.PHONY: clean
clean:
	rm -rf bin develop-eggs parts python
	rm -rf build dist
	rm -f .installed.cfg
	rm -f ID TAGS tags
	find . \( -path './src/*.mo' -o -name '*.o' \
	         -o -name '*.py[co]' \) -exec rm -f {} \;

.PHONY: extract-translations
extract-translations: build
	bin/i18nextract --egg schooltool --domain schooltool --zcml schooltool/common/translations.zcml --output-file src/schooltool/locales/schooltool.pot
	bin/i18nextract --egg schooltool --domain schooltool.commendation --zcml schooltool/commendation/translations.zcml --output-file src/schooltool/commendation/locales/schooltool.commendation.pot

.PHONY: compile-translations
compile-translations:
	set -e; \
	locales=src/schooltool/locales; \
	for f in $${locales}/*/LC_MESSAGES/schooltool.po; do \
	    msgfmt -o $${f%.po}.mo $$f;\
	done
	locales=src/schooltool/commendation/locales; \
	for f in $${locales}/*/LC_MESSAGES/schooltool.commendation.po; do \
	    msgfmt -o $${f%.po}.mo $$f;\
	done

.PHONY: update-translations
update-translations: extract-translations
	set -e; \
	locales=src/schooltool/commendation/locales; \
	for f in $${locales}/*/LC_MESSAGES/schooltool.commendation.po; do \
	    msgmerge -qU $$f $${locales}/schooltool.commendation.pot ;\
	done
	locales=src/schooltool/locales; \
	for f in $${locales}/*/LC_MESSAGES/schooltool.po; do \
	    msgmerge -qU $$f $${locales}/schooltool.pot ;\
	done
	$(MAKE) PYTHON=$(PYTHON) compile-translations

.PHONY: ubuntu-environment
ubuntu-environment:
	@if [ `whoami` != "root" ]; then { \
	 echo "You must be root to create an environment."; \
	 echo "I am running as $(shell whoami)"; \
	 exit 3; \
	} else { \
	 apt-get install subversion build-essential python-all python-all-dev libc6-dev libicu-dev; \
	 apt-get build-dep python-imaging; \
	 apt-get build-dep python-libxml2 libxml2; \
	 echo "Installation Complete: Next... Run 'make'."; \
	} fi
