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
Unit tests for schooltool.component

$Id$
"""

import unittest
from sets import Set
from zope.interface import Interface, implements, directlyProvides
from zope.interface.verify import verifyObject
from schooltool.interfaces import ISpecificURI, IRelatable, IQueryLinks

__metaclass__ = type

class I1(Interface):
    def foo():
        pass

class I2(Interface):
    pass

class C1:
    implements(I1)
    def __init__(self, context):
        self.context = context

    def foo(self):
        return "foo"

class TestGetAdapter(unittest.TestCase):

    def setUp(self):
        from schooltool.component import adapterRegistry
        self.reg = adapterRegistry.copy()

    def tearDown(self):
        from schooltool.component import adapterRegistry
        self.adapterRegistry = self.reg

    def test_getAdapter(self):
        from schooltool.component import getAdapter, provideAdapter
        from schooltool.interfaces import ComponentLookupError
        provideAdapter(I1, C1)
        self.assertEqual(getAdapter(object(), I1).foo(), "foo")
        self.assertRaises(ComponentLookupError, getAdapter, object(), I2)

    def test_getAdapter_provided(self):
        from schooltool.component import getAdapter, provideAdapter
        ob = C1(None)
        self.assertEqual(getAdapter(ob, I1), ob)


class TestCanonicalPath(unittest.TestCase):

    def test_api(self):
        from schooltool import component
        from schooltool.interfaces import IContainmentAPI
        verifyObject(IContainmentAPI, component)

    def test_path(self):
        from schooltool.component import getPath
        from schooltool.interfaces import ILocation, IContainmentRoot

        class Stub:
            implements(ILocation)

            def __init__(self, parent, name):
                self.__parent__ = parent
                self.__name__ = name

        a = Stub(None, 'root')
        self.assertRaises(TypeError, getPath, a)
        directlyProvides(a, IContainmentRoot)
        self.assertEqual(getPath(a), '/')
        b = Stub(a, 'foo')
        self.assertEqual(getPath(b), '/foo')
        c = Stub(b, 'bar')
        self.assertEqual(getPath(c), '/foo/bar')


class TestFacetFunctions(unittest.TestCase):

    def setUp(self):
        from schooltool.interfaces import IFaceted
        class Stub:
            implements(IFaceted)
            __facets__ = {}

        self.ob = Stub()
        self.marker = object()
        self.facet = object()

    def test_api(self):
        from schooltool import component
        from schooltool.interfaces import IFacetAPI
        verifyObject(IFacetAPI, component)

    def test_setFacet(self):
        from schooltool.component import setFacet
        setFacet(self.ob, self.marker, self.facet)
        self.assert_(self.ob.__facets__[self.marker] is self.facet)
        self.assertRaises(TypeError,
                          setFacet, object(), self.marker, self.facet)

    def test_getFacet(self):
        from schooltool.component import getFacet
        self.ob.__facets__[self.marker] = self.facet
        result = getFacet(self.ob, self.marker)
        self.assertEqual(result, self.facet)
        self.assertRaises(KeyError, getFacet, self.ob, object())
        self.assertRaises(TypeError, getFacet, object(), self.marker)

    def test_queryFacet(self):
        from schooltool.component import queryFacet
        self.ob.__facets__[self.marker] = self.facet
        result = queryFacet(self.ob, self.marker)
        self.assertEqual(result, self.facet)
        result = queryFacet(self.ob, object())
        self.assertEqual(result, None)
        cookie = object()
        result = queryFacet(self.ob, object(), cookie)
        self.assertEqual(result, cookie)
        self.assertRaises(TypeError, queryFacet, object(), self.marker)

    def test_getFacetItems(self):
        from schooltool.component import getFacetItems
        self.ob.__facets__[self.marker] = self.facet
        result = getFacetItems(self.ob)
        self.assertEqual(result, [(self.marker, self.facet)])
        self.assertRaises(TypeError, getFacetItems, object())


class TestServiceAPI(unittest.TestCase):

    def test_api(self):
        from schooltool import component
        from schooltool.interfaces import IServiceAPI
        verifyObject(IServiceAPI, component)

    def test_getEventService(self):
        from schooltool.component import getEventService
        from schooltool.interfaces import IServiceManager, ILocation
        from schooltool.interfaces import ComponentLookupError

        class RootStub:
            implements(IServiceManager)
            eventService = object()

        class ObjectStub:
            implements(ILocation)

            def __init__(self, parent, name='foo'):
                self.__parent__ = parent
                self.__name__ = name

        root = RootStub()
        a = ObjectStub(root)
        b = ObjectStub(a)
        cloud = ObjectStub(None)

        self.assertEquals(getEventService(root), root.eventService)
        self.assertEquals(getEventService(a), root.eventService)
        self.assertEquals(getEventService(b), root.eventService)
        self.assertRaises(ComponentLookupError, getEventService, cloud)
        self.assertRaises(ComponentLookupError, getEventService, None)


class TestSpecificURI(unittest.TestCase):

    def test_api(self):
        from schooltool import component
        from schooltool.interfaces import IURIAPI
        verifyObject(IURIAPI, component)

    def test_inspectSpecificURI(self):
        from schooltool.component import inspectSpecificURI
        from schooltool.interfaces import ISpecificURI
        self.assertRaises(TypeError, inspectSpecificURI, object())
        self.assertRaises(TypeError, inspectSpecificURI, I1)
        self.assertRaises(TypeError, inspectSpecificURI, ISpecificURI)
        class IURI(ISpecificURI):
            """http://example.com/foo

            Doc text
            """
        uri, doc = inspectSpecificURI(IURI)
        self.assertEqual(uri, "http://example.com/foo")
        self.assertEqual(doc, """Doc text
            """)

        class IURI2(ISpecificURI): """http://example.com/foo"""
        uri, doc = inspectSpecificURI(IURI2)
        self.assertEqual(uri, "http://example.com/foo")
        self.assertEqual(doc, "")

        class IURI3(ISpecificURI): """foo"""
        self.assertRaises(ValueError, inspectSpecificURI, IURI3)

        class IURI4(ISpecificURI):
            """\
            mailto:foo
            """
        uri, doc = inspectSpecificURI(IURI4)
        self.assertEqual(uri, "mailto:foo")
        self.assertEqual(doc, "")

        class IURI5(ISpecificURI):
            """
            mailto:foo
            """
        self.assertRaises(ValueError, inspectSpecificURI, IURI5)

    def test__isURI(self):
        from schooltool.component import isURI
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


