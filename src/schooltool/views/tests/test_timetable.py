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
import libxml2
import sets
from zope.interface import implements
from schooltool.interfaces import IServiceManager, ILocation, IContainmentRoot
from schooltool.views.tests import RequestStub, setPath
from schooltool.tests.utils import XMLCompareMixin
from schooltool.tests.utils import RegistriesSetupMixin

__metaclass__ = type


class TimetableStub(dict):

    def cloneEmpty(self):
        return TimetableStub()


class TimetabledStub:
    implements(ILocation)

    def __init__(self):
        self.timetables = {}
        self.overlay = {}

    def getCompositeTimetable(self, period_id, schema_id):
        try:
            tt = self.timetables[period_id, schema_id]
        except KeyError:
            return None
        else:
            copy = tt.cloneEmpty()
            copy.update(tt)
            if (period_id, schema_id) in self.overlay:
                copy.update(self.overlay[period_id, schema_id])
            return copy

    def listCompositeTimetables(self):
        return sets.Set(self.timetables.keys() + self.overlay.keys())


class ServiceManagerStub:
    implements(IServiceManager, IContainmentRoot)

    def __init__(self, weekly_tt):
        from schooltool.timetable import TimetableSchemaService
        from schooltool.timetable import TimePeriodService
        self.timetableSchemaService = TimetableSchemaService()
        self.timetableSchemaService['weekly'] = weekly_tt
        self.timePeriodService = TimePeriodService()
        self.timePeriodService.register('2003 fall')


