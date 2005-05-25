#!/usr/bin/make
#
# Makefile for SchoolBell
#
# $Id$

PYTHON=python2.3
TESTFLAGS=-w1
POT=src/schoolbell/app/locales/schoolbell.pot
PO=$(wildcard src/schoolbell/app/locales/*/LC_MESSAGES/*.po)
PYTHONPATH=src:Zope3/src

.PHONY: all
all: build

.PHONY: build
build:
	cd Zope3 && $(PYTHON) setup.py build_ext -i
	$(PYTHON) remove-stale-bytecode.py

.PHONY: clean
clean:
	find . \( -name '*.o' -o -name '*.py[co]' \) -exec rm -f {} \;
	rm -rf build

.PHONY: realclean
realclean: clean
	find . \( -name '*.so' -o -name '*.pyd' \) -exec rm -f {} \;
	rm -f Data.fs* tags ID *.log
	rm -f MANIFEST
	rm -rf dist

.PHONY: build
test: build
	LC_ALL="C" $(PYTHON) test.py $(TESTFLAGS)

.PHONY: ftest
ftest: build
	$(PYTHON) test.py -f $(TESTFLAGS)

.PHONY: run
run: build
	$(PYTHON) schoolbell-server.py

Zope3/principals.zcml:
	cp Zope3/sample_principals.zcml $@

Zope3/package-includes/schoolbell-configure.zcml:
	echo '<include package="schoolbell.app" />' > $@

.PHONY: schoolbelldist
schoolbelldist: realclean build extract-translations update-translations clean
	rm -rf dist
	find . -name '*.py[dco]' -exec rm -f {} \;
	fakeroot ./debian/rules clean
	./setup.py sdist --formats=gztar

.PHONY: signtar
signtar: dist
	md5sum dist/school*.tar.gz > dist/md5sum
	gpg --clearsign dist/md5sum
	mv dist/md5sum.asc dist/md5sum

.PHONY: extract-translations
extract-translations: Zope3/principals.zcml Zope3/package-includes/schoolbell-configure.zcml
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) \
		Zope3/utilities/i18nextract.py -d schoolbell \
			-o app/locales -p src/schoolbell schoolbell

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
	    -F "file=@src/schoolbell/app/locales/schoolbell.pot" \
	    -F "UPLOAD=Upload" \
	    https://launchpad.ubuntu.com/products/schoolbell/unknown/+pots/schoolbell-ui/+edit > ../launchpad_log2
	rm ../launchpad_cookies

.PHONY: get-rosetta-translations
get-rosetta-translations:
	./get-rosetta-translations.py
	$(MAKE) update-translations
