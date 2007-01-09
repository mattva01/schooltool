#!/usr/bin/make
#
# Makefile for SchoolTool
#
# $Id$

PYTHON=python
ZPKG=../../zpkgtools/bin/zpkg
TRANSLATION_DOMAINS=schoolbell schooltool
ZOPE_REPOSITORY=svn://svn.zope.org/repos/main/
ZOPE_HTML_REPOSITORY=svn://svn.zope.org/repos/main/zope.html/
ZOPE_FILE_REPOSITORY=svn://svn.zope.org/repos/main/zope.file/
ZOPE_MIMETYPE_REPOSITORY=svn://svn.zope.org/repos/main/zope.mimetype/
TESTFLAGS=-v
LOCALES=src/schooltool/locales/
PYTHONPATH:=$(PYTHONPATH):src:Zope3/src
SETUPFLAGS=

# Which part of the Zope3 repository do we track
#Z3_VERSION=trunk
Z3_VERSION=branches/3.3
#Z3_VERSION=tags/3.2.0

.PHONY: all
all: build

.PHONY: zope3-checkout
zope3-checkout:
	-test -d Zope3 || svn co $(ZOPE_REPOSITORY)/Zope3/${Z3_VERSION} Zope3

.PHONY: zope3-update
zope3-update:
	svn up Zope3

.PHONY: zope-addons-checkout
zope-addons-checkout:
	-test -d Zope3/src/zope/html || svn co $(ZOPE_HTML_REPOSITORY)/trunk/src/zope/html Zope3/src/zope/html
	-test -d Zope3/src/zope/file || svn co $(ZOPE_FILE_REPOSITORY)/trunk/src/zope/file Zope3/src/zope/file
	-test -d Zope3/src/zope/mimetype || svn co $(ZOPE_MIMETYPE_REPOSITORY)/trunk/src/zope/mimetype Zope3/src/zope/mimetype

.PHONY: zope-addons-update
zope-addons-update:
	svn up Zope3/src/zope/html
	svn up Zope3/src/zope/file
	svn up Zope3/src/zope/mimetype

.PHONY: zpkgsetup-checkout
zpkgsetup-checkout:
	-test -d buildsupport/zpkgsetup || svn co $(ZOPE_REPOSITORY)/zpkgtools/trunk/zpkgsetup buildsupport/zpkgsetup

.PHONY: zpkgsetup-update
zpkgsetup-update:
	svn up buildsupport/zpkgsetup

.PHONY: checkout
checkout: zope3-checkout zpkgsetup-checkout zope-addons-checkout

.PHONY: update
update: checkout zope3-update zpkgsetup-update zope-addons-update

.PHONY: build
build: zope3-checkout zpkgsetup-checkout zope-addons-checkout
	test -d Zope3 && cd Zope3 && $(PYTHON) setup.py build_ext -i
	$(PYTHON) setup.py $(SETUPFLAGS) \
                build_ext -i install_data --install-dir .
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) setup.eggs.py develop -S src --install-dir src
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
	$(PYTHON) test.py $(TESTFLAGS) -u schooltool

.PHONY: testall
testall: build
	$(PYTHON) test.py $(TESTFLAGS) 

.PHONY: ftest
ftest: build
	$(PYTHON) test.py $(TESTFLAGS) -f --at-level 2 schooltool 

.PHONY: run
run: build
	$(PYTHON) schooltool-server.py

.PHONY: coverage
coverage: build
	rm -rf coverage
	$(PYTHON) test.py $(TESTFLAGS) --coverage=coverage -s src/schooltool

.PHONY: coverage-reports-html
coverage-reports-html:
	rm -rf coverage/reports
	mkdir coverage/reports
	$(PYTHON) bin/coverage_reports.py coverage coverage/reports
	ln -s schooltool.html coverage/reports/index.html

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
		msgmerge -qU $$f $(LOCALES)/$${domain}.pot ;\
		msgfmt -o $${f%.po}.mo $$f;\
	    done;\
	done

#
# Makefile rules for importing and exporting translations to rosetta:
#
# To create a translation templates (schooltool.pot, schoolbell.pot) for
# uploading to rosetta:
#
# 	1. run 'make extract-translations'
# 	2. upload the src/schooltool/locales/{schoolbell,schooltool}.pot files
# 	   to rosetta.
#
# To create tarballs suitable for uploading to rosetta:
#
# 	The following command will create tarballs in the current directory of
# 	the form {schooltool,schoolbell}-translations.tar.gz. These should be
# 	suitable for uploading to rosetta.
#
# 	$ make translation-tarballs
# 	
# 	WARNING: Only do this if you are _sure_ you want to. you risk
# 	overwiting translations that have been changed in rosetta. Normally it
# 	is only necessary to upload *.pot files.
#
# To import translations from rosetta:
#
#	1. get a clean checkout of schooltool
# 	2. download the tarballs of exportd PO files from rosetta and rename
# 	   them to rosetta-schooltool.tar.gz and rosetta-schoolbell.tar.gz
# 	3. run 'make update-rosetta-translations'
# 	4. use svn to add and commit any new/changed translations
#


.PHONY:create-translation-tarball
create-translation-tarball:
	#extract-translations update-translations
	[ ! -e translations.tmp ] || \
	    { echo ERROR: cowardly refusing to continue because translations.tmp exists; exit 1; }
	mkdir translations.tmp
	cp $(LOCALES)/$(DOMAIN).pot translations.tmp/template.pot
	dir=`pwd` && cd $(LOCALES) && \
	    find * -maxdepth 0 -type d \
	    -exec cp {}/LC_MESSAGES/$(DOMAIN).po $${dir}/translations.tmp/{}.po \;
	cd translations.tmp && tar -czf ../$(DOMAIN)-translations.tar.gz *
	rm -rf translations.tmp

.PHONY: translation-tarballs
translation-tarballs: extract-translations update-translations
	$(MAKE) DOMAIN=schooltool create-translation-tarball
	$(MAKE) DOMAIN=schoolbell create-translation-tarball

.PHONY: extract-rosetta-tarball
extract-rosetta-tarball:
	[ -e rosetta-$(DOMAIN).tar.gz ]
	[ ! -e translations.tmp ] || \
	    { echo ERROR: cowardly refusing to continue because translations.tmp exists; exit 1; }
	mkdir translations.tmp
	cd translations.tmp && tar -xzf ../rosetta-$(DOMAIN).tar.gz && mv */* .
	set -e; for file in translations.tmp/*.po; do \
	    dir=$(LOCALES)/`basename $${file} .po`/LC_MESSAGES; \
	    [ -x $${dir} ] || mkdir -p $${dir}; \
	    cp $${file} $${dir}/$(DOMAIN).po; \
	    echo Updating $${dir}/$(DOMAIN).po; \
	done
	rm -rf translations.tmp

.PHONY: update-rosetta-translations
update-rosetta-translations:
	[ ! -e rosetta-schooltool.tar.gz ] || $(MAKE) DOMAIN=schooltool extract-rosetta-tarball
	[ ! -e rosetta-schoolbell.tar.gz ] || $(MAKE) DOMAIN=schoolbell extract-rosetta-tarball
	$(MAKE) PYTHON=$(PYTHON) extract-translations update-translations
	# remove .po~ and .mo files so they are not accidentally committed
	find $(LOCALES) \( -name '*.po~' -o -name '*.mo' \) -exec rm -f {} \;
