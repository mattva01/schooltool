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
import datetime
from sets import Set
from zope.interface import implements
from schooltool.interfaces import IServiceManager, ILocation, IContainmentRoot
from schooltool.interfaces import ITraversable
from schooltool.views.tests import RequestStub, TraversableRoot, setPath
from schooltool.tests.helpers import dedent
from schooltool.tests.utils import XMLCompareMixin
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.tests.utils import QuietLibxml2Mixin
from schooltool.schema.rng import validate_against_schema

__metaclass__ = type


class TimetableStub(dict):

    def cloneEmpty(self):
        return TimetableStub()


class TimetabledStub:
    implements(ILocation)

    def __init__(self):
        self.timetables = {}
        self.overlay = {}
        self.title = "Foo"

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
        return Set(self.timetables.keys() + self.overlay.keys())


class ResourceStub(TimetabledStub):

    def __init__(self, name, title):
        TimetabledStub.__init__(self)
        self.title = title
        self.__name__ = 'resources/%s' % name
        self.__parent__ = TraversableRoot()


class ResourceContainer(dict):
    implements(ITraversable)

    def traverse(self, name):
        return self[name]


class SchooldayModelStub:
    implements(ILocation)

    __parent__ = None
    __name__ = None

    first = datetime.date(2003, 9, 1)
    last = datetime.date(2003, 9, 30)

    def __iter__(self):
        return iter([])

    def isSchoolday(day):
        return False


class ServiceManagerStub:
    implements(IServiceManager, IContainmentRoot, ITraversable)

    def __init__(self, weekly_tt=None):
        from schooltool.timetable import TimetableSchemaService
        from schooltool.timetable import TimePeriodService
        self.timetableSchemaService = TimetableSchemaService()
        if weekly_tt is not None:
            self.timetableSchemaService['weekly'] = weekly_tt
        self.timePeriodService = TimePeriodService()
        self.timePeriodService['2003 fall'] = SchooldayModelStub()
        self.resources = ResourceContainer()
        self.resources['room1'] = ResourceStub('room1', 'Room 1')
        self.resources['lab1'] = ResourceStub('lab1', 'CS Lab 1')
        self.resources['lab2'] = ResourceStub('lab2', 'CS Lab 2')

    def traverse(self, name):
        return {'resources': self.resources}[name]


class TestTimetableContentNegotiation(unittest.TestCase):

    def test(self):
        from schooltool.views.timetable import TimetableContentNegotiation
        cn = TimetableContentNegotiation()
        cn.template = 'xml'
        cn.html_template = 'html'
        cn.wxhtml_template = 'wxhtml'

        rq = RequestStub()
        self.assertEquals(cn.chooseRepresentation(rq), 'xml')
        rq = RequestStub(accept=[(1, 'text/html', {}, {})])
        self.assertEquals(cn.chooseRepresentation(rq), 'html')
        rq = RequestStub(accept=[(1, 'text/xml', {}, {}),
                                 (0.9, 'text/html', {}, {})])
        self.assertEquals(cn.chooseRepresentation(rq), 'xml')
        rq = RequestStub(headers={'User-Agent': 'some variant of Mozilla'},
                         accept=[(1, 'text/xml', {}, {}),
                                 (0.9, 'text/html', {}, {})])
        self.assertEquals(cn.chooseRepresentation(rq), 'html')
        rq = RequestStub(headers={'User-Agent': 'wxWindows'})
        self.assertEquals(cn.chooseRepresentation(rq), 'wxhtml')


