#! /usr/bin/env python
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
"""Tests for TALInterpreter.

$Id$
"""
import unittest

from StringIO import StringIO

from zope.tal.htmltalparser import HTMLTALParser
from zope.tal.talinterpreter import TALInterpreter
from zope.tal.talgenerator import TALGenerator
from zope.tal.dummyengine import DummyEngine


page1 = '''<html metal:use-macro="main"><body>
<div metal:fill-slot="body">
page1=<span tal:replace="position:" />
</div>
</body></html>'''

main_template = '''<html metal:define-macro="main"><body>
main_template=<span tal:replace="position:" />
<div metal:define-slot="body" />
main_template=<span tal:replace="position:" />
<div metal:use-macro="foot" />
main_template=<span tal:replace="position:" />
</body></html>'''

footer = '''<div metal:define-macro="foot">
footer=<span tal:replace="position:" />
</div>'''

expected = '''<html><body>
main_template=main_template (2,14)
<div>
page1=page1 (3,6)
</div>
main_template=main_template (4,14)
<div>
footer=footer (2,7)
</div>
main_template=main_template (6,14)
</body></html>'''



class SourcePosTestCase(unittest.TestCase):

    def parse(self, eng, s, fn):
        gen = TALGenerator(expressionCompiler=eng, xml=0, source_file=fn)
        parser = HTMLTALParser(gen)
        parser.parseString(s)
        program, macros = parser.getCode()
        return program, macros

    def test_source_positions(self):
        # Ensure source file and position are set correctly by TAL
        macros = {}
        eng = DummyEngine(macros)
        page1_program, page1_macros = self.parse(eng, page1, 'page1')
        main_template_program, main_template_macros = self.parse(
            eng, main_template, 'main_template')
        footer_program, footer_macros = self.parse(eng, footer, 'footer')

        macros['main'] = main_template_macros['main']
        macros['foot'] = footer_macros['foot']

        stream = StringIO()
        interp = TALInterpreter(page1_program, macros, eng, stream)
        interp()
        self.assertEqual(stream.getvalue().strip(), expected.strip(),
                         "Got result:\n%s\nExpected:\n%s"
                         % (stream.getvalue(), expected))


def test_suite():
    return unittest.makeSuite(SourcePosTestCase)

if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
