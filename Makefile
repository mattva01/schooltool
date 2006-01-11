#!/usr/bin/make
#
# Makefile for SchoolTool
#
# $Id$

PYTHON=python
ZPKG=../../zpkgtools/bin/zpkg
ZOPE_REPOSITORY=svn://svn.zope.org/repos/main/
TESTFLAGS=-w -v
LOCALES=src/schooltool/locales/
TRANSLATION_DOMAINS=schoolbell # schooltool
PYTHONPATH=src:Zope3/src
LOCALE_PATTERN='src/schooltool/locales/@locale@/LC_MESSAGES/schoolbell.po'
ROSETTA_URL='https://launchpad.ubuntu.com/products/schooltool/0.10-rc1/+pots/schooltool'
ROSETTA_LOCALES=de el fr id lt nl nb pa pt tr
SETUPFLAGS=

# Which part of the Zope3 repository do we track
#Z3_VERSION=trunk
Z3_VERSION=branches/3.2
#Z3_VERSION=tags/3.2.0

.PHONY: all
all: build

.PHONY: zope3-checkout
zope3-checkout:
	-test -d Zope3 || svn co $(ZOPE_REPOSITORY)/Zope3/${Z3_VERSION} Zope3

.PHONY: zope3-update
zope3-update:
	svn up Zope3

.PHONY: zpkgsetup-checkout
zpkgsetup-checkout:
	-test -d buildsupport/zpkgsetup || svn co $(ZOPE_REPOSITORY)/zpkgtools/trunk/zpkgsetup buildsupport/zpkgsetup

.PHONY: zpkgsetup-update
zpkgsetup-update:
	svn up buildsupport/zpkgsetup

.PHONY: checkout
checkout: zope3-checkout zpkgsetup-checkout

.PHONY: update
update: checkout zope3-update zpkgsetup-update

.PHONY: build
build: zope3-checkout zpkgsetup-checkout
	test -d Zope3 && cd Zope3 && $(PYTHON) setup.py build_ext -i
	$(PYTHON) setup.py $(SETUPFLAGS) \
                build_ext -i install_data --install-dir .
	$(PYTHON) bin/remove-stale-bytecode.py

.PHONY: clean
clean:
	find . \( -path './src/*.mo' -o -name '*.o' \
	         -o -name '*.py[co]' \) -exec rm -f {} \;
	rm -rf build

.PHONY: cleandb
cleandb:
	rm -f schooltool-skel/var/Data.fs*

.PHONY: realclean
realclean: clean cleandb
	find . \( -name '*.so' -o -name '*.pyd' \) -exec rm -f {} \;
	rm -f *.csv tags ID *.log
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
	$(PYTHON) test.py $(TESTFLAGS) -s src/schooltool -f --level 2

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
dist: realclean update-translations
	$(ZPKG) -x reportlab -C releases/SchoolTool.cfg

.PHONY: signtar
signtar: dist
	md5sum dist/SchoolTool*.tgz > dist/md5sum
	gpg --clearsign dist/md5sum
	mv dist/md5sum.asc dist/md5sum

.PHONY: extract-translations
extract-translations: build
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) i18nextract.py

.PHONY: update-translations
update-translations:
	set -e; \
	for domain in $(TRANSLATION_DOMAINS); do \
	    for f in $(LOCALES)/*/LC_MESSAGES/$${domain}.po; do \
		msgmerge -U $$f $(LOCALES)/$${domain}.pot ;\
		msgfmt -o $${f%.po}.mo $$f;\
	    done;\
	done

.PHONY: update-rosetta-pot
update-rosetta-pot:
	$(PYTHON) setup.py build
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
	    https://launchpad.ubuntu.com/products/schooltool/0.10-rc1/+pots/schooltool/+upload > ../launchpad_log2
	rm ../launchpad_cookies

.PHONY: get-rosetta-translations
get-rosetta-translations:
	# This needs to be vewy vewy quiet as it will probably be called by cron
	./utilities/get-rosetta-translations.py \
	    --baseurl $(ROSETTA_URL)\
	    --filepattern $(LOCALE_PATTERN)\
	    --loglevel='ERROR' $(ROSETTA_LOCALES)
