# -*- coding: ISO-8859-1 -*-
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
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
"""Tests for TALInterpreter.

$Id: test_talinterpreter.py,v 1.11 2004/03/23 19:18:15 srichter Exp $
"""
import sys
import unittest

from StringIO import StringIO

from zope.tal.taldefs import METALError, I18NError
from zope.tal.htmltalparser import HTMLTALParser
from zope.tal.talinterpreter import TALInterpreter
from zope.tal.dummyengine import DummyEngine, DummyTranslationDomain
from zope.tal.tests import utils
from zope.i18n.messageid import MessageID

class TestCaseBase(unittest.TestCase):

    def _compile(self, source):
        parser = HTMLTALParser()
        parser.parseString(source)
        program, macros = parser.getCode()
        return program, macros


class MacroErrorsTestCase(TestCaseBase):

    def setUp(self):
        dummy, macros = self._compile('<p metal:define-macro="M">Booh</p>')
        self.macro = macros['M']
        self.engine = DummyEngine(macros)
        program, dummy = self._compile('<p metal:use-macro="M">Bah</p>')
        self.interpreter = TALInterpreter(program, {}, self.engine)

    def tearDown(self):
        try:
            self.interpreter()
        except METALError:
            pass
        else:
            self.fail("Expected METALError")

    def test_mode_error(self):
        self.macro[1] = ("mode", "duh")

    def test_version_error(self):
        self.macro[0] = ("version", "duh")


class MacroFunkyErrorTest(TestCaseBase):
    
    def test_div_in_p_using_macro(self):
        dummy, macros = self._compile('<p metal:define-macro="M">Booh</p>')
        engine = DummyEngine(macros)
        program, dummy = self._compile(
            '<p metal:use-macro="M"><div>foo</div></p>')
        interpreter = TALInterpreter(program, {}, engine)

        output = interpreter()
        self.assertEqual(output, '<p><div>foo</div></p>')


