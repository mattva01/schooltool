#!/usr/bin/env python
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Driver program to test METAL and TAL implementation.

Usage: driver.py [options] [file]
Options:
    -h / --help
        Print this message and exit.
    -H / --html
    -x / --xml
        Explicitly choose HTML or XML input.  The default is to automatically
        select based on the file extension.  These options are mutually
        exclusive.
    -l
        Lenient structure insertion.
    -m
        Macro expansion only
    -s
        Print intermediate opcodes only
    -t
        Leave TAL/METAL attributes in output
    -i
        Leave I18N substitution strings un-interpolated.
    -a
        Enable source annotations

$Id$
"""

import os
import sys

import getopt

if __name__ == "__main__":
    import setpath                      # Local hack to tweak sys.path etc.

# Import local classes
import zope.tal.taldefs
from zope.tal.dummyengine import DummyEngine
from zope.tal.dummyengine import DummyTranslationDomain

FILE = "tests/input/test01.xml"

class TestTranslations(DummyTranslationDomain):
    def translate(self, msgid, mapping=None, context=None,
                  target_language=None, default=None):
        if msgid == 'timefmt':
            return '%(minutes)s minutes after %(hours)s %(ampm)s' % mapping
        elif msgid == 'jobnum':
            return '%(jobnum)s is the JOB NUMBER' % mapping
        elif msgid == 'verify':
            s = 'Your contact email address is recorded as %(email)s'
            return s % mapping
        elif msgid == 'mailto:${request/submitter}':
            return 'mailto:bperson@dom.ain'
        elif msgid == 'origin':
            return '%(name)s was born in %(country)s' % mapping
        return DummyTranslationDomain.translate(
            self, msgid, mapping, context,
            target_language, default=default)


class TestEngine(DummyEngine):
    def __init__(self, macros=None):
        DummyEngine.__init__(self, macros)
        self.translationDomain = TestTranslations()

    def evaluatePathOrVar(self, expr):
        if expr == 'here/currentTime':
            return {'hours'  : 6,
                    'minutes': 59,
                    'ampm'   : 'PM',
                    }
        elif expr == 'context/@@object_name':
            return '7'
        elif expr == 'request/submitter':
            return 'aperson@dom.ain'
        return DummyEngine.evaluatePathOrVar(self, expr)


# This is a disgusting hack so that we can use engines that actually know
# something about certain object paths.  TimeEngine knows about
# here/currentTime.
ENGINES = {'test23.html': TestEngine,
           'test24.html': TestEngine,
           'test26.html': TestEngine,
           'test27.html': TestEngine,
           'test28.html': TestEngine,
           'test29.html': TestEngine,
           'test30.html': TestEngine,
           'test31.html': TestEngine,
           'test32.html': TestEngine,
           }

def usage(code, msg=''):
    print >> sys.stderr, __doc__
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)

def main():
    macros = 0
    mode = None
    showcode = 0
    showtal = -1
    sourceAnnotations = 0
    strictinsert = 1
    i18nInterpolate = 1
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hHxlmstia",
                                   ['help', 'html', 'xml'])
    except getopt.error, msg:
        usage(2, msg)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        if opt in ('-H', '--html'):
            if mode == 'xml':
                usage(1, '--html and --xml are mutually exclusive')
            mode = "html"
        if opt == '-l':
            strictinsert = 0
        if opt == '-m':
            macros = 1
        if opt in ('-x', '--xml'):
            if mode == 'html':
                usage(1, '--html and --xml are mutually exclusive')
            mode = "xml"
        if opt == '-s':
            showcode = 1
        if opt == '-t':
            showtal = 1
        if opt == '-i':
            i18nInterpolate = 0
        if opt == '-a':
            sourceAnnotations = 1
    if args:
        file = args[0]
    else:
        file = FILE
    it = compilefile(file, mode)
    if showcode:
        showit(it)
    else:
        # See if we need a special engine for this test
        engine = None
        engineClass = ENGINES.get(os.path.basename(file))
        if engineClass is not None:
            engine = engineClass(macros)
        interpretit(it, engine=engine,
                    tal=(not macros), showtal=showtal,
                    strictinsert=strictinsert,
                    i18nInterpolate=i18nInterpolate,
                    sourceAnnotations=sourceAnnotations)

def interpretit(it, engine=None, stream=None, tal=1, showtal=-1,
                strictinsert=1, i18nInterpolate=1, sourceAnnotations=0):
    from zope.tal.talinterpreter import TALInterpreter
    program, macros = it
    assert zope.tal.taldefs.isCurrentVersion(program)
    if engine is None:
        engine = DummyEngine(macros)
    TALInterpreter(program, macros, engine, stream, wrap=0,
                   tal=tal, showtal=showtal, strictinsert=strictinsert,
                   i18nInterpolate=i18nInterpolate,
                   sourceAnnotations=sourceAnnotations)()

def compilefile(file, mode=None):
    assert mode in ("html", "xml", None)
    if mode is None:
        ext = os.path.splitext(file)[1]
        if ext.lower() in (".html", ".htm"):
            mode = "html"
        else:
            mode = "xml"
    from zope.tal.talgenerator import TALGenerator
    filename = os.path.abspath(file)
    prefix = os.path.dirname(os.path.abspath(__file__)) + os.path.sep
    if filename.startswith(prefix):
        filename = filename[len(prefix):]
    filename = filename.replace(os.sep, '/') # test files expect slashes
    if mode == "html":
        from zope.tal.htmltalparser import HTMLTALParser
        p = HTMLTALParser(gen=TALGenerator(source_file=filename, xml=0))
    else:
        from zope.tal.talparser import TALParser
        p = TALParser(gen=TALGenerator(source_file=filename))
    p.parseFile(file)
    return p.getCode()

def showit(it):
    from pprint import pprint
    pprint(it)

if __name__ == "__main__":
    main()