class TestTimetableTraverseViews(XMLCompareMixin, unittest.TestCase):

    def do_test(self, view_class, tt_view_class, xml=None, html=None,
                path='/..object', kwargs=None):
        if kwargs is None:
            kwargs = {}
        context = TimetabledStub()
        setPath(context, path, ServiceManagerStub(TimetableStub()))
        tt = context.timetables['2003 fall', 'weekly'] = TimetableStub()
        context.overlay['2003 spring', 'weekly'] = TimetableStub()
        view = view_class(context, **kwargs)
        view.authorization = lambda ctx, rq: True
        request = RequestStub()

        result = view.render(request)
        if xml:
            self.assertEquals(request.code, 200)
            self.assertEquals(request.headers['content-type'],
                              "text/xml; charset=UTF-8")
            self.assertEqualsXML(result, xml, recursively_sort=['timetables'])
        else:
            self.assertEquals(request.code, 404)

        request.accept = [('1', 'text/html', {}, {})]
        result = view.render(request)
        if html:
            self.assertEquals(request.code, 200)
            self.assertEquals(request.headers['content-type'],
                              "text/html; charset=UTF-8")
            self.assertEqualsXML(result, html, recursively_sort=['ul'])
        else:
            self.assertEquals(request.code, 404)

        view2 = view._traverse('2003 fall', request)
        self.assert_(view2.__class__ is view_class,
                     '%r is not %r' % (view2.__class__, view_class))
        self.assert_(view2.context is context)
        self.assertEquals(view2.time_period, '2003 fall')

        view2.authorization = lambda ctx, rq: True
        result = view2.render(request)
        self.assertEquals(request.code, 404)

        view3 = view2._traverse('weekly', request)
        view3.authorization = lambda ctx, rq: True
        self.assert_(view3.__class__ is tt_view_class,
                     '%r is not %r' % (view3.__class__, tt_view_class))

        return view, view2, view3, context, tt

    def test_TimetableTraverseView_rw(self):
        from schooltool.views.timetable import TimetableTraverseView
        from schooltool.views.timetable import TimetableReadWriteView
        view1, view2, view3, context, tt = self.do_test(
            TimetableTraverseView, TimetableReadWriteView,
            """
            <timetables xmlns:xlink="http://www.w3.org/1999/xlink">
              <timetable period="2003 fall" schema="weekly" xlink:type="simple"
                         xlink:href="/..object/timetables/2003 fall/weekly" />
            </timetables>
            """, dedent("""
            <html>
            <head>
              <title>Timetables for Foo</title>
            </head>
            <body>
              <h1>Timetables for Foo</h1>
              <ul>
                <li><a href="http://localhost:7001/..object/timetables/\\
            2003 fall/weekly"
                    >2003 fall, weekly</a></li>
              </ul>
            </body>
            </html>
            """).replace("\\\n", ""))
        self.assert_(view3.timetabled is context)
        self.assertEquals(view3.key, ('2003 fall', 'weekly'))
        self.assert_(view3.context is tt, '%r is not %r' % (view3.context, tt))

        # traversing to nonexistent timetables is allowed
        request = RequestStub()
        view = view2._traverse('eewkly', request)
        self.assert_(view.context is None)
        self.assert_(view.timetabled is context)
        self.assertEquals(view.key, ('2003 fall', 'eewkly'))

    def test_TimetableTraverseView_ro(self):
        from schooltool.views.timetable import TimetableTraverseView
        from schooltool.views.timetable import TimetableReadView
        view1, view2, view3, context, tt = self.do_test(
            TimetableTraverseView, TimetableReadView,
            """
            <timetables xmlns:xlink="http://www.w3.org/1999/xlink">
              <timetable period="2003 fall" schema="weekly" xlink:type="simple"
                         xlink:href="/..object/timetables/2003 fall/weekly" />
            </timetables>
            """, dedent("""
            <html>
            <head>
              <title>Timetables for Foo</title>
            </head>
            <body>
              <h1>Timetables for Foo</h1>
              <ul>
                <li><a href="http://localhost:7001/..object/timetables/\\
            2003 fall/weekly"
                    >2003 fall, weekly</a></li>
              </ul>
            </body>
            </html>
            """).replace("\\\n", ""),
            kwargs={'readonly': True})
        self.assert_(view3.context is tt)

        request = RequestStub()
        self.assertRaises(KeyError, view2._traverse, 'eewkly', request)

    def test_CompositeTimetableTraverseView(self):
        from schooltool.views.timetable import CompositeTimetableTraverseView
        from schooltool.views.timetable import TimetableReadView
        view1, view2, view3, context, tt = self.do_test(
            CompositeTimetableTraverseView, TimetableReadView,
            """
            <timetables xmlns:xlink="http://www.w3.org/1999/xlink">
              <timetable period="2003 fall" schema="weekly"
                 xlink:href="/..object/composite-timetables/2003 fall/weekly"
                 xlink:type="simple" />
              <timetable period="2003 spring" schema="weekly"
                 xlink:href="/..object/composite-timetables/2003 spring/weekly"
                 xlink:type="simple" />
            </timetables>
            """, dedent("""
            <html>
            <head>
              <title>Composite timetables for Foo</title>
            </head>
            <body>
              <h1>Composite timetables for Foo</h1>
              <ul>
                <li><a href="http://localhost:7001/..object/\\
            composite-timetables/2003 fall/weekly"
                    >2003 fall, weekly</a></li>
                <li><a href="http://localhost:7001/..object/\\
            composite-timetables/2003 spring/weekly"
                    >2003 spring, weekly</a></li>
              </ul>
            </body>
            </html>
            """).replace("\\\n", ""))
        self.assertEqual(view3.context, tt)
        self.assert_(view3.context is not tt)

        request = RequestStub()
        self.assertRaises(KeyError, view2._traverse, 'eewkly', request)

    def test_SchoolTimetableTraverseView(self):
        from schooltool.views.timetable import SchoolTimetableTraverseView
        from schooltool.views.timetable import SchoolTimetableView
        view1, view2, view3, context, tt = (
            self.do_test(SchoolTimetableTraverseView, SchoolTimetableView,
                """
                <timetables xmlns:xlink="http://www.w3.org/1999/xlink">
                  <timetable period="2003 fall" schema="weekly"
                    xlink:href="/schooltt/2003 fall/weekly"
                    xlink:type="simple" />
                </timetables>
                """, """
                <html>
                <head>
                  <title>School timetables</title>
                </head>
                <body>
                  <h1>School timetables</h1>
                  <ul>
                    <li><a
                         href="http://localhost:7001/schooltt/2003 fall/weekly"
                        >2003 fall, weekly</a></li>
                  </ul>
                </body>
                </html>
                """,
                path='/')
            )
        self.assertEqual(view3.context, context)

        request = RequestStub()
        self.assertRaises(KeyError, view2._traverse, 'eewkly', request)
        self.assertRaises(KeyError, view1._traverse, '2033 faal', request)


