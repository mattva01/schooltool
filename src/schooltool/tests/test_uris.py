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
from zope.component import queryUtility
from zope.interface.verify import verifyObject
from schooltool.tests.utils import RegistriesSetupMixin

__metaclass__ = type


class TestURIObjects(RegistriesSetupMixin, unittest.TestCase):

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

    def testURIRegistry(self):
        from schooltool.interfaces import IURIObject
        from schooltool.uris import URIObject
        from zope.component.exceptions import ComponentLookupError
        from schooltool.uris import registerURI
        from zope.component import getUtility

        URI1 = URIObject("http://example.com/foobar")
        URI2 = URIObject("http://example.com/foo")
        URI2Dupe = URIObject("http://example.com/foo")

        self.assert_(queryUtility(IURIObject, "http://example.com/foobar")
                     is None)
        self.assert_(queryUtility(IURIObject, "http://example.com/foo")
                     is None)

        registerURI(URI1)
        self.assert_(getUtility(IURIObject, "http://example.com/foobar")
                     is URI1)

        registerURI(URI2)
        registerURI(URI2)
        self.assert_(getUtility(IURIObject, "http://example.com/foo") is URI2)
        registerURI(URI2Dupe)
        self.assert_(getUtility(IURIObject, "http://example.com/foo")
                     is URI2Dupe)

    def testURISetup(self):
        import schooltool.uris
        from zope.component import getUtility
        from schooltool.interfaces import IModuleSetup, IURIObject
        verifyObject(IModuleSetup, schooltool.uris)
        schooltool.uris.setUp()
        getUtility(IURIObject, "http://schooltool.org/ns/membership")
        getUtility(IURIObject, "http://schooltool.org/ns/membership/member")
        getUtility(IURIObject, "http://schooltool.org/ns/membership/group")
        getUtility(IURIObject, "http://schooltool.org/ns/teaching")
        getUtility(IURIObject, "http://schooltool.org/ns/teaching/teacher")
        getUtility(IURIObject, "http://schooltool.org/ns/teaching/taught")
        getUtility(IURIObject, "http://schooltool.org/ns/occupies")
        getUtility(IURIObject,
                   "http://schooltool.org/ns/occupies/currentlyresides")
        getUtility(IURIObject,
                   "http://schooltool.org/ns/occupies/currentresidence")
        getUtility(IURIObject, "http://schooltool.org/ns/guardian")
        getUtility(IURIObject, "http://schooltool.org/ns/guardian/custodian")
        getUtility(IURIObject, "http://schooltool.org/ns/guardian/ward")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestURIObjects))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