class TestTimetableTraverseViews(XMLCompareMixin, unittest.TestCase):

    def do_test(self, view_class, tt_view_class, xml=None, html=None):
        context = TimetabledStub()
        setPath(context, '/...object', ServiceManagerStub(TimetableStub()))
        tt = context.timetables['2003 fall', 'weekly'] = TimetableStub()
        context.overlay['2003 spring', 'weekly'] = TimetableStub()
        view = view_class(context)
        request = RequestStub()

        if xml:
            result = view.render(request)
            self.assertEquals(request.code, 200)
            self.assertEquals(request.headers['Content-Type'],
                              "text/xml; charset=UTF-8")
            self.assertEqualsXML(result, xml, recursively_sort=['timetables'])

        if html:
            request.accept = [('1', 'text/html', {}, {})]
            result = view.render(request)
            self.assertEquals(request.code, 200)
            self.assertEquals(request.headers['Content-Type'],
                              "text/html; charset=UTF-8")
            self.assertEqualsXML(result, html, recursively_sort=['ul'])

        view2 = view._traverse('2003 fall', request)
        self.assert_(view2.__class__ is view_class,
                     '%r is not %r' % (view2.__class__, view_class))
        self.assert_(view2.context is context)
        self.assertEquals(view2.time_period, '2003 fall')

        result = view2.render(request)
        self.assertEquals(request.code, 404)

        view3 = view2._traverse('weekly', request)
        self.assert_(view3.__class__ is tt_view_class,
                     '%r is not %r' % (view3.__class__, tt_view_class))

        return view, view2, view3, context, tt

    def test_TimetableTraverseView(self):
        from schooltool.views.timetable import TimetableTraverseView
        from schooltool.views.timetable import TimetableReadWriteView
        view1, view2, view3, context, tt = self.do_test(
            TimetableTraverseView, TimetableReadWriteView,
            """
            <timetables xmlns:xlink="http://www.w3.org/1999/xlink">
              <timetable period="2003 fall" schema="weekly" xlink:type="simple"
                         xlink:href="/...object/timetable/2003 fall/weekly" />
            </timetables>
            """, """
            <html>
            <head>
              <title>Timetables for /...object</title>
            </head>
            <body>
              <h1>Timetables for /...object</h1>
              <ul>
                <li><a href="/...object/timetable/2003 fall/weekly"
                    >2003 fall, weekly</a></li>
              </ul>
            </body>
            </html>
            """)
        self.assert_(view3.timetabled is context)
        self.assertEquals(view3.key, ('2003 fall', 'weekly'))
        self.assert_(view3.context is tt, '%r is not %r' % (view3.context, tt))

        # traversing to nonexistent timetables is allowed
        request = RequestStub()
        view = view2._traverse('eewkly', request)
        self.assert_(view.context is None)
        self.assert_(view.timetabled is context)
        self.assertEquals(view.key, ('2003 fall', 'eewkly'))

    def test_CompositeTimetableTraverseView(self):
        from schooltool.views.timetable import CompositeTimetableTraverseView
        from schooltool.views.timetable import TimetableReadView
        view1, view2, view3, context, tt = self.do_test(
            CompositeTimetableTraverseView, TimetableReadView,
            """
            <timetables xmlns:xlink="http://www.w3.org/1999/xlink">
              <timetable period="2003 fall" schema="weekly" xlink:type="simple"
                xlink:href="/...object/composite-timetable/2003 fall/weekly" />
              <timetable period="2003 spring" schema="weekly"
                 xlink:href="/...object/composite-timetable/2003 spring/weekly"
                 xlink:type="simple" />
            </timetables>
            """, """
            <html>
            <head>
              <title>Composite timetables for /...object</title>
            </head>
            <body>
              <h1>Composite timetables for /...object</h1>
              <ul>
                <li><a href="/...object/composite-timetable/2003 fall/weekly"
                    >2003 fall, weekly</a></li>
                <li><a href="/...object/composite-timetable/2003 spring/weekly"
                    >2003 spring, weekly</a></li>
              </ul>
            </body>
            </html>
            """)
        self.assertEqual(view3.context, tt)
        self.assert_(view3.context is not tt)

        request = RequestStub()
        self.assertRaises(KeyError, view2._traverse, 'eewkly', request)

    def test_SchoolTimetableTraverseView(self):
        from schooltool.views.timetable import SchoolTimetableTraverseView
        from schooltool.views.timetable import SchoolTimetableView
        view1, view2, view3, context, tt = (
            self.do_test(SchoolTimetableTraverseView,
                         SchoolTimetableView)
            )
        self.assertEqual(view3.context, context)

        request = RequestStub()
        self.assertRaises(KeyError, view2._traverse, 'eewkly', request)
        self.assertRaises(KeyError, view1._traverse, '2033 faal', request)


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

    empty_html = """
        <html>
        <head>
          <title>Timetable ...object/timetable/x/y</title>
        </head>
        <body>
          <h1>Timetable ...object/timetable/x/y</h1>
          <table>
            <tr>
              <th colspan="2">Day 1</th>
              <th colspan="2">Day 2</th>
            </tr>
            <tr>
              <th>A</th>
              <td></td>
              <th>C</th>
              <td></td>
            </tr>
            <tr>
              <th>B</th>
              <td></td>
              <th>D</th>
              <td></td>
            </tr>
          </table>
        </body>
        </html>
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

    full_html = """
        <html>
        <head>
          <title>Timetable ...object/timetable/x/y</title>
        </head>
        <body>
          <h1>Timetable ...object/timetable/x/y</h1>
          <table>
            <tr>
              <th colspan="2">Day 1</th>
              <th colspan="2">Day 2</th>
            </tr>
            <tr>
              <th>A</th>
              <td>Maths</td>
              <th>C</th>
              <td>CompSci</td>
            </tr>
            <tr>
              <th>B</th>
              <td>English / French</td>
              <th>D</th>
              <td></td>
            </tr>
          </table>
        </body>
        </html>
        """

    def createEmpty(self):
        from schooltool.timetable import Timetable, TimetableDay
        tt = Timetable(['Day 1', 'Day 2'])
        tt['Day 1'] = TimetableDay(['A', 'B'])
        tt['Day 2'] = TimetableDay(['C', 'D'])
        return tt

    def createFull(self, owner=None):
        from schooltool.timetable import TimetableActivity
        tt = self.createEmpty()
        tt['Day 1'].add('A', TimetableActivity('Maths', owner))
        tt['Day 1'].add('B', TimetableActivity('English', owner))
        tt['Day 1'].add('B', TimetableActivity('French', owner))
        tt['Day 2'].add('C', TimetableActivity('CompSci', owner))
        return tt

    def createView(self, context):
        from schooltool.views.timetable import TimetableReadView
        return TimetableReadView(context)

    def do_test_get(self, context, expected, ctype="text/xml", accept=()):
        request = RequestStub('...object/timetable/x/y')
        request.accept = accept
        result = self.createView(context).render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "%s; charset=UTF-8" % ctype)
        self.assertEqualsXML(result, expected, recursively_sort=['timetable'])

    def test_get(self):
        self.do_test_get(self.createEmpty(), self.empty_xml)
        self.do_test_get(self.createFull(), self.full_xml)

    def test_get_html(self):
        self.do_test_get(self.createEmpty(), self.empty_html,
                         accept=[('1', 'text/html', {}, {})],
                         ctype='text/html')
        self.do_test_get(self.createFull(), self.full_html,
                         accept=[('1', 'text/html', {}, {})],
                         ctype='text/html')


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

    def setUp(self):
        TestTimetableReadView.setUp(self)
        libxml2.registerErrorHandler(lambda ctx, error: None, None)

    def createTimetabled(self):
        from schooltool.timetable import TimetableSchemaService
        from schooltool.timetable import TimePeriodService
        timetabled = TimetabledStub()
        timetabled.__parent__ = ServiceManagerStub(self.createEmpty())
        return timetabled

    def createView(self, context=None, timetabled=None,
                   key=('2003 fall', 'weekly')):
        from schooltool.views.timetable import TimetableReadWriteView
        if timetabled is None:
            timetabled = self.createTimetabled()
            if context is not None:
                timetabled.timetables[key] = context
        return TimetableReadWriteView(timetabled, key)

    def test_get_nonexistent(self):
        view = self.createView(None)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_put(self):
        key = ('2003 fall', 'weekly')
        ttd = self.createTimetabled()

        ttd.timetables[key] = self.createEmpty()
        expected = self.createFull(ttd)
        self.do_test_put(ttd, key, self.full_xml, expected)

        ttd.timetables[key] = self.createFull(ttd)
        expected = self.createEmpty()
        self.do_test_put(ttd, key, self.empty_xml, expected)

    def do_test_put(self, timetabled, key, xml, expected):
        view = self.createView(timetabled=timetabled, key=key)
        request = RequestStub(method="PUT", body=xml,
                              headers={'Content-Type': 'text/xml'})
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(timetabled.timetables[key], expected)

    def test_put_nonexistent(self):
        key = ('2003 fall', 'weekly')
        timetabled = self.createTimetabled()
        expected = self.createFull(timetabled)
        self.do_test_put(timetabled, key, self.full_xml, expected)

    def test_put_bad_schema(self):
        key = ('2003 fall', 'wekly')
        timetabled = self.createTimetabled()
        view = self.createView(None, timetabled, key)
        request = RequestStub(method="PUT", body=self.full_xml,
                              headers={'Content-Type': 'text/xml'})
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assert_(key not in timetabled.timetables)

    def test_put_bad_period(self):
        key = ('2003 faal', 'weekly')
        timetabled = self.createTimetabled()
        view = self.createView(None, timetabled, key)
        request = RequestStub(method="PUT", body=self.full_xml,
                              headers={'Content-Type': 'text/xml'})
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assert_(key not in timetabled.timetables)

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


class TestTimetableSchemaView(TestTimetableReadView):

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

    duplicate_day_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <day id="Day 1">
            <period id="A">
            </period>
            <period id="B">
            </period>
          </day>
          <day id="Day 1">
          </day>
        </timetable>
        """

    duplicate_period_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <day id="Day 1">
            <period id="A">
            </period>
            <period id="A">
            </period>
          </day>
        </timetable>
        """

    def createView(self, context, service=None, key='weekly'):
        from schooltool.timetable import TimetableSchemaService
        from schooltool.views.timetable import TimetableSchemaView
        if service is None:
            service = TimetableSchemaService()
            if context is not None:
                service[key] = context
        return TimetableSchemaView(service, key)

    def test_get(self):
        """overrides TestTimetableReadView.test_get"""
        self.do_test_get(self.createEmpty(), self.empty_xml)

    def test_get_html(self):
        """overrides TestTimetableReadView.test_get"""
        self.do_test_get(self.createEmpty(), self.empty_html,
                         accept=[('1', 'text/html', {}, {})],
                         ctype='text/html')

    def test_get_nonexistent(self):
        view = self.createView(None)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_delete(self):
        from schooltool.timetable import TimetableSchemaService
        key = 'weekly'
        service = TimetableSchemaService()
        context = service[key] = self.createEmpty()
        view = self.createView(context, service, key)
        request = RequestStub(method="DELETE")
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertRaises(KeyError, lambda: service[key])

    def test_delete_nonexistent(self):
        view = self.createView(None)
        request = RequestStub(method="DELETE")
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_put(self):
        from schooltool.timetable import TimetableSchemaService
        key = 'weekly'
        service = TimetableSchemaService()
        view = self.createView(None, service, key)
        request = RequestStub(method="PUT", body=self.empty_xml,
                              headers={'Content-Type': 'text/xml'})
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(service[key], self.createEmpty())

    def do_test_error(self, xml=None, ctype='text/xml'):
        from schooltool.timetable import TimetableSchemaService
        if xml is None:
            xml = self.empty_xml
        key = 'weekly'
        service = TimetableSchemaService()
        view = self.createView(None, service, key)
        request = RequestStub(method="PUT", body=xml,
                              headers={'Content-Type': ctype})
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertRaises(KeyError, lambda: service[key])

    def test_put_error_handling(self):
        self.do_test_error(ctype='text/plain')
        self.do_test_error(xml=self.illformed_xml)
        self.do_test_error(xml=self.invalid_xml)
        self.do_test_error(xml=self.full_xml)
        self.do_test_error(xml=self.duplicate_day_xml)
        self.do_test_error(xml=self.duplicate_period_xml)


class TestTimetableSchemaServiceView(XMLCompareMixin, unittest.TestCase):

    def test_get(self):
        from schooltool.timetable import TimetableSchemaService, Timetable
        from schooltool.views.timetable import TimetableSchemaServiceView
        context = TimetableSchemaService()
        setPath(context, '/ttservice')
        view = TimetableSchemaServiceView(context)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <timetableSchemas xmlns:xlink="http://www.w3.org/1999/xlink">
            </timetableSchemas>
            """)

        context['weekly'] = Timetable()
        context['4day'] = Timetable()
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <timetableSchemas xmlns:xlink="http://www.w3.org/1999/xlink">
              <schema xlink:title="4day" xlink:type="simple"
                      xlink:href="/ttservice/4day" />
              <schema xlink:title="weekly" xlink:type="simple"
                      xlink:href="/ttservice/weekly" />
            </timetableSchemas>
            """, recursively_sort=['timetableSchemas'])

    def test_traverse(self):
        from schooltool.timetable import TimetableSchemaService, Timetable
        from schooltool.views.timetable import TimetableSchemaServiceView
        from schooltool.views.timetable import TimetableSchemaView
        context = TimetableSchemaService()
        tt = context['weekly'] = Timetable()
        view = TimetableSchemaServiceView(context)
        request = RequestStub()

        result = view._traverse('weekly', request)
        self.assert_(result.__class__ is TimetableSchemaView)
        self.assertEquals(result.context, tt)
        self.assert_(result.service is context)
        self.assertEquals(result.key, 'weekly')

        result = view._traverse('newone', request)
        self.assert_(result.__class__ is TimetableSchemaView)
        self.assert_(result.context is None)
        self.assert_(result.service is context)
        self.assertEquals(result.key, 'newone')


class TestSchoolTimetableView(XMLCompareMixin, RegistriesSetupMixin,
                              unittest.TestCase):

    def setUp(self):
        from schooltool.views.timetable import SchoolTimetableView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool.teaching import TeacherFacet, Teaching
        from schooltool.component import FacetManager
        from schooltool import membership
        from schooltool import relationship
        self.setUpRegistries()
        membership.setUp()
        relationship.setUp()
        app = Application()

        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.teachers = app['groups'].new("teachers", title="teachers")

        self.teacher1 = app['persons'].new("p1", title="Albert")
        Membership(group=self.teachers, member=self.teacher1)
        FacetManager(self.teacher1).setFacet(TeacherFacet())

        self.teacher2 = app['persons'].new("p2", title="Marius")
        Membership(group=self.teachers, member=self.teacher2)
        FacetManager(self.teacher2).setFacet(TeacherFacet())

        self.sg1 = app['groups'].new("sg1", title="Math 1")
        self.sg2 = app['groups'].new("sg2", title="Calculus 1")
        self.sg3 = app['groups'].new("sg3", title="Chemistry 1")
        self.sg4 = app['groups'].new("sg4", title="Physics 1")

        Teaching(teacher=self.teacher1, taught=self.sg1)
        Teaching(teacher=self.teacher1, taught=self.sg2)
        Teaching(teacher=self.teacher2, taught=self.sg3)
        Teaching(teacher=self.teacher2, taught=self.sg4)

        self.view = SchoolTimetableView(app, key=('2003-spring', '2day'))

    def testEmpty(self):
        request = RequestStub()
        result = self.view.render(request)
        expected = """
            <schooltt xmlns="http://schooltool.org/ns/timetable/0.1">
              <teacher path="/persons/p2">
              </teacher>
              <teacher path="/persons/p1">
              </teacher>
            </schooltt>
            """
        self.assertEqualsXML(result, expected, recursively_sort=['schooltt'])

    def testNonempty(self):
        from schooltool.timetable import Timetable, TimetableDay
        from schooltool.timetable import TimetableActivity

        tt = Timetable(("A", "B"))
        tt["A"] = TimetableDay(("Green", "Blue"))
        tt["B"] = TimetableDay(("Red", "Yellow"))
        tt["A"].add("Green", TimetableActivity("Slacking", self.sg1))
        self.sg1.timetables['2003-spring', '2day'] = tt

        tt = tt.cloneEmpty()
        tt["A"].add("Blue", TimetableActivity("Slashdot", self.sg2))
        self.sg2.timetables['2003-spring', '2day'] = tt

        tt = tt.cloneEmpty()
        tt["B"].add("Red", TimetableActivity("Email", self.sg3))
        self.sg3.timetables['2003-spring', '2day'] = tt

        request = RequestStub()
        result = self.view.render(request)
        expected = """
            <schooltt xmlns="http://schooltool.org/ns/timetable/0.1">
              <teacher path="/persons/p2">
                <day id="A">
                  <period id="Blue">
                  </period>
                  <period id="Green">
                  </period>
                </day>
                <day id="B">
                  <period id="Red">
                    <activity group="/groups/sg3">
                      Email
                    </activity>
                  </period>
                  <period id="Yellow">
                  </period>
                </day>
              </teacher>
              <teacher path="/persons/p1">
                <day id="A">
                  <period id="Blue">
                    <activity group="/groups/sg2">
                      Slashdot
                    </activity>
                  </period>
                  <period id="Green">
                    <activity group="/groups/sg1">
                      Slacking
                    </activity>
                  </period>
                </day>
                <day id="B">
                  <period id="Red">
                  </period>
                  <period id="Yellow">
                  </period>
                </day>
              </teacher>
            </schooltt>
            """
        self.assertEqualsXML(result, expected, recursively_sort=['schooltt'])


class TestTimePeriodServiceView(XMLCompareMixin, unittest.TestCase):

    def test_get(self):
        from schooltool.timetable import TimePeriodService
        from schooltool.views.timetable import TimePeriodServiceView
        context = TimePeriodService()
        setPath(context, '/time-periods')
        view = TimePeriodServiceView(context)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <timePeriods xmlns:xlink="http://www.w3.org/1999/xlink">
            </timePeriods>
            """)

        context.register('2003 fall')
        context.register('2004 spring')
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <timePeriods xmlns:xlink="http://www.w3.org/1999/xlink">
              <period xlink:title="2003 fall" xlink:type="simple"
                      xlink:href="/time-periods/2003 fall" />
              <period xlink:title="2004 spring" xlink:type="simple"
                      xlink:href="/time-periods/2004 spring" />
            </timePeriods>
            """, recursively_sort=['timePeriods'])

    def test_traverse(self):
        from schooltool.timetable import TimePeriodService
        from schooltool.views.timetable import TimePeriodServiceView
        from schooltool.views.timetable import TimePeriodCreatorView
        context = TimePeriodService()
        context.register('2003 fall')
        view = TimePeriodServiceView(context)
        request = RequestStub()

        result = view._traverse('2003 fall', request)
        self.assert_(result.__class__ is TimePeriodCreatorView)
        self.assert_(result.service is context)
        self.assertEquals(result.key, '2003 fall')

        result = view._traverse('2004 fall', request)
        self.assert_(result.__class__ is TimePeriodCreatorView)
        self.assert_(result.service is context)
        self.assertEquals(result.key, '2004 fall')


class TestTimePeriodCreatorView(unittest.TestCase):

    def test_get(self):
        from schooltool.timetable import TimePeriodService
        from schooltool.views.timetable import TimePeriodCreatorView
        service = TimePeriodService()
        key = '2003 fall'
        view = TimePeriodCreatorView(service, key)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_put(self):
        from schooltool.timetable import TimePeriodService
        from schooltool.views.timetable import TimePeriodCreatorView
        service = TimePeriodService()
        key = '2003 fall'
        view = TimePeriodCreatorView(service, key)
        request = RequestStub(method='PUT')
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assert_(key in service)

    def test_delete(self):
        from schooltool.timetable import TimePeriodService
        from schooltool.views.timetable import TimePeriodCreatorView
        service = TimePeriodService()
        key = '2003 fall'
        service.register(key)
        view = TimePeriodCreatorView(service, key)
        request = RequestStub(method='DELETE')
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assert_(key not in service)

    def test_delete_nonexistent(self):
        from schooltool.timetable import TimePeriodService
        from schooltool.views.timetable import TimePeriodCreatorView
        service = TimePeriodService()
        key = '2003 fall'
        view = TimePeriodCreatorView(service, key)
        request = RequestStub(method='DELETE')
        result = view.render(request)
        self.assertEquals(request.code, 404)


class TestModuleSetup(RegistriesSetupMixin, unittest.TestCase):

    def test(self):
        from schooltool.timetable import TimetableSchemaService
        from schooltool.timetable import TimePeriodService
        from schooltool.views.timetable import TimetableSchemaServiceView
        from schooltool.views.timetable import TimePeriodServiceView
        from schooltool.component import getView
        import schooltool.views.timetable
        schooltool.views.timetable.setUp()

        def viewClass(obj):
            return getView(obj).__class__

        self.assert_(viewClass(TimePeriodService()) is TimePeriodServiceView)
        self.assert_(viewClass(TimetableSchemaService())
                        is TimetableSchemaServiceView)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTimetableTraverseViews))
    suite.addTest(unittest.makeSuite(TestTimetableReadView))
    suite.addTest(unittest.makeSuite(TestTimetableReadWriteView))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaView))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaServiceView))
    suite.addTest(unittest.makeSuite(TestSchoolTimetableView))
    suite.addTest(unittest.makeSuite(TestTimePeriodServiceView))
    suite.addTest(unittest.makeSuite(TestTimePeriodCreatorView))
    suite.addTest(unittest.makeSuite(TestModuleSetup))
    return suite

if __name__ == '__main__':
    unittest.main()