class TestTimetableReadView(XMLCompareMixin, unittest.TestCase):

    empty_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
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

    empty_html_template = """
        <html>
        <head>
          <title>
            John Smith's %(tt_type)s timetable for 2003 fall, weekly
          </title>
          <style type="text/css">
            table { border-collapse: collapse; }
            td, th { border: 1px solid black; }
          </style>
        </head>
        <body>
          <h1>John Smith's %(tt_type)s timetable for 2003 fall, weekly</h1>
          <table border="1">
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
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
          <day id="Day 1">
            <period id="A">
              <activity title="Maths">
                <resource xlink:type="simple" xlink:href="/resources/room1"
                          xlink:title="Room 1"/>
              </activity>
            </period>
            <period id="B">
              <activity title="English" />
              <activity title="French">
              </activity>
            </period>
          </day>
          <day id="Day 2">
            <period id="C">
              <activity title="CompSci">
                <resource xlink:type="simple" xlink:href="/resources/lab1"
                          xlink:title="CS Lab 1"/>
                <resource xlink:type="simple" xlink:href="/resources/lab2"
                          xlink:title="CS Lab 2"/>
              </activity>
            </period>
            <period id="D">
            </period>
          </day>
        </timetable>
        """

    full_html_template = """
        <html>
        <head>
          <title>
            John Smith's %(tt_type)s timetable for 2003 fall, weekly
          </title>
          <style type="text/css">
            table { border-collapse: collapse; }
            td, th { border: 1px solid black; }
          </style>
        </head>
        <body>
          <h1>John Smith's %(tt_type)s timetable for 2003 fall, weekly</h1>
          <table border="1">
            <tr>
              <th colspan="2">Day 1</th>
              <th colspan="2">Day 2</th>
            </tr>
            <tr>
              <th>A</th>
              <td>Maths (Room 1)</td>
              <th>C</th>
              <td>CompSci (CS Lab 1, CS Lab 2)</td>
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

    empty_html = empty_html_template % {'tt_type': "complete"}
    full_html = full_html_template % {'tt_type': "complete"}

    def setUp(self):
        self.root = ServiceManagerStub()

    def createEmpty(self):
        from schooltool.timetable import Timetable, TimetableDay
        grandparent = TimetabledStub()
        grandparent.title = "John Smith"
        parent = TimetabledStub()  # in real life this is a TimetableDict
        parent.__parent__ = grandparent
        tt = Timetable(['Day 1', 'Day 2'])
        tt.__parent__ = parent
        tt['Day 1'] = TimetableDay(['A', 'B'])
        tt['Day 2'] = TimetableDay(['C', 'D'])
        return tt

    def createFull(self, owner=None):
        from schooltool.timetable import TimetableActivity
        tt = self.createEmpty()
        room1 = self.root.resources['room1']
        lab1 = self.root.resources['lab1']
        lab2 = self.root.resources['lab2']
        tt['Day 1'].add('A', TimetableActivity('Maths', owner, [room1]))
        tt['Day 1'].add('B', TimetableActivity('English', owner))
        tt['Day 1'].add('B', TimetableActivity('French', owner))
        tt['Day 2'].add('C', TimetableActivity('CompSci', owner, [lab1, lab2]))
        return tt

    def createView(self, context, key=('2003 fall', 'weekly')):
        from schooltool.views.timetable import TimetableReadView
        return TimetableReadView(context, key)

    def do_test_get(self, context, expected, ctype="text/xml", accept=()):
        request = RequestStub('...object/timetables/x/y')
        request.accept = accept
        view = self.createView(context)
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
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


class TestTimetableReadWriteView(QuietLibxml2Mixin, TestTimetableReadView):

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
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
          <day id="Day 1">
            <period id="A">
              <activity title="English"/>
            </period>
            <period id="B">
            </period>
          </day>
          <day id="Day 3">
          </day>
        </timetable>
        """

    unknown_period_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
          <day id="Day 1">
            <period id="A">
              <activity title="English"/>
            </period>
            <period id="X">
            </period>
          </day>
        </timetable>
        """

    nonexistent_resource_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
          <day id="Day 1">
            <period id="A">
              <activity title="English">
                <resource xlink:type="simple" xlink:href="/resources/moon"/>
              </activity>
            </period>
            <period id="X">
            </period>
          </day>
        </timetable>
        """

    empty_html = TestTimetableReadView.empty_html_template % {'tt_type': "own"}
    full_html = TestTimetableReadView.full_html_template % {'tt_type': "own"}

    def setUp(self):
        TestTimetableReadView.setUp(self)
        self.setUpLibxml2()
        self.root = ServiceManagerStub(self.createEmpty())

    def tearDown(self):
        self.tearDownLibxml2()

    def createTimetabled(self):
        from schooltool.timetable import TimetableSchemaService
        from schooltool.timetable import TimePeriodService
        timetabled = TimetabledStub()
        timetabled.__parent__ = self.root
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
        view.authorization = lambda ctx, rq: True
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_put(self):
        key = ('2003 fall', 'weekly')
        ttd = self.createTimetabled()
        room1 = self.root.resources['room1']
        lab1 = self.root.resources['lab1']
        lab2 = self.root.resources['lab2']

        ttd.timetables[key] = self.createEmpty()
        expected = self.createFull(ttd)
        self.do_test_put(ttd, key, self.full_xml, expected)
        self.assertEquals([(d, p, a.title) for d, p, a in
                                room1.timetables[key].itercontent()],
                          [('Day 1', 'A', 'Maths')])
        self.assertEquals([(d, p, a.title) for d, p, a in
                                lab1.timetables[key].itercontent()],
                          [('Day 2', 'C', 'CompSci')])
        self.assertEquals([(d, p, a.title) for d, p, a in
                                lab2.timetables[key].itercontent()],
                          [('Day 2', 'C', 'CompSci')])

        ttd.timetables[key] = self.createFull(ttd)
        expected = self.createEmpty()
        self.do_test_put(ttd, key, self.empty_xml, expected)
        self.assertEquals(list(room1.timetables[key].itercontent()), [])
        self.assertEquals(list(lab1.timetables[key].itercontent()), [])
        self.assertEquals(list(lab2.timetables[key].itercontent()), [])

    def do_test_put(self, timetabled, key, xml, expected):
        view = self.createView(timetabled=timetabled, key=key)
        view.authorization = lambda ctx, rq: True
        request = RequestStub(method="PUT", body=xml,
                              headers={'Content-Type': 'text/xml'})
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
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
        view.authorization = lambda ctx, rq: True
        request = RequestStub(method="PUT", body=self.full_xml,
                              headers={'Content-Type': 'text/xml'})
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assert_(key not in timetabled.timetables)

    def test_put_bad_period(self):
        key = ('2003 faal', 'weekly')
        timetabled = self.createTimetabled()
        view = self.createView(None, timetabled, key)
        view.authorization = lambda ctx, rq: True
        request = RequestStub(method="PUT", body=self.full_xml,
                              headers={'Content-Type': 'text/xml'})
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assert_(key not in timetabled.timetables)

    def do_test_error(self, xml=None, ctype='text/xml', message=None):
        if xml is None:
            xml = self.empty_xml
        context = self.createEmpty()
        view = self.createView(context)
        view.authorization = lambda ctx, rq: True
        request = RequestStub(method="PUT", body=xml,
                              headers={'Content-Type': ctype})
        result = view.render(request)
        if message is not None:
            self.assertEquals(result, message)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(context, self.createEmpty())

    def test_put_error_handling(self):
        self.do_test_error(ctype='text/plain',
                           message="Unsupported content type: text/plain")
        self.do_test_error(xml=self.illformed_xml,
                           message="Timetable not valid XML")
        self.do_test_error(xml=self.invalid_xml,
                           message="Timetable not valid according to schema")
        self.do_test_error(xml=self.unknown_day_xml,
                           message="Unknown day id: u'Day 3'")
        self.do_test_error(xml=self.unknown_period_xml,
                           message="Unknown period id: u'X'")
        self.do_test_error(xml=self.nonexistent_resource_xml,
                           message="Invalid path: /resources/moon")

    def test_delete(self):
        key = ('2003 fall', 'weekly')
        timetabled = self.createTimetabled()
        context = timetabled.timetables[key] = self.createEmpty()
        view = self.createView(context, timetabled, key)
        view.authorization = lambda ctx, rq: True
        request = RequestStub(method="DELETE")
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assert_(key not in timetabled.timetables)

    def test_delete_nonexistent(self):
        view = self.createView(None)
        view.authorization = lambda ctx, rq: True
        request = RequestStub(method="DELETE")
        result = view.render(request)
        self.assertEquals(request.code, 404)


