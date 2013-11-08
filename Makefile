#!/usr/bin/make

PACKAGE=schooltool
LOCALES=src/schooltool/locales
TRANSLATIONS_ZCML=schooltool/common/translations.zcml

DIST=/home/ftp/pub/schooltool/trunk
PYTHON=python

INSTANCE_TYPE=schooltool
BUILDOUT_FLAGS=
REDIS_PORT:=$$(grep ^port instance/redis.conf | cut -d' ' -f 2)

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

instance/run/supervisord.pid:
	bin/supervisord

.PHONY: run
run: build instance instance/run/supervisord.pid
	@bin/supervisorctl start "services:*"
	@bin/supervisorctl status schooltool | grep RUNNING && bin/supervisorctl stop schooltool || exit 0
	@bin/supervisorctl status
	REDIS_PORT=$(REDIS_PORT) bin/start-schooltool-instance instance

.PHONY: start
start: build instance instance/run/supervisord.pid
	bin/supervisorctl start all
	@bin/supervisorctl status

.PHONY: start-services
start-services: build instance instance/run/supervisord.pid
	@bin/supervisorctl status | grep services[:] | grep -v RUNNING && bin/supervisorctl start "services:*" || exit 0
	@bin/supervisorctl status | grep services[:]

.PHONY: restart
restart: build instance instance/run/supervisord.pid
	@bin/supervisorctl restart "services:celery_report"
	@bin/supervisorctl start "services:*"
	bin/supervisorctl restart schooltool
	@bin/supervisorctl status

.PHONY: rerun
rerun: build instance instance/run/supervisord.pid
	@bin/supervisorctl restart "services:celery_report"
	@bin/supervisorctl start "services:*"
	@bin/supervisorctl status schooltool | grep RUNNING && bin/supervisorctl stop schooltool || exit 0
	@bin/supervisorctl status
	REDIS_PORT=$(REDIS_PORT) bin/start-schooltool-instance instance

.PHONY: stop
stop:
	@test -S instance/run/supervisord.sock && bin/supervisorctl status | grep -v STOPPED && bin/supervisorctl stop all || exit 0
	@test -S instance/run/supervisord.sock && bin/supervisorctl shutdown || echo Nothing to stop
	@rm -f instance/run/zeo.sock
	@rm -f instance/run/supervisord.sock
	@rm -f instance/run/supervisord.pid

.PHONY: status
status:
	@test -f instance/run/supervisord.pid && bin/supervisorctl status || echo All services shut down

.PHONY: tags
tags: build
	bin/ctags

.PHONY: clean
clean: stop
	rm -rf python
	rm -rf bin develop-eggs parts .installed.cfg
	rm -rf build
	rm -f ID TAGS tags
	rm -rf coverage ftest-coverage
	rm -rf docs
	rm -rf instance/var/celerybeat-schedule
	rm -rf instance/var/redis-dump.rdb
	rm -rf instance/run/zeo.sock
	rm -rf instance/run/supervisord.sock
	rm -rf instance/run/supervisord.pid
	rm -rf instance/var/Data.fs.lock
	find . -name '*.py[co]' -delete
	find . -name '*.mo' -delete
	find . -name 'LC_MESSAGES' -exec rmdir -p --ignore-fail-on-non-empty {} +

.PHONY: realclean
realclean: stop
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
	set -e ;\
	for f in $(LOCALES)/*.po; do \
	    mkdir -p $${f%.po}/LC_MESSAGES; \
	    msgfmt -o $${f%.po}/LC_MESSAGES/$(PACKAGE).mo $$f;\
	done

.PHONY: update-translations
update-translations:
	set -e ;\
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
	set -e ;\
	VERSION=`cat version.txt.in` ;\
	DIST=$(DIST) ;\
	grep -qv 'dev' version.txt.in || VERSION=`cat version.txt.in`-r`bzr revno` ;\
	grep -qv 'dev' version.txt.in || DIST=$(DIST)/dev ;\
	if [ -w $${DIST} ] ; then \
	    echo cp dist/$(PACKAGE)-$${VERSION}.tar.gz $${DIST} ;\
	    cp dist/$(PACKAGE)-$${VERSION}.tar.gz $${DIST} ;\
	else \
	    echo scp dist/$(PACKAGE)-$${VERSION}.tar.gz* ftp.schooltool.org:$${DIST} ;\
	    scp dist/$(PACKAGE)-$${VERSION}.tar.gz* ftp.schooltool.org:$${DIST} ;\
	fi

# Helpers

.PHONY: ubuntu-environment
ubuntu-environment:
	sudo apt-get install build-essential gettext enscript \
	    python-dev python-virtualenv \
	    ttf-ubuntu-font-family ttf-liberation \
	    libicu-dev libxslt1-dev libfreetype6-dev libjpeg-dev \
	    redis-server

