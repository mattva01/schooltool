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
Unit tests for schooltool.adapters

$Id$
"""

import unittest
from zope.interface import Interface, implements, directlyProvides

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
        from schooltool.adapters import adapterRegistry
        self.reg = adapterRegistry.copy()

    def tearDown(self):
        from schooltool.adapters import adapterRegistry
        self.adapterRegistry = self.reg

    def test_getAdapter(self):
        from schooltool.adapters import getAdapter, provideAdapter
        from schooltool.adapters import ComponentLookupError
        provideAdapter(I1, C1)
        self.assertEqual(getAdapter(object(), I1).foo(), "foo")
        self.assertRaises(ComponentLookupError, getAdapter, object(), I2)

    def test_getAdapter_provided(self):
        from schooltool.adapters import getAdapter, provideAdapter
        ob = C1(None)
        self.assertEqual(getAdapter(ob, I1), ob)


class TestCanonicalPath(unittest.TestCase):

    def test_path(self):
        from schooltool.adapters import getPath
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

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestGetAdapter))
    suite.addTest(unittest.makeSuite(TestCanonicalPath))
    return suite

if __name__ == '__main__':
    unittest.main()
