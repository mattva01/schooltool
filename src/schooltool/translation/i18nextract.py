#!/usr/bin/env python2.3
##############################################################################
#
# Loosely based on i18nextract.py from Zope 3.  Portions of extract.py were
# also incorporated and modified.  The original copyright message follows.
#
##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Program to extract internationalization markup from SchoolTool source tree.

Usage: i18nextracy.py [options] [path ...]

Options:
  -h, --help
            Print this message and exit.
  -d, --domain <domain>
            Specify the domain.  Only strings from this domain will be
            extracted from page templates.  The default is 'schooltool' and
            messages from the default domain.  This has no effect on strings
            that will be extracted from Python modules.
      --include-default-domain
            Include messages from the default domain as well as the domain
            specified with -d.  By default this is enabled when the domain is
            not explicitly specified on the command line.  If you want to
            enable this option, make sure it follows -d in the argument list.
  -o, --output <path>
            Specify the output file (default: '.', i.e. the current directory).
            If <path> specified is a directory, <domain>.pot will be appended.
            (Note that paths are relative to the current directory.  This
            differs from i18nextract.py used in Zope 3.)
  -b, --basedir <path>
            Specify the base directory that should be stripped from file name
            in comments.  If omitted, the longest common prefix will be
            stripped.
  <path>
            Specify a file or a directory to scan.  There can be more than one.
            (This is another difference from Zope's i18nextract.py: there's no
            -p option.)

            Note that files named 'extract.py' and 'pygettext.py' are excluded
            from directory scans.

