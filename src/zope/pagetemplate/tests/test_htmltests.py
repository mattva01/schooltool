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
"""Page Template HTML Tests

$Id$
"""
import unittest

from zope.pagetemplate.tests import util
from zope.pagetemplate.pagetemplate import PageTemplate


class Folder(object):
    context = property(lambda self: self)

class HTMLTests(unittest.TestCase):

    def setUp(self):
        self.folder = f = Folder()
        f.laf = PageTemplate()
        f.t = PageTemplate()

    def getProducts(self):
        return [
           {'description': 'This is the tee for those who LOVE Zope. '
            'Show your heart on your tee.',
            'price': 12.99, 'image': 'smlatee.jpg'
            },
           {'description': 'This is the tee for Jim Fulton. '
            'He\'s the Zope Pope!',
            'price': 11.99, 'image': 'smpztee.jpg'
            },
           ]

    def test_1(self):
        laf = self.folder.laf
        laf.write(util.read_input('teeshoplaf.html'))
        expect = util.read_output('teeshoplaf.html')
        util.check_html(expect, laf())

    def test_2(self):
        self.folder.laf.write(util.read_input('teeshoplaf.html'))

        t = self.folder.t
        t.write(util.read_input('teeshop2.html'))
        expect = util.read_output('teeshop2.html')
        out = t(laf = self.folder.laf, getProducts = self.getProducts)
        util.check_html(expect, out)


    def test_3(self):
        self.folder.laf.write(util.read_input('teeshoplaf.html'))

        t = self.folder.t
        t.write(util.read_input('teeshop1.html'))
        expect = util.read_output('teeshop1.html')
        out = t(laf = self.folder.laf, getProducts = self.getProducts)
        util.check_html(expect, out)

    def test_SimpleLoop(self):
        t = self.folder.t
        t.write(util.read_input('loop1.html'))
        expect = util.read_output('loop1.html')
        out = t()
        util.check_html(expect, out)

    def test_GlobalsShadowLocals(self):
        t = self.folder.t
        t.write(util.read_input('globalsshadowlocals.html'))
        expect = util.read_output('globalsshadowlocals.html')
        out = t()
        util.check_html(expect, out)

    def test_StringExpressions(self):
        t = self.folder.t
        t.write(util.read_input('stringexpression.html'))
        expect = util.read_output('stringexpression.html')
        out = t()
        util.check_html(expect, out)

    def test_ReplaceWithNothing(self):
        t = self.folder.t
        t.write(util.read_input('checknothing.html'))
        expect = util.read_output('checknothing.html')
        out = t()
        util.check_html(expect, out)

    def test_WithXMLHeader(self):
        t = self.folder.t
        t.write(util.read_input('checkwithxmlheader.html'))
        expect = util.read_output('checkwithxmlheader.html')
        out = t()
        util.check_html(expect, out)

    def test_NotExpression(self):
        t = self.folder.t
        t.write(util.read_input('checknotexpression.html'))
        expect = util.read_output('checknotexpression.html')
        out = t()
        util.check_html(expect, out)

    def test_PathNothing(self):
        t = self.folder.t
        t.write(util.read_input('checkpathnothing.html'))
        expect = util.read_output('checkpathnothing.html')
        out = t()
        util.check_html(expect, out)

    def test_PathAlt(self):
        t = self.folder.t
        t.write(util.read_input('checkpathalt.html'))
        expect = util.read_output('checkpathalt.html')
        out = t()
        util.check_html(expect, out)


def test_suite():
    return unittest.makeSuite(HTMLTests)

if __name__=='__main__':
    unittest.TextTestRunner().run(test_suite())
