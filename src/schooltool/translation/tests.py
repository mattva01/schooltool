#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Unit tests for the schooltool.translation module.

$Id$
"""

import unittest
from zope.testing.doctest import DocTestSuite


class TestTranslatableString(unittest.TestCase):

    def test(self):
        from schooltool.translation import TranslatableString
        TS = TranslatableString

        self.assertEquals(repr(TS("foo")), "_('foo')")
        self.assertEquals(int(TS("42")), 42)
        self.assertEquals(long(TS("42")), 42L)
        self.assertEquals(float(TS("4.2")), 4.2)
        # __complex__: YAGNI
        self.assertEquals(hash(TS("xyzzy")), hash("xyzzy"))

        self.assertEquals(len(TS("abc")), 3)
        self.assertEquals(TS("abc")[1], 'b')
        self.assertEquals(TS("abc")[0:2], 'ab')
        self.assertEquals(TS("a") + TS("B"), "aB")
        s = TS("x")
        s += TS("y")
        self.assertEquals(s, "xy")
        self.assertEquals(TS("a") * 3, "aaa")
        s *= 3
        self.assertEquals(s, "xyxyxy")
        self.assertEquals(TS("%s: %s") % ("a", "b"), "a: b")

    def test_translation_performed(self):
        from schooltool.translation import TranslatableString

        class TS(TranslatableString):
            def __unicode__(self):
                return self.msgid.replace('*', '')

        self.assertEquals(unicode(TS("*foo")), "foo")
        self.assertEquals(repr(TS("*foo")), "_('*foo')")
        self.assertEquals(int(TS("4*2")), 42)
        self.assertEquals(long(TS("42*")), 42L)
        self.assertEquals(float(TS("4.*2")), 4.2)
        # __complex__: YAGNI
        self.assertEquals(hash(TS("xyzz*y")), hash("xyzzy"))

        self.assertEquals(len(TS("a*bc")), 3)
        self.assertEquals(TS("a*bc")[1], 'b')
        self.assertEquals(TS("a*bc")[0:2], 'ab')
        self.assertEquals(TS("a*") + TS("*B"), "aB")
        s = TS("*x")
        s += TS("y*")
        self.assertEquals(s, "xy")
        self.assertEquals(TS("a*") * 3, "aaa")
        s *= 3
        self.assertEquals(s, "xyxyxy")
        self.assertEquals(TS("%s*: %s") % ("a", "b"), "a: b")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.translation.extract'))
    suite.addTest(unittest.makeSuite(TestTranslatableString))
    return suite
