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


class TestURIObjects(RegistriesSetupMixin, unittest.TestCase):

    def test_api(self):
        import schooltool.uris
        from schooltool.interfaces import IURIAPI
        verifyObject(IURIAPI, schooltool.uris)

    def test_URIObject(self):
        from schooltool.uris import URIObject
        from schooltool.interfaces import IURIObject
        uri = URIObject('http://example.com', 'Example', 'An example')
        verifyObject(IURIObject, uri)
        self.assertEquals(uri.uri, 'http://example.com')
        self.assertEquals(uri.name, 'Example')
        self.assertEquals(uri.description, 'An example')

        uri = URIObject('http://example.com', 'Example')
        self.assertEquals(uri.description, '')

        uri = URIObject('http://example.com')
        self.assertEquals(uri.name, None)

        self.assertRaises(ValueError, URIObject, 'not a uri', 'Bad Example')

    def test_equality(self):
        from schooltool.uris import URIObject
        uri1 = URIObject('http://example.com')
        uri2 = URIObject('http://example.com')
        uri3 = URIObject('http://example.org')
        assert uri1 == uri2
        assert uri1 != uri3
        assert not (uri1 != uri2)
        assert not (uri1 == uri3)
        assert hash(uri1) == hash(uri2)
        assert hash(uri1) != hash(uri3)

    def test_verifyURI(self):
        from schooltool.uris import URIObject, verifyURI
        uri = URIObject('http://example.com')
        verifyURI(uri)

        self.assertRaises(TypeError, verifyURI, 'http://example.com')
        self.assertRaises(TypeError, verifyURI, 'Just a name')

    def test_isURI(self):
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
               None,
               ]
        for string in good:
            self.assert_(isURI(string), string)
        for string in bad:
            self.assert_(not isURI(string), string)

    def testURIRegistry(self):
        from schooltool.interfaces import ComponentLookupError
        from schooltool.uris import URIObject, getURI, registerURI, listURIs
        URI1 = URIObject("http://example.com/foobar")
        URI2 = URIObject("http://example.com/foo")
        URI2Dupe = URIObject("http://example.com/foo")

        self.assert_(URI1 not in listURIs())
        self.assert_(URI2 not in listURIs())
        self.assertRaises(ComponentLookupError, getURI,
                          "http://example.com/foobar")
        registerURI(URI1)
        self.assert_(getURI("http://example.com/foobar") is URI1)
        self.assert_(URI1 in listURIs())

        registerURI(URI2)
        registerURI(URI2)
        self.assert_(URI2 in listURIs())
        self.assert_(getURI("http://example.com/foo") is URI2)
        self.assertRaises(ValueError, registerURI, URI2Dupe)
        self.assert_(getURI("http://example.com/foo") is URI2)

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
    suite.addTest(unittest.makeSuite(TestURIObjects))
    return suite

if __name__ == '__main__':
    unittest.main()
