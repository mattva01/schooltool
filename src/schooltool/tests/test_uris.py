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
Unit tests for schooltool.uris

$Id$
"""

import unittest
from zope.interface.verify import verifyObject
from schooltool.tests.utils import RegistriesSetupMixin

__metaclass__ = type


class TestSpecificURI(RegistriesSetupMixin, unittest.TestCase):

    def test_api(self):
        import schooltool.uris
        from schooltool.uris import IURIAPI
        verifyObject(IURIAPI, schooltool.uris)

    def test_inspectSpecificURI(self):
        from zope.interface import Interface
        from schooltool.uris import ISpecificURI
        from schooltool.uris import inspectSpecificURI, strURI, nameURI

        class I1(Interface):
            pass

        self.assertRaises(TypeError, inspectSpecificURI, object())
        self.assertRaises(TypeError, inspectSpecificURI, I1)
        self.assertRaises(TypeError, inspectSpecificURI, ISpecificURI)

        class IURI(ISpecificURI):
            """http://example.com/foo

            Title

            Doc text
            with newlines in it
            """

        uri, title, doc = inspectSpecificURI(IURI)
        self.assertEqual(uri, "http://example.com/foo")
        self.assertEqual(uri, strURI(IURI))
        self.assertEqual(title, "Title")
        self.assertEqual(title, nameURI(IURI))
        self.assertEqual(doc, "Doc text\nwith newlines in it")

        class IURI2(ISpecificURI): """http://example.com/foo"""
        uri, title, doc = inspectSpecificURI(IURI2)
        self.assertEqual(uri, "http://example.com/foo")
        self.assertEqual(uri, strURI(IURI2))
        self.assertEqual(title, None)
        self.assertEqual(title, nameURI(IURI2))
        self.assertEqual(doc, "")

        class IURI3(ISpecificURI): """foo"""
        self.assertRaises(ValueError, inspectSpecificURI, IURI3)

        class IURI4(ISpecificURI):
            """\
            mailto:foo
            """
        uri, title, doc = inspectSpecificURI(IURI4)
        self.assertEqual(uri, "mailto:foo")
        self.assertEqual(uri, strURI(IURI4))
        self.assertEqual(title, None)
        self.assertEqual(title, nameURI(IURI2))
        self.assertEqual(doc, "")

        class IURI5(ISpecificURI):
            """

            mailto:foo
            """
        self.assertRaises(ValueError, inspectSpecificURI, IURI5)

    def test__isURI(self):
        from schooltool.uris import isURI
        good = ["http://foo/bar?baz#quux",
                "HTTP://foo/bar?baz#quux",
                "mailto:root",
                ]
        bad = ["2HTTP://foo/bar?baz#quux",
               "\nHTTP://foo/bar?baz#quux",
               "mailto:postmaster ",
               "mailto:postmaster text"
               "nocolon",
               ]
        for string in good:
            self.assert_(isURI(string), string)
        for string in bad:
            self.assert_(not isURI(string), string)

    def testURIRegistry(self):
        from schooltool.interfaces import ComponentLookupError
        from schooltool.uris import ISpecificURI, getURI, registerURI
        class IURI1(ISpecificURI): """http://example.com/foobar"""
        class IURI2(ISpecificURI): """http://example.com/foo"""
        class IURI2Dupe(ISpecificURI): """http://example.com/foo"""

        self.assertRaises(ComponentLookupError, getURI,
                          """http://example.com/foobar""")
        registerURI(IURI1)
        self.assert_(getURI("http://example.com/foobar") is IURI1)

        registerURI(IURI2)
        registerURI(IURI2)
        self.assert_(getURI("http://example.com/foo") is IURI2)
        self.assertRaises(ValueError, registerURI, IURI2Dupe)
        self.assert_(getURI("http://example.com/foo") is IURI2)

    def testURISetup(self):
        import schooltool.uris
        from schooltool.uris import getURI
        from schooltool.interfaces import IModuleSetup
        verifyObject(IModuleSetup, schooltool.uris)
        schooltool.uris.setUp()
        getURI("http://schooltool.org/ns/membership")
        getURI("http://schooltool.org/ns/membership/member")
        getURI("http://schooltool.org/ns/membership/group")
        getURI("http://schooltool.org/ns/teaching")
        getURI("http://schooltool.org/ns/teaching/teacher")
        getURI("http://schooltool.org/ns/teaching/taught")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSpecificURI))
    return suite

if __name__ == '__main__':
    unittest.main()
