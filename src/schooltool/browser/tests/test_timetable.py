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
Unit tests for schooltool.browser.timetable

$Id$
"""

import unittest

from schooltool.browser.tests import RequestStub
from schooltool.browser.tests import TraversalTestMixin
from schooltool.browser.tests.test_model import AppSetupMixin

__metaclass__ = type


class TestTimetableTraverseView(AppSetupMixin, TraversalTestMixin,
                                unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.browser.timetable import TimetableTraverseView
        return TimetableTraverseView(self.person)

    def assertTraversesEq(self, view, name, viewclass, context=None):
        """Assert that traversal returns the appropriate view.

        Checks that view._traverse(name, request) returns an instance of
        viewclass, and that the context attribute of the new view is
        equivalent (as opposed to identical) to context.

        """
        request = RequestStub()
        destination = view._traverse(name, request)
        self.assert_(isinstance(destination, viewclass))
        self.assertEquals(destination.context, context)
        return destination

    def test_render(self):
        view = self.createView()
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_traverse(self):
        from schooltool.browser.timetable import TimetableTraverseView
        from schooltool.browser.timetable import TimetableView
        from schooltool.timetable import Timetable
        view = self.createView()
        t1 = self.person.timetables['2004-spring', 'default'] = Timetable([])
        t2 = self.person.timetables['2004-spring', 'another'] = Timetable([])
        t3 = self.person.timetables['2003-fall', 'another'] = Timetable([])
        t4 = self.root.timetables['2003-fall', 'default'] = Timetable([])
        view2 = self.assertTraverses(view, '2004-spring',
                                     TimetableTraverseView, view.context)
        v1 = self.assertTraversesEq(view2, 'default', TimetableView, t1)
        v2 = self.assertTraversesEq(view2, 'another', TimetableView, t2)
        self.assertRaises(KeyError, view2._traverse, 'missing', RequestStub())
        view2 = self.assertTraverses(view, '2003-fall',
                                     TimetableTraverseView, view.context)
        v3 = self.assertTraversesEq(view2, 'another', TimetableView, t3)
        v4 = self.assertTraversesEq(view2, 'default', TimetableView, t4)
        self.assertRaises(KeyError, view2._traverse, 'missing', RequestStub())

        self.assertEquals(v1.key, ('2004-spring', 'default'))
        self.assertEquals(v2.key, ('2004-spring', 'another'))
        self.assertEquals(v3.key, ('2003-fall', 'another'))
        self.assertEquals(v4.key, ('2003-fall', 'default'))


class TestTimetableView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.timetable import Timetable
        from schooltool.browser.timetable import TimetableView
        key = ('2004 fall', 'default')
        self.person.timetables[key] = Timetable([])
        self.person.title = 'John Smith'
        return TimetableView(self.person.timetables[key], key)

    def test_render(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.person)
        result = view.render(request)
        self.assertEquals(request.code, 200)

    def test_title(self):
        view = self.createView()
        view.request = RequestStub()
        self.assertEquals(view.title(),
                          "John Smith's timetable for 2004 fall, default")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTimetableTraverseView))
    suite.addTest(unittest.makeSuite(TestTimetableView))
    return suite


if __name__ == '__main__':
    unittest.main()
