#!/usr/bin/make
#
# Makefile for SchoolTool
#
# $Id$

PYTHON=python
TESTFLAGS=-w
POT=src/schooltool/locales/schooltool.pot
PO=$(wildcard src/schooltool/locales/*/LC_MESSAGES/*.po)
PYTHONPATH=src:Zope3/src

.PHONY: all
all: build

.PHONY: build
build:
	$(PYTHON) setup.py build_ext -i
	cd Zope3 && $(PYTHON) setup.py build_ext -i
	$(PYTHON) remove-stale-bytecode.py

.PHONY: clean
clean:
	find . \( -path './src/schooltool/*.mo' -o -name '*.o' \
	         -o -name '*.py[co]' \) -exec rm -f {} \;
	rm -rf build

.PHONY: realclean
realclean: clean
	find . \( -name '*.so' -o -name '*.pyd' \) -exec rm -f {} \;
	rm -f Data.fs* *.csv tags ID *.log
	rm -f scripts/import-sampleschool
	rm -f MANIFEST
	rm -rf dist

.PHONY: test
test: build
	$(PYTHON) test.py $(TESTFLAGS) -s src/schooltool

.PHONY: testall
testall: build
	$(PYTHON) test.py $(TESTFLAGS)

.PHONY: ftest
ftest: build
	$(PYTHON) test.py $(TESTFLAGS) -s src/schooltool -f

.PHONY: run
run: build
	$(PYTHON) schooltool-server.py

.PHONY: coverage
coverage: build
	rm -rf coverage
	$(PYTHON) test.py $(TESTFLAGS) --coverage -s src/schooltool

.PHONY: coverage-report
coverage-report:
	@cd coverage && ls schooltool* | grep -v tests | xargs grep -c '^>>>>>>' | grep -v ':0$$'

.PHONY: coverage-report-list
coverage-report-list:
	@cd coverage && ls schooltool* | grep -v tests | xargs grep -l '^>>>>>>'

.PHONY: edit-coverage-reports
edit-coverage-reports:
	@cd coverage && $(EDITOR) `ls schooltool* | grep -v tests | xargs grep -l '^>>>>>>'`

.PHONY: vi-coverage-reports
vi-coverage-reports:
	@cd coverage && vi '+/^>>>>>>/' `ls schooltool* | grep -v tests | xargs grep -l '^>>>>>>'`

Zope3/principals.zcml:
	cp Zope3/sample_principals.zcml $@

Zope3/package-includes/schoolbell-configure.zcml:
	echo '<include package="schoolbell.app" />' > $@

Zope3/package-includes/schooltool-configure.zcml:
	echo '<include package="schooltool" />' > $@

.PHONY: dist
dist: realclean build extract-translations update-translations clean
	rm -rf dist
	find . -name '*.py[dco]' -exec rm -f {} \;
	fakeroot ./debian/rules clean
	./setup.py sdist --formats=schooltooltgz

.PHONY: signtar
signtar: dist
	md5sum dist/school*.tar.gz > dist/md5sum
	gpg --clearsign dist/md5sum
	mv dist/md5sum.asc dist/md5sum

.PHONY: extract-translations
extract-translations: Zope3/principals.zcml Zope3/package-includes/schoolbell-configure.zcml Zope3/package-includes/schooltool-configure.zcml
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) \
		Zope3/utilities/i18nextract.py -d schooltool \
			-o locales -p src/schooltool schooltool

.PHONY: update-translations
update-translations:
	# XXX - fail on error (set -e) when
	# https://launchpad.ubuntu.com/malone/bugs/710 is fixed - jinty
	-for f in $(PO); do			\
	     msgmerge -U $$f $(POT);		\
	     msgfmt -o $${f%.po}.mo $$f;	\
	done

.PHONY: update-rosetta-pot
update-rosetta-pot:
	$(MAKE) build extract-translations
	touch ../launchpad_cookies
	chmod 0600 ../launchpad_cookies ../launchpad_pwd
	curl -kc ../launchpad_cookies -D ../header_login\
	    -F "loginpage_password=<../launchpad_pwd" \
	    -F loginpage_email=jinty@web.de \
	    -F loginpage_submit_login=Log\ In \
	    https://launchpad.ubuntu.com/+login > ../launchpad_log
	curl -kc ../launchpad_cookies -b ../launchpad_cookies\
	    -F "file=@src/schooltool/locales/schooltool.pot" \
	    -F "UPLOAD=Upload" \
	    https://launchpad.ubuntu.com/products/schooltool/0.10-rc1/+pots/schooltool/+edit > ../launchpad_log2
	rm ../launchpad_cookies

.PHONY: get-rosetta-translations
get-rosetta-translations:
	./get-rosetta-translations.py
