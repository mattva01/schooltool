#!/usr/bin/env python
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005    Shuttleworth Foundation
#                       Brian Sutherland
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Script to download the latest translations from rosetta.

It assumes that rosetta is the cannonical source of translations.
"""

import os
import urllib2
import optparse
import logging
import tempfile
import subprocess

class POVerificationError(Exception):
    """To be raised when verification of a PO file fails."""


class FileWriter:
    """Write PO files to disk.

    Verifies a PO file and writes it to disk according to a filename pettern
    based on its locale.
    """

    open = open

    def __init__(self, pathnamepattern, config):
        self.pathnamepattern = pathnamepattern
        self.logger = logging
        self.config = config

    def _testsize(self, po, locale):
        r"""Raises error if no of lines of the new po file is <50% of the old.

        Get a writer:

            >>> writer = FileWriter(os.path.join('tmp', '@locale@', 'po.po'),
            ...     'ConfigStub')

        Stub some things:

            >>> def existsStub(dir):
            ...     return not dir == os.path.join('tmp', 'se', 'po.po')
            >>> old_exists = os.path.exists
            >>> os.path.exists = existsStub
            >>> class OpenStub:
            ...     def __init__(self, filename, perm):
            ...         self.filename = filename
            ...         self.perm = perm
            ...     def read(self):
            ...         print "FileRead: %s\nPermissions: %s"\
            ...             % (self.filename, self.perm)
            ...         return "\n".join(["" for i in range(22)])
            ...     def close(self):
            ...         pass
            >>> writer.open = OpenStub

        Test a small PO file:

            >>> po = "\n".join(["" for i in range(11)])
            >>> writer._testsize(po, 'es_ES')
            Traceback (most recent call last):
                ...
            POVerificationError: New es_ES PO file is suspiciously smaller.

        Test a bigger PO file:

            >>> po = "\n".join(["" for i in range(12)])
            >>> writer._testsize(po, 'es')
            FileRead: tmp/es/po.po
            Permissions: r

        Make sure we don't try to read non-existent files:

            >>> po = "\n".join(["" for i in range(22)])
            >>> writer._testsize(po, 'se')

        Cleanup:
            >>> os.path.exists = old_exists
        """
        filename = self.pathnamepattern.replace("@locale@", locale)
        if not os.path.exists(filename):
            return
        file = self.open(filename, 'r')
        oldpo = file.read()
        file.close()
        if (0.5 * len(oldpo.splitlines())) > len(po.splitlines()):
            raise POVerificationError("New %s PO file is suspiciously smaller."
                    % locale)

    def _testcompile(self, po, locale):
        r"""Tries to compile the po file using msgfmt, raising an error on fail.

        Get a writer:

            >>> writer = FileWriter(os.path.join('tmp', '@locale@', 'po.po'),
            ...     'ConfigStub')

        Write a non-compiling PO file:

            >>> po = r'msgid ""' + '\n' +\
            ...     r'"\n"' + '\n' +\
            ...     r'"This is not a SchoolBelldatabase\n"' + '\n' +\
            ...     r'msgstr ""' + '\n' +\
            ...     r'"Esto no es una base de datos de Schoolbell\n"' + '\n'

        Test it:

            >>> writer._testcompile(po, 'es')
            Traceback (most recent call last):
                ...
            POVerificationError: PO file for es fails to compile with error:
            <stdin>:1: `msgid' and `msgstr' entries do not both begin with '\n'
            msgfmt: found 1 fatal error
            <BLANKLINE>

        Write a compiling PO file:

            >>> po = r'msgid ""' + '\n' +\
            ...     r'"This is not a SchoolBelldatabase\n"' + '\n' +\
            ...     r'msgstr ""' + '\n' +\
            ...     r'"Esto no es una base de datos de Schoolbell\n"' + '\n'

        Test it:

            >>> writer._testcompile(po, 'es')
        """
        pofile = tempfile.NamedTemporaryFile() # XXX - must be a better way
        pofile.write(po)
        pofile.seek(0)
        p = subprocess.Popen(['msgfmt', '-o', '-', '-'], stdin=pofile,
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if  p.wait() != 0:
            raise POVerificationError("PO file for %s fails to compile "
                    "with error:\n%s" % (locale, p.stderr.read()))

    def runTests(self, po, locale):
        """Raises POVerificationError if new PO file fails tests.

            >>> class ConfigStub:
            ...     testcompile = True
            ...     testsize = False

        Get a writer:

            >>> writer = FileWriter(os.path.join('tmp', '@locale@', 'po.po'),
            ...     ConfigStub())

        Some stubs:
            >>> def testcompile(po, locale):
            ...     print 'compilation tested locale %s' % locale
            >>> writer._testcompile = testcompile
            >>> def testsize(po, locale):
            ...     print 'size tested locale %s' % locale
            >>> writer._testsize = testsize

        Tests:

            >>> writer.runTests("hi", "es")
            compilation tested locale es
            >>> writer.config.testcompile = False
            >>> writer.config.testsize = True
            >>> writer.runTests("hi", "es")
            size tested locale es
        """
        if self.config.testcompile:
            self._testcompile(po, locale)
        if self.config.testsize:
            self._testsize(po, locale)

    def write(self, po, locale):
        r"""Write the po file to disk.

        Get a writer:

            >>> writer = FileWriter(os.path.join('tmp', '@locale@', 'po.po'),
            ...     'ConfigStub')

        Stub some stuff:

            >>> def runTests(po, locale):
            ...     print 'tested locale %s' % locale
            >>> writer.runTests = runTests
            >>> class OpenStub:
            ...     def __init__(self, filename, perm):
            ...         self.filename = filename
            ...         self.perm = perm
            ...     def write(self, data):
            ...         print "File: %s\nPermissions: %s\nContents: %s"\
            ...             % (self.filename, self.perm, data)
            ...     def close(self):
            ...         pass
            >>> writer.open = OpenStub
            >>> class logger:
            ...     def info(self, msg):
            ...         print 'INFO: %s' % msg
            >>> writer.logger = logger()
            >>> def mkdirStub(dir):
            ...     print "Created: %s" % dir
            >>> old_makedirs = os.makedirs
            >>> os.makedirs = mkdirStub
            >>> def existsStub(dir):
            ...     return dir == os.path.join('tmp', 'es_ZA')
            >>> old_exists = os.path.exists
            >>> os.path.exists = existsStub

        Write some locales:

            >>> writer.write('I am the es_ZA po file.', 'es_ZA')
            tested locale es_ZA
            File: tmp/es_ZA/po.po
            Permissions: w
            Contents: I am the es_ZA po file.
            INFO: Written locale es_ZA to tmp/es_ZA/po.po
            >>> writer.write('I am the es po file.', 'es')
            tested locale es
            Created: tmp/es
            File: tmp/es/po.po
            Permissions: w
            Contents: I am the es po file.
            INFO: Written locale es to tmp/es/po.po

        Cleanup:
            >>> os.makedirs = old_makedirs
            >>> os.path.exists = old_exists
        """
        self.runTests(po, locale)
        filename = self.pathnamepattern.replace("@locale@", locale)
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        file = self.open(filename, 'w')
        file.write(po)
        file.close()
        self.logger.info('Written locale %s to %s' % (locale, filename))


class RosettaConnection:
    """Represents a rosetta source."""

    stream_factory = urllib2
    logger = logging

    def __init__(self, baseurl):
        """Set up a connection where baseurl is the location in the rosetta.

        e.g. baseurl =
             "https://launchpad.ubuntu.com/products/myproduct/1.0/+pots"
        """
        self.baseurl = baseurl
        self.config = config

    def getPO(self, locale):
        """Return the translation for a locale as a string.

        Get a connection:

            >>> con = RosettaConnection("https://somerosetta")

        First we can stub the stream factory:

            >>> class URLStub:
            ...     def __init__(self, url):
            ...         self.url = url
            ...     def read(self):
            ...         return "I am: " + self.url
            ...     def close(self):
            ...         pass
            ...     @staticmethod
            ...     def urlopen(url):
            ...         return URLStub(url)
            >>> con.stream_factory = URLStub
            >>> class logger:
            ...     def info(self, msg):
            ...         print 'INFO: %s' % msg
            >>> con.logger = logger()

        Then we try to get two translations:

            >>> for locale in ['fr', 'es_CO']:
            ...    con.getPO(locale)
            INFO: Read locale fr from https://somerosetta/fr/+po
            'I am: https://somerosetta/fr/+po'
            INFO: Read locale es_CO from https://somerosetta/es_CO/+po
            'I am: https://somerosetta/es_CO/+po'
        """
        url = self.baseurl + '/' + locale + '/+po'
        url_obj = self.stream_factory.urlopen(url)
        po = url_obj.read()
        url_obj.close()
        self.logger.info("Read locale %s from %s" % (locale, url))
        return po


class ImportExport:
    """Iterates over locales importing them from rosetta nad writing to disk."""

    importer_hook = RosettaConnection
    exporter_hook = FileWriter
    logger = logging

    def run(self, config, locales):
        r"""Import a list of locales.

        get an ImportExport object:

            >>> impexp = ImportExport()

        Stub everything:

            >>> class ImporterStub:
            ...     def __init__(self, baseurl):
            ...         self.baseurl = baseurl
            ...     def getPO(self, locale):
            ...         return "locale %s from %s" % (locale, self.baseurl)
            >>> impexp.importer_hook = ImporterStub
            >>> class ExporterStub:
            ...     def __init__(self, pattern, config, create_dir=True):
            ...         self.pattern = pattern
            ...     def write(self, po, locale):
            ...         if locale == "en_ZA":
            ...             raise IOError("Cannot write en_ZA")
            ...         print "writing locale %s:\nTo:%s" %\
            ...             (locale, self.pattern)
            >>> impexp.exporter_hook = ExporterStub
            >>> class logger:
            ...     def debug(self, msg):
            ...         print 'DEBUG: %s' % msg
            ...     def info(self, msg):
            ...         print 'INFO: %s' % msg
            ...     def exception(self, msg):
            ...         print 'EXCEPTION: %s' % msg
            >>> impexp.logger = logger()
            >>> class ConfigStub:
            ...     baseurl = 'http://there'
            ...     filepattern = '/mydir/@locale@/there'
            >>> config = ConfigStub()

        Now get some locales:

            >>> impexp.run(config, ['es', 'en_ZA'])
            INFO: Importing es
            writing locale es:
            To:/mydir/@locale@/there
            DEBUG: PO file contents: locale es from http://there
            INFO: Importing en_ZA
            EXCEPTION: Failed to import locale en_ZA
        """
        importer = self.importer_hook(config.baseurl)
        exporter = self.exporter_hook(config.filepattern, config)
        for locale in locales:
            try:
                self.logger.info("Importing %s" % locale)
                po = importer.getPO(locale)
                exporter.write(po, locale)
                self.logger.debug("PO file contents: %s" % po)
            except:
                self.logger.exception("Failed to import locale %s" % locale)


def parseOptions():
    """Parse the arguments.

    Save the old args.
        >>> import sys
        >>> old_args = sys.argv

    Defaults:
        >>> sys.argv = ['myprog']
        >>> (options, locales) = parseOptions()
        >>> options.test
        False
        >>> options.baseurl is None
        True
        >>> options.filepattern is None
        True
        >>> options.loglevel
        'INFO'
        >>> options.testcompile
        True
        >>> options.testsize
        True

    Some settings:
        >>> sys.argv = ['myprog', '--test', 'ca',
        ...     '--filepattern', '/root/@locale@', 'en_ZA',
        ...     '--baseurl', 'http://somehost/rosetta',
        ...     '-l', 'DEBUG', '--notestcompile', '--notestsize']
        >>> (options, locales) = parseOptions()
        >>> options.test
        True
        >>> locales
        ['ca', 'en_ZA']
        >>> options.baseurl
        'http://somehost/rosetta'
        >>> options.filepattern
        '/root/@locale@'
        >>> options.loglevel
        'DEBUG'
        >>> options.testcompile
        False
        >>> options.testsize
        False

    Cleanup:
        >>> sys.argv = old_args
    """
    # TODO - filepattern and baseurl are essential, this function needs to fail
    parser = optparse.OptionParser(usage="usage: %prog [options] [locale...]")
    parser.add_option("-t", "--test", dest="test", action="store_true",
                      default=False, help="run self tests")
    parser.add_option("--notestcompile", dest="testcompile",
                      action="store_false", default=True,
                      help="do not test the PO file by checking if compilation"
                      " with msgfmt succeeds")
    parser.add_option("--notestsize", dest="testsize",
                      action="store_false", default=True,
                      help="do not test the PO file by checking if the new no"
                      " of lines are less than 50% of the old")
    parser.add_option("--filepattern", dest="filepattern",
                      help="The file pattern to write to, the locale name "
                      "will replace any instances of @locale@.")
    parser.add_option("--baseurl", dest="baseurl",
                      help="The base url of the rosetta page to use, will be"
                      " extended by @locale@/po to get the PO file.")
    parser.add_option("-l", "--loglevel", dest="loglevel", default="INFO",
                      help="The level of logging, see the logging module")
    return parser.parse_args()

def main(config, locales):
    logging.basicConfig(level=getattr(logging, config.loglevel))
    importer = ImportExport()
    importer.run(config, locales)

if __name__ == "__main__":
    (config, locales) = parseOptions()
    if config.test:
        import doctest
        doctest.testmod(verbose=True)
    else:
        main(config, locales)