class TestTimetableSchemaView(RegistriesSetupMixin, QuietLibxml2Mixin,
                              TestTimetableReadView):

    empty_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <model factory="SequentialDaysTimetableModel">
            <daytemplate>
              <used when="Friday Thursday"/>
              <period duration="60" id="A" tstart="08:00"/>
              <period duration="60" id="B" tstart="11:00"/>
              <period duration="60" id="C" tstart="08:00"/>
              <period duration="60" id="D" tstart="11:00"/>
            </daytemplate>
            <daytemplate>
              <used when="default"/>
              <period duration="60" id="A" tstart="09:00"/>
              <period duration="60" id="B" tstart="10:00"/>
              <period duration="60" id="C" tstart="09:00"/>
              <period duration="60" id="D" tstart="10:00"/>
            </daytemplate>
          </model>
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
          <model factory="SequentialDaysTimetableModel">
            <daytemplate id="Normal">
              <used when="default" />
              <period id="A" tstart="9:00" duration="60" />
              <period id="C" tstart="9:00" duration="60" />
              <period id="B" tstart="10:00" duration="60" />
              <period id="D" tstart="10:00" duration="60" />
            </daytemplate>
          </model>
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
          <model factory="SequentialDaysTimetableModel">
            <daytemplate id="Normal">
              <used when="default" />
              <period id="A" tstart="9:00" duration="60" />
              <period id="C" tstart="9:00" duration="60" />
              <period id="B" tstart="10:00" duration="60" />
              <period id="D" tstart="10:00" duration="60" />
            </daytemplate>
          </model>
          <day id="Day 1">
            <period id="A">
            </period>
            <period id="A">
            </period>
          </day>
        </timetable>
        """

    bad_time_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <model factory="SequentialDaysTimetableModel">
            <daytemplate id="Normal">
              <used when="default" />
              <period id="A" tstart="9:00:00" duration="60" />
            </daytemplate>
          </model>
          <day id="Day 1">
            <period id="A">
            </period>
            <period id="B">
            </period>
          </day>
        </timetable>
        """

    bad_model_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <model factory="Nonexistent">
            <daytemplate id="Normal">
              <used when="default" />
              <period id="A" tstart="9:00" duration="60" />
            </daytemplate>
          </model>
          <day id="Day 1">
            <period id="A">
            </period>
            <period id="B">
            </period>
          </day>
        </timetable>
        """

    bad_dur_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <model factory="SequentialDaysTimetableModel">
            <daytemplate id="Normal">
              <used when="default" />
              <period id="A" tstart="9:00" duration="1h" />
            </daytemplate>
          </model>
          <day id="Day 1">
            <period id="A">
            </period>
            <period id="B">
            </period>
          </day>
        </timetable>
        """

    bad_weekday_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <model factory="SequentialDaysTimetableModel">
            <daytemplate id="Normal">
              <used when="froday" />
              <period id="A" tstart="9:00" duration="1h" />
            </daytemplate>
          </model>
          <day id="Day 1">
            <period id="A">
            </period>
            <period id="B">
            </period>
          </day>
        </timetable>
        """

    empty_html = """
        <html>
        <head>
          <title>Timetable schema: weekly</title>
          <style type="text/css">
            table { border-collapse: collapse; }
            td, th { border: 1px solid black; }
          </style>
        </head>
        <body>
          <h1>Timetable schema: weekly</h1>
          <table border="1">
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

    schema_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <model factory="SequentialDaysTimetableModel">
            <daytemplate>
              <used when="default" />
              <period id="A" tstart="9:00" duration="60" />
              <period id="C" tstart="9:00" duration="60" />
              <period id="B" tstart="10:00" duration="60" />
              <period id="D" tstart="10:00" duration="60" />
            </daytemplate>
            <daytemplate>
              <used when="Friday Thursday" />
              <period id="A" tstart="8:00" duration="60" />
              <period id="C" tstart="8:00" duration="60" />
              <period id="B" tstart="11:00" duration="60" />
              <period id="D" tstart="11:00" duration="60" />
            </daytemplate>
          </model>
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

    def setUp(self):
        TestTimetableReadView.setUp(self)
        self.setUpRegistries()
        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownLibxml2()
        self.tearDownRegistries()

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
        view.authorization = lambda ctx, rq: True
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_delete(self):
        from schooltool.timetable import TimetableSchemaService
        key = 'weekly'
        service = TimetableSchemaService()
        context = service[key] = self.createEmpty()
        view = self.createView(context, service, key)
        view.authorization = lambda ctx, rq: True
        request = RequestStub(method="DELETE")
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertRaises(KeyError, lambda: service[key])

    def test_delete_nonexistent(self):
        view = self.createView(None)
        view.authorization = lambda ctx, rq: True
        request = RequestStub(method="DELETE")
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def createEmpty(self):
        from schooltool.timetable import SequentialDaysTimetableModel
        from schooltool.timetable import SchooldayPeriod, SchooldayTemplate
        from datetime import time, timedelta
        tt = TestTimetableReadView.createEmpty(self)
        day_template1 = SchooldayTemplate()
        hour = timedelta(minutes=60)
        day_template1.add(SchooldayPeriod('A', time(9, 0), hour))
        day_template1.add(SchooldayPeriod('B', time(10, 0), hour))
        day_template1.add(SchooldayPeriod('C', time(9, 0), hour))
        day_template1.add(SchooldayPeriod('D', time(10, 0), hour))

        day_template2 = SchooldayTemplate()
        hour = timedelta(minutes=60)
        day_template2.add(SchooldayPeriod('A', time(8, 0), hour))
        day_template2.add(SchooldayPeriod('B', time(11, 0), hour))
        day_template2.add(SchooldayPeriod('C', time(8, 0), hour))
        day_template2.add(SchooldayPeriod('D', time(11, 0), hour))
        tm = SequentialDaysTimetableModel(['Day 1', 'Day 2'],
                                          {None: day_template1,
                                           3: day_template2,
                                           4: day_template2})
        tt.model = tm
        return tt

    def test_put(self):
        from schooltool.timetable import TimetableSchemaService
        from schooltool.timetable import setUp
        setUp()
        key = 'weekly'
        service = TimetableSchemaService()
        view = self.createView(None, service, key)
        view.authorization = lambda ctx, rq: True
        request = RequestStub(method="PUT", body=self.schema_xml,
                              headers={'Content-Type': 'text/xml'})
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(service[key], self.createEmpty())

    def test_roundtrip(self):
        from schooltool.timetable import TimetableSchemaService
        from schooltool.timetable import setUp
        setUp()
        key = 'weekly'
        service = TimetableSchemaService()
        view = self.createView(None, service, key)
        view.authorization = lambda ctx, rq: True
        request = RequestStub(method="PUT", body=self.schema_xml,
                              headers={'Content-Type': 'text/xml'})
        view.render(request)

        view2 = self.createView(service[key], service, key)
        view2.authorization = lambda ctx, rq: True

        request = RequestStub()
        result = view2.render(request)
        request = RequestStub(method="PUT", body=result,
                              headers={'Content-Type': 'text/xml'})
        self.assertEquals(request.code, 200)

    def do_test_error(self, xml=None, ctype='text/xml'):
        from schooltool.timetable import TimetableSchemaService
        if xml is None:
            xml = self.empty_xml
        key = 'weekly'
        service = TimetableSchemaService()
        view = self.createView(None, service, key)
        view.authorization = lambda ctx, rq: True
        request = RequestStub(method="PUT", body=xml,
                              headers={'Content-Type': ctype})
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertRaises(KeyError, lambda: service[key])

    def test_put_error_handling(self):
        self.do_test_error(ctype='text/plain')
        self.do_test_error(xml=self.illformed_xml)
        self.do_test_error(xml=self.invalid_xml)
        self.do_test_error(xml=self.full_xml)
        self.do_test_error(xml=self.duplicate_day_xml)
        self.do_test_error(xml=self.duplicate_period_xml)
        self.do_test_error(xml=self.bad_dur_xml)
        self.do_test_error(xml=self.bad_time_xml)
        self.do_test_error(xml=self.bad_model_xml)
        self.do_test_error(xml=self.bad_weekday_xml)


