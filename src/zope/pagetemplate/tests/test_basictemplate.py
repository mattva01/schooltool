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
"""Basic Page Template tests

$Id$
"""
import unittest

from zope.pagetemplate.tests import util
from zope.pagetemplate.pagetemplate import PageTemplate

class BasicTemplateTests(unittest.TestCase):

    def setUp(self):
        self.t = PageTemplate()

    def test_if_in_var(self):
        # DTML test 1: if, in, and var:
        pass # for unittest
        """
        %(comment)[ blah %(comment)]
        <html><head><title>Test of documentation templates</title></head>
        <body>
        %(if args)[
        <dl><dt>The arguments to this test program were:<p>
        <dd>
        <ul>
        %(in args)[
          <li>Argument number %(num)d was %(arg)s
        %(in args)]
        </ul></dl><p>
        %(if args)]
        %(else args)[
        No arguments were given.<p>
        %(else args)]
        And thats da trooth.
        </body></html>
        """
        tal = util.read_input('dtml1.html')
        self.t.write(tal)

        aa = util.argv(('one', 'two', 'three', 'cha', 'cha', 'cha'))
        o = self.t(content=aa)
        expect = util.read_output('dtml1a.html')

        util.check_xml(expect, o)

        aa = util.argv(())
        o = self.t(content=aa)
        expect = util.read_output('dtml1b.html')
        util.check_xml(expect, o)

    def test_template_usage(self):
        tal = util.read_input('template_usage.html')
        self.t.write(tal)

        o = self.t(template_usage=u"test")
        expect = util.read_output('template_usage1.html')
        util.check_xml(expect, o)

        o = self.t(template_usage=u"retest")
        expect = util.read_output('template_usage2.html')
        util.check_xml(expect, o)

        o = self.t(template_usage=u"other")
        expect = util.read_output('template_usage3.html')
        util.check_xml(expect, o)

        o = self.t(template_usage=u"")
        expect = util.read_output('template_usage4.html')
        util.check_xml(expect, o)

    def test_batches_and_formatting(self):
        # DTML test 3: batches and formatting:
        pass # for unittest
        """
          <html><head><title>Test of documentation templates</title></head>
          <body>
          <!--#if args-->
            The arguments were:
            <!--#in args size=size end=end-->
                <!--#if previous-sequence-->
                   (<!--#var previous-sequence-start-arg-->-
                    <!--#var previous-sequence-end-arg-->)
                <!--#/if previous-sequence-->
                <!--#if sequence-start-->
                   <dl>
                <!--#/if sequence-start-->
                <dt><!--#var sequence-arg-->.</dt>
                <dd>Argument <!--#var num fmt=d--> was <!--#var arg--></dd>
                <!--#if next-sequence-->
                   (<!--#var next-sequence-start-arg-->-
                    <!--#var next-sequence-end-arg-->)
                <!--#/if next-sequence-->
            <!--#/in args-->
            </dl>
          <!--#else args-->
            No arguments were given.<p>
          <!--#/if args-->
          And I\'m 100% sure!
          </body></html>
        """
        tal = util.read_input('dtml3.html')
        self.t.write(tal)

        aa = util.argv(('one', 'two', 'three', 'four', 'five',
                        'six', 'seven', 'eight', 'nine', 'ten',
                        'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
                        'sixteen', 'seventeen', 'eighteen', 'nineteen',
                        'twenty',
                        ))
        from zope.pagetemplate.tests import batch
        o = self.t(content=aa, batch=batch.batch(aa.args, 5))

        expect = util.read_output('dtml3.html')
        util.check_xml(expect, o)


def test_suite():
    return unittest.makeSuite(BasicTemplateTests)

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
