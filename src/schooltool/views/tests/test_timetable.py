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
Unit tests for schooltool.views.timetable

$Id$
"""

import unittest
from zope.interface import implements
from schooltool.interfaces import IServiceManager, ILocation
from schooltool.views.tests import RequestStub
from schooltool.tests.utils import XMLCompareMixin

__metaclass__ = type


class TimetableStub(dict):

    def cloneEmpty(self):
        return TimetableStub()


class TimetabledStub:
    implements(ILocation)

    def __init__(self):
        self.timetables = {}

    def getCompositeTimetable(self, schema_id, period_id):
        try:
            tt = self.timetables[schema_id, period_id]
        except KeyError:
            return None
        else:
            copy = tt.cloneEmpty()
            copy.update(tt)
            return copy


class TestTimetableTraverseViews(unittest.TestCase):

    def do_test(self, view_class, tt_view_class):
        context = TimetabledStub()
        tt = context.timetables[('weekly', '2003 fall')] = TimetableStub()
        view = view_class(context)
        request = RequestStub()

        result = view.render(request)
        self.assertEquals(request.code, 404)

        view2 = view._traverse('2003 fall', request)
        self.assert_(view2.__class__ is view_class,
                     '%r is not %r' % (view2.__class__, view_class))
        self.assert_(view2.context is context)
        self.assertEquals(view2.time_period, '2003 fall')

        view3 = view2._traverse('weekly', request)
        self.assert_(view3.__class__ is tt_view_class,
                     '%r is not %r' % (view3.__class__, tt_view_class))

        return view2, view3, context, tt

    def test_TimetableTraverseView(self):
        from schooltool.views.timetable import TimetableTraverseView
        from schooltool.views.timetable import TimetableReadWriteView
        view2, view, context, tt = self.do_test(TimetableTraverseView,
                                                TimetableReadWriteView)
        self.assert_(view.context is tt)
        self.assert_(view.timetabled is context)
        self.assertEquals(view.key, ('weekly', '2003 fall'))

        # traversing to nonexistent timetables is allowed
        request = RequestStub()
        view = view2._traverse('eewkly', request)
        self.assert_(view.context is None)
        self.assert_(view.timetabled is context)
        self.assertEquals(view.key, ('eewkly', '2003 fall'))

    def test_CompositeTimetableTraverseView(self):
        from schooltool.views.timetable import CompositeTimetableTraverseView
        from schooltool.views.timetable import TimetableReadView
        view2, view, context, tt = self.do_test(CompositeTimetableTraverseView,
                                                TimetableReadView)
        self.assertEqual(view.context, tt)
        self.assert_(view.context is not tt)

        request = RequestStub()
        self.assertRaises(KeyError, view2._traverse, 'eewkly', request)


class TestTimetableReadView(XMLCompareMixin, unittest.TestCase):

    empty_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <day id="Day 1">
            <period id="A">
            </period>
            <period id="B">
            </period>
          </day>
          <day id="Day 2">
            <period id="C">
            </period>
            <period id="D">
            </period>
          </day>
        </timetable>
        """

    full_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <day id="Day 1">
            <period id="A">
              <activity>Maths</activity>
            </period>
            <period id="B">
              <activity>English</activity>
              <activity>French</activity>
            </period>
          </day>
          <day id="Day 2">
            <period id="C">
              <activity>CompSci</activity>
            </period>
            <period id="D">
            </period>
          </day>
        </timetable>
        """

    def createEmpty(self):
        from schooltool.timetable import Timetable, TimetableDay
        tt = Timetable(['Day 1', 'Day 2'])
        tt['Day 1'] = TimetableDay(['A', 'B'])
        tt['Day 2'] = TimetableDay(['C', 'D'])
        return tt

    def createFull(self):
        from schooltool.timetable import TimetableActivity
        tt = self.createEmpty()
        tt['Day 1'].add('A', TimetableActivity('Maths'))
        tt['Day 1'].add('B', TimetableActivity('English'))
        tt['Day 1'].add('B', TimetableActivity('French'))
        tt['Day 2'].add('C', TimetableActivity('CompSci'))
        return tt

    def createView(self, context):
        from schooltool.views.timetable import TimetableReadView
        return TimetableReadView(context)

    def test_get(self):
        for context, xml in [(self.createEmpty(), self.empty_xml),
                             (self.createFull(), self.full_xml)]:
            result = self.createView(context).render(RequestStub())
            self.assertEqualsXML(result, xml, recursively_sort=['timetable'])


class TestTimetableReadWriteView(TestTimetableReadView):

    illformed_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <day id="Day 1"
        </timetable>
        """

    invalid_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <week>
            <day id="Day 1" />
          </week>
        </timetable>
        """

    unknown_day_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <day id="Day 1">
            <period id="A">
              <activity>English</activity>
            </period>
            <period id="B">
            </period>
          </day>
          <day id="Day 3">
          </day>
        </timetable>
        """

    unknown_period_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <day id="Day 1">
            <period id="A">
              <activity>English</activity>
            </period>
            <period id="X">
            </period>
          </day>
        </timetable>
        """

    def createTimetabled(self):
        from schooltool.timetable import TimetableSchemaService

        class ServiceManagerStub:
            implements(IServiceManager)

            timetableSchemaService = TimetableSchemaService()
            timetableSchemaService['weekly'] = self.createEmpty()

        timetabled = TimetabledStub()
        timetabled.__parent__ = ServiceManagerStub()
        return timetabled

    def createView(self, context, timetabled=None,
                   key=('2003 fall', 'weekly')):
        from schooltool.views.timetable import TimetableReadWriteView
        if timetabled is None:
            timetabled = self.createTimetabled()
            if context is not None:
                timetabled.timetables[key] = context
        return TimetableReadWriteView(context, timetabled, key)

    def test_get_nonexistent(self):
        view = self.createView(None)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_put(self):
        for context, xml, expected in [
                (self.createEmpty(), self.full_xml, self.createFull()),
                (self.createFull(), self.empty_xml, self.createEmpty())]:
            view = self.createView(context)
            request = RequestStub(method="PUT", body=xml,
                                  headers={'Content-Type': 'text/xml'})
            result = view.render(request)
            self.assertEquals(request.code, 200)
            self.assertEquals(request.headers['Content-Type'], "text/plain")
            self.assertEquals(context, expected)

    def test_put_nonexistent(self):
        key = ('2003 fall', 'weekly')
        timetabled = self.createTimetabled()
        view = self.createView(None, timetabled, key)
        request = RequestStub(method="PUT", body=self.full_xml,
                              headers={'Content-Type': 'text/xml'})
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        expected = self.createFull()
        self.assertEquals(timetabled.timetables[key], expected)

    def do_test_error(self, xml=None, ctype='text/xml'):
        if xml is None:
            xml = self.empty_xml
        context = self.createEmpty()
        view = self.createView(context)
        request = RequestStub(method="PUT", body=xml,
                              headers={'Content-Type': ctype})
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(context, self.createEmpty())

    def test_put_error_handling(self):
        self.do_test_error(ctype='text/plain')
        self.do_test_error(xml=self.illformed_xml)
        self.do_test_error(xml=self.invalid_xml)
        self.do_test_error(xml=self.unknown_day_xml)
        self.do_test_error(xml=self.unknown_period_xml)

    def test_delete(self):
        key = ('2003 fall', 'weekly')
        timetabled = self.createTimetabled()
        context = timetabled.timetables[key] = self.createEmpty()
        view = self.createView(context, timetabled, key)
        request = RequestStub(method="DELETE")
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assert_(key not in timetabled.timetables)

    def test_delete_nonexistent(self):
        view = self.createView(None)
        request = RequestStub(method="DELETE")
        result = view.render(request)
        self.assertEquals(request.code, 404)



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTimetableTraverseViews))
    suite.addTest(unittest.makeSuite(TestTimetableReadView))
    suite.addTest(unittest.makeSuite(TestTimetableReadWriteView))
    return suite

if __name__ == '__main__':
    unittest.main()