$Id: i18nextract.py,v 1.4 2004/04/01 18:09:35 sidnei Exp $
"""

import os
import sys
import time
import getopt
import fnmatch
import tokenize
import traceback
from schooltool.translation.extract import POTMaker, TokenEater
from schooltool.translation.pygettext import make_escapes
from zope.tal.talgettext import POEngine, POTALInterpreter
from zope.tal.htmltalparser import HTMLTALParser


__metaclass__ = type

DEFAULT_CHARSET = 'UTF-8'
DEFAULT_ENCODING = '8bit'

pot_header = '''\
##############################################################################
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
##############################################################################
msgid ""
msgstr ""
"Project-Id-Version: %(version)s\\n"
"POT-Creation-Date: %(time)s\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: SchoolTool Developers <schooltool@schooltool.org>\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=%(charset)s\\n"
"Content-Transfer-Encoding: %(encoding)s\\n"
"Generated-By: schooltool/translation/i18nextract.py\\n"

'''


class SchoolToolPotMaker(POTMaker):
    """Gettext template (.pot) maker for SchoolTool."""

    def __init__(self, output_file):
        POTMaker.__init__(self, output_file, None)

    def _getProductVersion(self):
        """Return product version information to be included in the .pot."""
        try:
            import schooltool.main
            return schooltool.main.SERVER_VERSION
        except:
            return "SchoolTool (unknown version)"

    def write(self):
        file = open(self._output_filename, 'w')
        file.write(pot_header % {'time':     time.ctime(),
                                 'version':  self._getProductVersion(),
                                 'charset':  DEFAULT_CHARSET,
                                 'encoding': DEFAULT_ENCODING})

        # Sort the catalog entries by filename
        catalog = self.catalog.values()
        catalog.sort()

        # Write each entry to the file
        for entry in catalog:
            entry.write(file)

        file.close()


def find_files(dir, pattern, exclude=()):
    """Find files matching pattern from dir recursively.

    Returns an iterator.
    """
    for dirpath, dirnames, filenames in os.walk(dir):
        for name in fnmatch.filter(filenames, pattern):
            if name not in exclude:
                yield os.path.join(dirpath, name)


def py_strings(filenames, domain=None):
    """Return extracted strings from Python modules."""
    eater = TokenEater()
    for filename in filenames:
        fp = open(filename)
        try:
            eater.set_filename(filename)
            try:
                tokenize.tokenize(fp.readline, eater)
            except tokenize.TokenError, e:
                print >> sys.stderr, '%s: %s, line %d, column %d' % (
                    e[0], filename, e[1][0], e[1][1])
        finally:
            fp.close()
    # XXX: No support for domains yet :(
    return eater.getCatalog()


def tal_strings(filenames, domain="zope", include_default_domain=False):
    """Retrieve all TAL messages that are in the domain."""
    engine = POEngine()

    class Devnull:
        def write(self, s):
            pass

    for filename in filenames:
        try:
            engine.file = filename
            p = HTMLTALParser()
            p.parseFile(filename)
            program, macros = p.getCode()
            POTALInterpreter(program, macros, engine, stream=Devnull(),
                             metal=False)()
        except: # Hee hee, I love bare excepts!
            print >> sys.stderr, 'There was an error processing', filename
            traceback.print_exc()

    # See whether anything in the domain was found
    if not engine.catalog.has_key(domain):
        return {}
    # We do not want column numbers.
    catalog = engine.catalog[domain].copy()
    # When the Domain is 'default', then this means that none was found;
    # Include these strings; yes or no?
    if include_default_domain:
        catalog.update(engine.catalog['default'])
    for msgid, locations in catalog.items():
        catalog[msgid] = [(l[0], l[1][0]) for l in locations]
    return catalog


def guess_base_dir(filenames):
    """Return the longest common path prefix.

    Examples (assuming os.path.sep == '/'):

        >>> guess_base_dir(['/a/b/c.txt', '/a/b/d/e.txt'])
        '/a/b/'
        >>> guess_base_dir(['/a/b/c/d.txt', '/a/b/d/e.txt'])
        '/a/b/'
        >>> guess_base_dir(['/a/b/c/d.txt', '/x/y/z.txt'])
        ''
        >>> guess_base_dir(['/a/b/c.txt'])
        '/a/b/'
        >>> guess_base_dir([])
        ''

    """
    if not filenames:
        return ''

    def dirname(fn):
        """Return the dirname of fn including a trailing slash."""
        return os.path.dirname(fn) + os.path.sep
    longest_prefix = dirname(filenames[0])
    for fn in filenames[1:]:
        prefix = dirname(fn)
        while not prefix.startswith(longest_prefix):
            idx = longest_prefix.rfind(os.path.sep, 0, -1)
            if idx == -1:
                return ''
            longest_prefix = longest_prefix[:idx+1]
    return longest_prefix


def usage(code, msg=""):
    """Print the usage message, an error message (optional), and exit."""
    if msg:
        print >> sys.stderr, __doc__
        print >> sys.stderr, msg
    else:
        print __doc__
    sys.exit(code)


def main(argv=sys.argv):
    """Main."""
    try:
        opts, args = getopt.gnu_getopt(argv[1:], 'hd:o:b:',
                                       ['help', 'domain=', 'output=',
                                        'basedir=', 'include-default-domain'])
    except getopt.error, msg:
        usage(1, msg)

    domain = 'schooltool'
    include_default_domain = True
    path = '.'
    output_path = '.'
    base_dir = None
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt in ('-d', '--domain'):
            domain = arg
            include_default_domain = False
        elif opt in ('--include-default-domain'):
            include_default_domain = True
        elif opt in ('-o', '--output'):
            output_path = arg
        elif opt in ('-b', '--basedir'):
            base_dir = os.path.abspath(arg)

    if os.path.isdir(output_path):
        output_path = os.path.join(output_path, domain + '.pot')

    if base_dir is None:
        base_dir = guess_base_dir(map(os.path.abspath, args))
    else:
        base_dir = os.path.abspath(base_dir) + os.path.sep

    maker = SchoolToolPotMaker(output_path)
    make_escapes(0)  # mg: yuck
    for arg in args:
        path = os.path.abspath(arg)
        if os.path.isdir(path):
            python_files = find_files(path, '*.py',
                                      exclude=('extract.py', 'pygettext.py'))
            maker.add(py_strings(python_files, domain), base_dir)
            tal_files = find_files(path, '*.pt')
            maker.add(tal_strings(tal_files, domain, include_default_domain),
                      base_dir)
        elif path.endswith('.py'):
            maker.add(py_strings([path], domain), base_dir)
        elif path.endswith('.pt'):
            maker.add(tal_strings([path], domain, include_default_domain),
                      base_dir)
        else:
            usage(1, "%s is not a Python module or a Page Template" % path)
    maker.write()


if __name__ == '__main__':
    main()
