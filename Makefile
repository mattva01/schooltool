#!/usr/bin/make

PACKAGE=schooltool
LOCALES=src/schooltool/locales
TRANSLATIONS_ZCML=schooltool/common/translations.zcml

DIST=/home/ftp/pub/schooltool/flourish
PYTHON=python

INSTANCE_TYPE=schooltool
BUILDOUT_FLAGS=

.PHONY: all
all: build

.PHONY: build
build: .installed.cfg

python:
	rm -rf python
	virtualenv --no-site-packages -p $(PYTHON) python

.PHONY: bootstrap
bootstrap bin/buildout: | buildout.cfg python
	python/bin/python bootstrap.py

buildout.cfg:
	cp deploy.cfg buildout.cfg

.PHONY: buildout
buildout .installed.cfg: python bin/buildout buildout.cfg base.cfg deploy.cfg setup.py
	bin/buildout $(BUILDOUT_FLAGS)

.PHONY: develop
develop bin/coverage bin/docs: buildout.cfg develop.cfg
	sed -e 's/base.cfg/develop.cfg/' -i buildout.cfg
	$(MAKE) buildout

.PHONY: update
update:
	bzr up
	$(MAKE) buildout BUILDOUT_FLAGS=-n

instance: | build
	bin/make-schooltool-instance instance instance_type=$(INSTANCE_TYPE)

.PHONY: run
run: build instance
	bin/start-schooltool-instance instance

.PHONY: tags
tags: build
	bin/ctags

.PHONY: clean
clean:
	rm -rf python
	rm -rf bin develop-eggs parts .installed.cfg
	rm -rf build
	rm -f ID TAGS tags
	rm -rf coverage ftest-coverage
	rm -rf docs
	find . -name '*.py[co]' -delete
	find . -name '*.mo' -delete
	find . -name 'LC_MESSAGES' -exec rmdir -p --ignore-fail-on-non-empty {} +

.PHONY: realclean
realclean:
	rm -f buildout.cfg
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
	rm -rf coverage
	bin/test --at-level 2 -u --coverage=$(CURDIR)/coverage

.PHONY: coverage-reports-html
coverage-reports-html coverage/reports: bin/coverage build
	test -d coverage || $(MAKE) coverage
	rm -rf coverage/reports
	mkdir coverage/reports
	bin/coverage coverage coverage/reports
	ln -s $(PACKAGE).html coverage/reports/index.html

.PHONY: ftest-coverage
ftest-coverage: build
	rm -rf ftest-coverage
	bin/test --at-level 2 -f --coverage=$(CURDIR)/ftest-coverage

.PHONY: ftest-coverage-reports-html
ftest-coverage-reports-html ftest-coverage/reports: bin/coverage build
	test -d ftest-coverage || $(MAKE) ftest-coverage
	rm -rf ftest-coverage/reports
	mkdir ftest-coverage/reports
	bin/coverage ftest-coverage ftest-coverage/reports
	ln -s $(PACKAGE).html ftest-coverage/reports/index.html

# Translations

.PHONY: extract-translations
extract-translations: build
	bin/i18nextract --egg $(PACKAGE) \
	                --domain $(PACKAGE) \
	                --zcml $(TRANSLATIONS_ZCML) \
	                --output-file $(LOCALES)/$(PACKAGE).pot

.PHONY: compile-translations
compile-translations:
	for f in $(LOCALES)/*.po; do \
	    mkdir -p $${f%.po}/LC_MESSAGES; \
	    msgfmt -o $${f%.po}/LC_MESSAGES/$(PACKAGE).mo $$f;\
	done

.PHONY: update-translations
update-translations:
	for f in $(LOCALES)/*.po; do \
	    msgmerge -qUN $$f $(LOCALES)/$(PACKAGE).pot ;\
	done
	$(MAKE) compile-translations

# Docs

docs: bin/docs build
	bin/docs

# Release

.PHONY: release
release: compile-translations
	-cp buildout.cfg buildout.cfg~dev~
	cp deploy.cfg buildout.cfg
	grep -qv 'dev' version.txt.in || echo -n `cat version.txt.in`-r`bzr revno` > version.txt
	$(PYTHON) setup.py sdist
	rm -f version.txt
	-mv buildout.cfg~dev~ buildout.cfg

.PHONY: move-release
move-release: upload
	rm -v dist/$(PACKAGE)-*dev-r*.tar.gz

.PHONY: upload
upload:
	@VERSION=`cat version.txt.in` ;\
	DIST=$(DIST) ;\
	grep -qv 'dev' version.txt.in || VERSION=`cat version.txt.in`-r`bzr revno` ;\
	grep -qv 'dev' version.txt.in || DIST=$(DIST)/dev ;\
	if [ -w $${DIST} ] ; then \
	    echo cp dist/$(PACKAGE)-$${VERSION}.tar.gz $${DIST} ;\
	    cp dist/$(PACKAGE)-$${VERSION}.tar.gz $${DIST} ;\
	else \
	    echo scp dist/$(PACKAGE)-$${VERSION}.tar.gz* schooltool.org:$${DIST} ;\
	    scp dist/$(PACKAGE)-$${VERSION}.tar.gz* schooltool.org:$${DIST} ;\
	fi

# Helpers

.PHONY: ubuntu-environment
ubuntu-environment:
	sudo apt-get install bzr build-essential gettext enscript ttf-liberation \
	    python-all-dev python-virtualenv ttf-ubuntu-font-family \
	    libicu-dev libxslt1-dev libfreetype6-dev libjpeg62-dev

