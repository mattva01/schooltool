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
from zope.interface import Interface, implements, directlyProvides
from zope.interface.verify import verifyObject

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
        from schooltool.interfaces import IFacetAPI, IContainmentAPI
        verifyObject(IFacetAPI, component)
        verifyObject(IContainmentAPI, component)

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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestGetAdapter))
    suite.addTest(unittest.makeSuite(TestCanonicalPath))
    suite.addTest(unittest.makeSuite(TestFacetFunctions))
    return suite

if __name__ == '__main__':
    unittest.main()