class TestTimetableSchemaServiceView(XMLCompareMixin, unittest.TestCase):

    def test_get(self):
        from schooltool.timetable import TimetableSchemaService, Timetable
        from schooltool.views.timetable import TimetableSchemaServiceView
        context = TimetableSchemaService()
        setPath(context, '/ttservice')
        view = TimetableSchemaServiceView(context)
        view.authorization = lambda ctx, rq: True
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <timetableSchemas xmlns:xlink="http://www.w3.org/1999/xlink">
            </timetableSchemas>
            """)

        context['weekly'] = Timetable(())
        context['4day'] = Timetable(())
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
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
        tt = context['weekly'] = Timetable(())
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
                              QuietLibxml2Mixin, unittest.TestCase):

    example_xml = """
        <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2"
                  xmlns:xlink="http://www.w3.org/1999/xlink">
          <teacher xlink:type="simple" xlink:title="Marius"
                   xlink:href="/persons/p2">
            <day id="A">
              <period id="Blue">
              </period>
              <period id="Green">
              </period>
            </day>
            <day id="B">
              <period id="Red">
                <activity group="/groups/sg3" title="Email">
                  <resource xlink:type="simple" xlink:href="/resources/room1"
                            xlink:title="Room 1"/>
                </activity>
              </period>
              <period id="Yellow">
              </period>
            </day>
          </teacher>
          <teacher xlink:type="simple" xlink:title="Albert"
                   xlink:href="/persons/p1">
            <day id="A">
              <period id="Blue">
                <activity group="/groups/sg2" title="Slashdot">
                </activity>
              </period>
              <period id="Green">
                <activity group="/groups/sg1" title="Slacking">
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

    def setUp(self):
        from schooltool.views.timetable import SchoolTimetableView
        from schooltool.model import Group, Person, Resource
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool.teaching import TeacherFacet, Teaching
        from schooltool.component import FacetManager
        from schooltool.component import getTimetableSchemaService
        from schooltool import membership
        from schooltool import relationship
        from schooltool.timetable import Timetable, TimetableDay
        self.setUpLibxml2()
        self.setUpRegistries()
        membership.setUp()
        relationship.setUp()
        app = self.app = Application()

        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        app['resources'] = ApplicationObjectContainer(Resource)
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

        self.room1 = app['resources'].new('room1', title="Room 1")

        self.key = ('2003-spring', '2day')
        self.view = SchoolTimetableView(app, key=self.key)
        self.view.authorization = lambda ctx, rq: True

        service = getTimetableSchemaService(self.app)

        tt = Timetable(("A", "B"))
        tt["A"] = TimetableDay(("Green", "Blue"))
        tt["B"] = TimetableDay(("Red", "Yellow"))
        service[self.key[1]] = tt

    def tearDown(self):
        self.tearDownRegistries()
        self.tearDownLibxml2()

    def testEmpty(self):
        request = RequestStub()
        result = self.view.render(request)
        expected = """
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2"
                      xmlns:xlink="http://www.w3.org/1999/xlink">
              <teacher xlink:type="simple" xlink:title="Marius"
                       xlink:href="/persons/p2">
                <day id="A">
                  <period id="Blue">
                  </period>
                  <period id="Green">
                  </period>
                </day>
                <day id="B">
                  <period id="Red">
                  </period>
                  <period id="Yellow">
                  </period>
                </day>
              </teacher>
              <teacher xlink:type="simple" xlink:title="Albert"
                       xlink:href="/persons/p1">
                <day id="A">
                  <period id="Blue">
                  </period>
                  <period id="Green">
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
        self.assert_(validate_against_schema(self.view.schema, result),
                     "Doesn't validate:\n" + result)

    def setUpTimetables(self):
        from schooltool.component import getTimetableSchemaService
        from schooltool.timetable import TimetableActivity

        tt = getTimetableSchemaService(self.app)[self.key[1]]
        tt["A"].add("Green", TimetableActivity("Slacking", self.sg1))
        self.sg1.timetables[self.key] = tt

        tt = tt.cloneEmpty()
        tt["A"].add("Blue", TimetableActivity("Slashdot", self.sg2))
        self.sg2.timetables[self.key] = tt

        email_activity = TimetableActivity("Email", self.sg3, [self.room1])
        tt = tt.cloneEmpty()
        tt["B"].add("Red", email_activity)
        self.sg3.timetables[self.key] = tt

        tt = tt.cloneEmpty()
        tt["B"].add("Red", email_activity)
        self.room1.timetables[self.key] = tt

    def testNonempty(self):
        from schooltool.component import getTimetableSchemaService
        from schooltool.timetable import TimetableActivity
        self.setUpTimetables()
        request = RequestStub()
        result = self.view.render(request)
        expected = self.example_xml
        self.assertEqualsXML(result, expected, recursively_sort=['schooltt'])
        self.assert_(validate_against_schema(self.view.schema, result),
                     "Doesn't validate:\n" + result)

        # Teacher's personal timetables should not be included here
        tt = getTimetableSchemaService(self.app)[self.key[1]]
        tt["B"].add("Yellow", TimetableActivity("Personal", self.teacher1))
        self.teacher1.timetables[self.key] = tt
        result = self.view.render(request)
        self.assertEqualsXML(result, expected, recursively_sort=['schooltt'])

    def test_PUT(self):
        from schooltool.timetable import TimetableActivity

        xml = self.example_xml
        request = RequestStub(method="PUT", body=xml,
                              headers={'Content-Type': 'text/xml'})
        result = self.view.render(request)

        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")

        self.assertEquals(self.sg4.timetables[self.key],
                          self.sg4.timetables[self.key].cloneEmpty())

        tt1 = self.sg1.timetables[self.key]
        self.assertEquals(Set(tt1["A"]["Green"]),
                          Set([TimetableActivity("Slacking", self.sg1)]))
        self.assertEquals(Set(tt1["A"]["Blue"]), Set())
        self.assertEquals(Set(tt1["B"]["Red"]), Set())
        self.assertEquals(Set(tt1["B"]["Yellow"]), Set())

        tt2 = self.sg2.timetables[self.key]
        self.assertEquals(Set(tt2["A"]["Blue"]),
                          Set([TimetableActivity("Slashdot", self.sg2)]))
        self.assertEquals(Set(tt2["A"]["Green"]), Set())
        self.assertEquals(Set(tt2["B"]["Red"]), Set())
        self.assertEquals(Set(tt2["B"]["Yellow"]), Set())

        tt3 = self.sg3.timetables[self.key]
        self.assertEquals(Set(tt3["A"]["Blue"]), Set())
        self.assertEquals(Set(tt3["A"]["Green"]), Set())
        self.assertEquals(Set(tt3["B"]["Red"]),
                          Set([TimetableActivity("Email", self.sg3,
                                                 [self.room1])]))
        self.assertEquals(Set(tt3["B"]["Yellow"]), Set())

        email_activity = list(tt3["B"]["Red"])[0]
        self.assertEquals(list(self.room1.timetables[self.key].itercontent()),
                          [('B', 'Red', email_activity)])

    def test_PUT_empty(self):
        xml = """
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2"
                      xmlns:xlink="http://www.w3.org/1999/xlink">
              <teacher xlink:type="simple" xlink:href="/persons/p2">
              </teacher>
              <teacher xlink:type="simple" xlink:href="/persons/p1">
              </teacher>
            </schooltt>
            """
        self.setUpTimetables()
        request = RequestStub(method="PUT", body=xml,
                              headers={'Content-Type': 'text/xml'})
        result = self.view.render(request)
        self.assertEquals(result, "OK")
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(self.sg1.timetables[self.key],
                          self.sg1.timetables[self.key].cloneEmpty())
        self.assertEquals(self.sg2.timetables[self.key],
                          self.sg2.timetables[self.key].cloneEmpty())
        self.assertEquals(self.sg3.timetables[self.key],
                          self.sg3.timetables[self.key].cloneEmpty())
        self.assertEquals(self.sg4.timetables[self.key],
                          self.sg4.timetables[self.key].cloneEmpty())

        self.assertEquals(list(self.room1.timetables[self.key].itercontent()),
                          [])

    def test_PUT_badxml(self):
        nonxml = "<schooltt parse error>"
        badxml = """
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2">
              <coach xlink:type="simple" xlink:href="/persons/p2">
              </coach>
            </schooltt>
            """
        bad_path_xml = """
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2">
              <teacher xlink:type="simple" xlink:href="/persons/p3">
              </teacher>
              <teacher xlink:type="simple" xlink:href="/persons/p1">
              </teacher>
            </schooltt>
            """
        bad_day_xml = """
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2">
              <teacher xlink:type="simple" xlink:href="/persons/p1">
                <day id="bad"/>
              </teacher>
            </schooltt>
            """
        bad_period_xml = """
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2">
              <teacher xlink:type="simple" xlink:href="/persons/p1">
                <day id="A">
                  <period id="bad"/>
                </day>
              </teacher>
            </schooltt>
            """
        bad_group_xml = """
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2">
              <teacher xlink:type="simple" xlink:href="/persons/p1">
                <day id="A">
                  <period id="Blue">
                    <activity group="/persons/p1">Haxoring</activity>
                  </period>
                </day>
              </teacher>
            </schooltt>
            """
        bad_teacher_xml = """
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2">
              <teacher xlink:type="simple" xlink:href="/persons/p1">
                <day id="A">
                  <period id="Blue">
                    <activity group="/groups/sg3">Instead of p2</activity>
                  </period>
                </day>
              </teacher>
              <teacher xlink:type="simple" xlink:href="/persons/p2" />
            </schooltt>
            """
        for body in (nonxml, badxml, bad_path_xml, bad_day_xml, bad_period_xml,
                     bad_group_xml, bad_teacher_xml):
            request = RequestStub(method="PUT", body=body,
                                  headers={'Content-Type': 'text/xml'})
            result = self.view.render(request)
            self.assertEquals(request.code, 400)


class TestTimePeriodServiceView(XMLCompareMixin, unittest.TestCase):

    def test_get(self):
        from schooltool.timetable import TimePeriodService
        from schooltool.views.timetable import TimePeriodServiceView
        context = TimePeriodService()
        setPath(context, '/time-periods')
        view = TimePeriodServiceView(context)
        view.authorization = lambda ctx, rq: True
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <timePeriods xmlns:xlink="http://www.w3.org/1999/xlink">
            </timePeriods>
            """)

        context['2003 fall'] = SchooldayModelStub()
        context['2004 spring'] = SchooldayModelStub()
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
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
        context['2003 fall'] = SchooldayModelStub()
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
        view.authorization = lambda ctx, rq: True
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

        sm = service[key] = SchooldayModelStub()
        setPath(sm, '/time-periods/%s' % key)
        view = TimePeriodCreatorView(service, key)
        view.authorization = lambda ctx, rq: True
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/calendar; charset=UTF-8")

    def test_put(self):
        from schooltool.timetable import TimePeriodService
        from schooltool.views.timetable import TimePeriodCreatorView
        from schooltool.component import getPath
        service = TimePeriodService()
        setPath(service, '/time-periods')
        key = '2003 fall'
        view = TimePeriodCreatorView(service, key)
        view.authorization = lambda ctx, rq: True
        body = dedent("""
            BEGIN:VCALENDAR
            BEGIN:VEVENT
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20040901
            DTEND;VALUE=DATE:20041001
            END:VEVENT
            END:VCALENDAR
        """)
        request = RequestStub(method='PUT', body=body,
                              headers={"Content-Type": "text/calendar"})
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assert_(key in service)
        self.assertEquals(service[key].first, datetime.date(2004, 9, 1))
        self.assertEquals(getPath(service[key]), '/time-periods/%s' % key)

    def test_delete(self):
        from schooltool.timetable import TimePeriodService
        from schooltool.views.timetable import TimePeriodCreatorView
        service = TimePeriodService()
        key = '2003 fall'
        service[key] = SchooldayModelStub()
        view = TimePeriodCreatorView(service, key)
        view.authorization = lambda ctx, rq: True
        request = RequestStub(method='DELETE')
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assert_(key not in service)

    def test_delete_nonexistent(self):
        from schooltool.timetable import TimePeriodService
        from schooltool.views.timetable import TimePeriodCreatorView
        service = TimePeriodService()
        key = '2003 fall'
        view = TimePeriodCreatorView(service, key)
        view.authorization = lambda ctx, rq: True
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
    suite.addTest(unittest.makeSuite(TestTimetableContentNegotiation))
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