class Relatable:
    implements(IRelatable, IQueryLinks)

    def __init__(self):
        self.__links__ = Set()

    def listLinks(self, role):
        return [link for link in self.__links__
                     if link.role.extends(role, False)]

class URISuperior(ISpecificURI): """http://army.gov/ns/superior"""
class URIReport(ISpecificURI): """http://army.gov/ns/report"""
class URICommand(ISpecificURI): """http://army.gov/ns/command"""

class TestRelationships(unittest.TestCase):

    def test_getRelatedObjects(self):
        from schooltool.component import getRelatedObjects, relate
        officer = Relatable()
        soldier = Relatable()
        self.assertEqual(list(getRelatedObjects(officer, URIReport)), [])

        relate(URICommand, (officer, URISuperior), (soldier, URIReport))
        self.assertEqual(list(getRelatedObjects(officer, URIReport)),
                         [soldier])
        self.assertEqual(list(getRelatedObjects(officer, URISuperior)), [])

class TestRelate(unittest.TestCase):
    def setUp(self):
        from schooltool import component
        self.real_relate3 = component.relate3
        component.relate3 = self.stub = Stub_relate3()

    def tearDown(self):
        from schooltool import component
        component.relate3 = self.real_relate3

    def test_relate(self):
        from schooltool.component import relate
        title = 'a title'
        a = object()
        role_a = URISuperior
        b = object()
        role_b = URIReport
        links = relate(URICommand, (a, role_a), (b, role_b), title='a title')
        self.assertEqual(len(links), 2)
        self.assertEqual(self.stub.reltype, URICommand)
        self.assertEqual(self.stub.title, title)
        self.assert_(self.stub.a is a)
        self.assert_(self.stub.role_a is role_a)
        self.assert_(self.stub.b is b)
        self.assert_(self.stub.role_b is role_b)

    def test_relate_membership(self):
        from schooltool.component import relate
        from schooltool.interfaces import URIGroup, URIMember, URIMembership
        from schooltool.model import GroupLink, MemberLink

        m = MemberStub()
        g = GroupStub()

        links = relate(URIMembership, (g, URIGroup), (m, URIMember))
        self.assertEqual(len(links), 2)
        self.assertEqual(type(links[0]), MemberLink)
        self.assertEqual(type(links[1]), GroupLink)

        links = relate(URIMembership, (g, URIGroup), (m, URIMember),
                       title="Membership")
        self.assertEqual(len(links), 2)
        self.assertEqual(type(links[0]), MemberLink)
        self.assertEqual(type(links[1]), GroupLink)

        links = relate(URIMembership,  (m, URIMember), (g, URIGroup))
        self.assertEqual(len(links), 2)
        self.assertEqual(type(links[0]), GroupLink)
        self.assertEqual(type(links[1]), MemberLink)

        links = relate(URIMember,  (m, URIMember), (g, URIGroup))
        self.assertEqual(len(links), 2)
        self.assertNotEqual(type(links[0]), GroupLink)
        self.assertNotEqual(type(links[1]), MemberLink)

        self.assertRaises(TypeError, relate,
                          URIMembership,  (m, URIMember), (g, URISuperior))

        self.assertRaises(TypeError, relate,
                          URIMembership,  (m, URIMember), (g, URISuperior),
                          title="foo")


class Stub_relate3:
    reltype = None
    title = None
    a = None
    role_a = None
    b = None
    role_b = None
    def __call__(self, reltype, (a, role_a), (b, role_b), title=None):
        self.reltype = reltype
        self.title = title
        self.a = a
        self.role_a = role_a
        self.b = b
        self.role_b = role_b
        return object(), object()


class MemberStub:
    pass

class GroupStub:
    def add(self, value):
        return "name"


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestGetAdapter))
    suite.addTest(unittest.makeSuite(TestCanonicalPath))
    suite.addTest(unittest.makeSuite(TestFacetFunctions))
    suite.addTest(unittest.makeSuite(TestServiceAPI))
    suite.addTest(unittest.makeSuite(TestSpecificURI))
    suite.addTest(unittest.makeSuite(TestRelationships))
    suite.addTest(unittest.makeSuite(TestRelate))
    return suite

if __name__ == '__main__':
    unittest.main()