class I18NCornerTestCase(TestCaseBase):

    def setUp(self):
        self.engine = DummyEngine()
        self.engine.setLocal('foo', MessageID('FoOvAlUe', 'default'))
        self.engine.setLocal('bar', 'BaRvAlUe')

    def _check(self, program, expected):
        result = StringIO()
        self.interpreter = TALInterpreter(program, {}, self.engine,
                                          stream=result)
        self.interpreter()
        self.assertEqual(expected, result.getvalue())

    def test_simple_messageid_translate(self):
        # This test is mainly here to make sure our DummyEngine works
        # correctly.
        program, macros = self._compile('<span tal:content="foo"/>')
        self._check(program, '<span>FOOVALUE</span>\n')

        program, macros = self._compile('<span tal:replace="foo"/>')
        self._check(program, 'FOOVALUE\n')

    def test_replace_with_messageid_and_i18nname(self):
        program, macros = self._compile(
            '<div i18n:translate="" >'
            '<span tal:replace="foo" i18n:name="foo_name"/>'
            '</div>')
        self._check(program, '<div>FOOVALUE</div>\n')

    def test_pythonexpr_replace_with_messageid_and_i18nname(self):
        program, macros = self._compile(
            '<div i18n:translate="" >'
            '<span tal:replace="python: foo" i18n:name="foo_name"/>'
            '</div>')
        self._check(program, '<div>FOOVALUE</div>\n')

    def test_structure_replace_with_messageid_and_i18nname(self):
        program, macros = self._compile(
            '<div i18n:translate="" >'
            '<span tal:replace="structure foo" i18n:name="foo_name"/>'
            '</div>')
        self._check(program, '<div>FOOVALUE</div>\n')

    def test_complex_replace_with_messageid_and_i18nname(self):
        program, macros = self._compile(
            '<div i18n:translate="" >'
            '<em i18n:name="foo_name">'
            '<span tal:replace="foo"/>'
            '</em>'
            '</div>')
        self._check(program, '<div>FOOVALUE</div>\n')

    def test_content_with_messageid_and_i18nname(self):
        program, macros = self._compile(
            '<div i18n:translate="" >'
            '<span tal:content="foo" i18n:name="foo_name"/>'
            '</div>')
        self._check(program, '<div><span>FOOVALUE</span></div>\n')

    def test_content_with_messageid_and_i18nname_and_i18ntranslate(self):
        # Let's tell the user this is incredibly silly!
        self.assertRaises(
            I18NError, self._compile,
            '<span i18n:translate="" tal:content="foo" i18n:name="foo_name"/>')

    def test_content_with_plaintext_and_i18nname_and_i18ntranslate(self):
        # Let's tell the user this is incredibly silly!
        self.assertRaises(
            I18NError, self._compile,
            '<span i18n:translate="" i18n:name="color_name">green</span>')

    def test_translate_static_text_as_dynamic(self):
        program, macros = self._compile(
            '<div i18n:translate="">This is text for '
            '<span i18n:translate="" tal:content="bar" i18n:name="bar_name"/>.'
            '</div>')
        self._check(program,
                    '<div>THIS IS TEXT FOR <span>BARVALUE</span>.</div>\n')

    def test_translate_static_text_as_dynamic_from_bytecode(self):
        program =  [('version', '1.4'),
 ('mode', 'html'),
('setPosition', (1, 0)),
('beginScope', {'i18n:translate': ''}),
('startTag', ('div', [('i18n:translate', '', 'i18n')])),
('insertTranslation',
 ('',
  [('rawtextOffset', ('This is text for ', 17)),
   ('setPosition', (1, 40)),
   ('beginScope',
    {'tal:content': 'bar', 'i18n:name': 'bar_name', 'i18n:translate': ''}),
   ('i18nVariable',
       ('bar_name',
        [('startTag',
           ('span',
            [('i18n:translate', '', 'i18n'),
             ('tal:content', 'bar', 'tal'),
             ('i18n:name', 'bar_name', 'i18n')])),
         ('insertTranslation',
           ('',
             [('insertText', ('$bar$', []))])),
         ('rawtextOffset', ('</span>', 7))],
      None)),
   ('endScope', ()),
   ('rawtextOffset', ('.', 1))])),
('endScope', ()),
('rawtextOffset', ('</div>', 6)) 
]
        self._check(program,
                    '<div>THIS IS TEXT FOR <span>BARVALUE</span>.</div>\n')

    def test_for_correct_msgids(self):

        class CollectingTranslationDomain(DummyTranslationDomain):
            data = []

            def translate(self, msgid, mapping=None,
                          context=None, target_language=None, default=None):
                self.data.append(msgid)
                return DummyTranslationDomain.translate(
                    self,
                    msgid, mapping, context, target_language, default)

        xlatdmn = CollectingTranslationDomain()
        self.engine.translationDomain = xlatdmn
        result = StringIO()
        program, macros = self._compile(
            '<div i18n:translate="">This is text for '
            '<span i18n:translate="" tal:content="bar" '
            'i18n:name="bar_name"/>.</div>')
        self.interpreter = TALInterpreter(program, {}, self.engine,
                                          stream=result)
        self.interpreter()
        self.assert_('BaRvAlUe' in xlatdmn.data)
        self.assert_('This is text for ${bar_name}.' in
                     xlatdmn.data)
        self.assertEqual(
            '<div>THIS IS TEXT FOR <span>BARVALUE</span>.</div>\n',
            result.getvalue())


class ScriptTestCase(TestCaseBase):

    def setUp(self):
        self.engine = DummyEngine()

    def _check(self, program, expected):
        result = StringIO()
        self.interpreter = TALInterpreter(program, {}, self.engine,
                                          stream=result)
        self.interpreter()
        self.assertEqual(expected, result.getvalue())

    def test_simple(self):
        program, macros = self._compile(
            '<p tal:script="text/server-python">print "hello"</p>')
        self._check(program, '<p>hello\n</p>\n')

    def test_script_and_tal_block(self):
        program, macros = self._compile(
            '<tal:block script="text/server-python">\n'
            '  global x\n'
            '  x = 1\n'
            '</tal:block>\n'
            '<span tal:replace="x" />')
        self._check(program, '\n1\n')
        self.assertEqual(self.engine.codeGlobals['x'], 1)

    def test_script_and_tal_block_having_inside_print(self):
        program, macros = self._compile(
            '<tal:block script="text/server-python">\n'
            '  print "hello"'
            '</tal:block>')
        self._check(program, 'hello\n\n')

    def test_script_and_omittag(self):
        program, macros = self._compile(
            '<p tal:omit-tag="" tal:script="text/server-python">\n'
            '  print "hello"'
            '</p>')
        self._check(program, 'hello\n\n')

    def test_script_and_inside_tags(self):
        program, macros = self._compile(
            '<p tal:omit-tag="" tal:script="text/server-python">\n'
            '  print "<b>hello</b>"'
            '</p>')
        self._check(program, '<b>hello</b>\n\n')

    def test_script_and_inside_tags_with_tal(self):
        program, macros = self._compile(
            '<p tal:omit-tag="" tal:script="text/server-python"> <!--\n'
            '  print """<b tal:replace="string:foo">hello</b>"""\n'
            '--></p>')
        self._check(program, '<b tal:replace="string:foo">hello</b>\n\n')

    def test_html_script(self):
        program, macros = self._compile(
            '<script type="text/server-python">\n'
            '  print "Hello world!"\n'
            '</script>')
        self._check(program, 'Hello world!\n')

    def test_html_script_and_javascript(self):
        program, macros = self._compile(
            '<script type="text/javascript" src="somefile.js" />\n'
            '<script type="text/server-python">\n'
            '  print "Hello world!"\n'
            '</script>')
        self._check(program,
                    '<script type="text/javascript" src="somefile.js" />\n'
                    'Hello world!\n')


