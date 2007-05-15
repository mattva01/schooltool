#!/usr/bin/make
#
# Makefile for SchoolTool
#
# $Id$

PYTHON=python2.4
TRANSLATION_DOMAINS=schoolbell schooltool
TESTFLAGS=-v
LOCALES=src/schooltool/locales/
PYTHONPATH:=$(PYTHONPATH):src:eggs
SETUPFLAGS=

.PHONY: all
all: build

.PHONY: build
build: 
	test -d eggs || mkdir eggs
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) setup.py develop -S eggs --install-dir eggs
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
	rm -rf dist
	rm -rf eggs

.PHONY: test
test: build
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) test.py $(TESTFLAGS) -u schooltool

.PHONY: testall
testall: build
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) test.py $(TESTFLAGS) 

.PHONY: ftest
ftest: build
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) test.py $(TESTFLAGS) -f --at-level 2 schooltool 

.PHONY: run
run: build
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) schooltool-server.py

.PHONY: coverage
coverage: build
	rm -rf coverage
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) test.py $(TESTFLAGS) --coverage=coverage schooltool
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

.PHONY: dist
dist: realclean extract-translations update-translations
	$(PYTHON) setup.py register sdist bdist_eg

.PHONY: dist/md5sum
dist/md5sum: dist
	# TODO: this can probably be a non _phony_ rue
	md5sum dist/schooltool*.tgz > dist/md5sum
	gpg --clearsign dist/md5sum
	mv dist/md5sum.asc dist/md5sum


.PHONY: signtar
signtar: dist/md5sum
	md5sum dist/schooltool*.tgz > dist/md5sum
	gpg --clearsign dist/md5sum
	mv dist/md5sum.asc dist/md5sum

.PHONY: extract-translations
extract-translations: build
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) i18nextract.py --domain=schooltool --zcml=`pwd`/schooltool-skel/etc/site.zcml
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) i18nextract.py --domain=schoolbell --zcml=`pwd`/schoolbell-site.zcml
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) i18nextract.py --domain=schooltool.commendation --zcml=`pwd`/src/schooltool/commendation/ftesting.zcml

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