class I18NErrorsTestCase(TestCaseBase):

    def _check(self, src, msg):
        try:
            self._compile(src)
        except I18NError:
            pass
        else:
            self.fail(msg)

    def test_id_with_replace(self):
        self._check('<p i18n:id="foo" tal:replace="string:splat"></p>',
                    "expected i18n:id with tal:replace to be denied")

    def test_missing_values(self):
        self._check('<p i18n:attributes=""></p>',
                    "missing i18n:attributes value not caught")
        self._check('<p i18n:data=""></p>',
                    "missing i18n:data value not caught")
        self._check('<p i18n:id=""></p>',
                    "missing i18n:id value not caught")

    def test_id_with_attributes(self):
        self._check('''<input name="Delete"
                       tal:attributes="name string:delete_button"
                       i18n:attributes="name message-id">''',
            "expected attribute being both part of tal:attributes" +
            " and having a msgid in i18n:attributes to be denied")

class OutputPresentationTestCase(TestCaseBase):

    def test_attribute_wrapping(self):
        # To make sure the attribute-wrapping code is invoked, we have to
        # include at least one TAL/METAL attribute to avoid having the start
        # tag optimized into a rawtext instruction.
        INPUT = r"""
        <html this='element' has='a' lot='of' attributes=', so' the='output'
              needs='to' be='line' wrapped='.' tal:define='foo nothing'>
        </html>"""
        EXPECTED = r'''
        <html this="element" has="a" lot="of"
              attributes=", so" the="output" needs="to"
              be="line" wrapped=".">
        </html>''' "\n"
        self.compare(INPUT, EXPECTED)

    def test_unicode_content(self):
        INPUT = """<p tal:content="python:u'déjà-vu'">para</p>"""
        EXPECTED = u"""<p>déjà-vu</p>""" "\n"
        self.compare(INPUT, EXPECTED)

    def test_unicode_structure(self):
        INPUT = """<p tal:replace="structure python:u'déjà-vu'">para</p>"""
        EXPECTED = u"""déjà-vu""" "\n"
        self.compare(INPUT, EXPECTED)

    def test_i18n_replace_number(self):
        INPUT = """
        <p i18n:translate="foo ${bar}">
        <span tal:replace="python:123" i18n:name="bar">para</span>
        </p>"""
        EXPECTED = u"""
        <p>FOO 123</p>""" "\n"
        self.compare(INPUT, EXPECTED)

    def test_entities(self):
        INPUT = ('<img tal:define="foo nothing" '
                 'alt="&a; &#1; &#x0a; &a &#45 &; &#0a; <>" />')
        EXPECTED = ('<img alt="&a; &#1; &#x0a; '
                    '&amp;a &amp;#45 &amp;; &amp;#0a; &lt;&gt;" />\n')
        self.compare(INPUT, EXPECTED)

    def compare(self, INPUT, EXPECTED):
        program, macros = self._compile(INPUT)
        sio = StringIO()
        interp = TALInterpreter(program, {}, DummyEngine(), sio, wrap=60)
        interp()
        self.assertEqual(sio.getvalue(), EXPECTED)


def test_suite():
    suite = unittest.makeSuite(I18NErrorsTestCase)
    suite.addTest(unittest.makeSuite(MacroErrorsTestCase))
    suite.addTest(unittest.makeSuite(OutputPresentationTestCase))
    suite.addTest(unittest.makeSuite(ScriptTestCase))
    suite.addTest(unittest.makeSuite(I18NCornerTestCase))

    # XXX: Deactivated test, since we have not found a solution for this and
    # it is a deep and undocumented HTML parser issue.
    # Fred is looking into this.
    #suite.addTest(unittest.makeSuite(MacroFunkyErrorTest))

    return suite

if __name__ == "__main__":
    errs = utils.run_suite(test_suite())
    sys.exit(errs and 1 or 0)
