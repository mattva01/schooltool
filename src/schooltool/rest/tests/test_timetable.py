#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Unit tests for schooltool.rest.timetable.

$Id$
"""

import unittest
import datetime
from StringIO import StringIO

from zope.app.component.hooks import setSite
from zope.app.component.site import LocalSiteManager
from zope.interface import Interface
from zope.component import adapts
from zope.app.traversing import namespace
from zope.app.testing import ztapi, setup
from zope.interface import implements, directlyProvides
from zope.app.filerepresentation.interfaces import IFileFactory, IWriteFile
from zope.interface.verify import verifyObject
from zope.app.location.interfaces import ILocation
from zope.app.traversing.interfaces import ITraversable
from zope.app.component.testing import PlacefulSetup
from zope.testing.doctest import DocTestSuite, ELLIPSIS
from zope.publisher.browser import TestRequest
from zope.app.traversing.interfaces import IContainmentRoot
from zope.publisher.interfaces.http import IHTTPRequest
from zope.app.annotation.interfaces import IAnnotatable
from zope.interface import directlyProvidedBy


from schoolbell.app.rest.tests.utils import QuietLibxml2Mixin
from schoolbell.app.rest.tests.utils import XMLCompareMixin
from schoolbell.app.rest.errors import RestError


class TimetableTestMixin(PlacefulSetup, XMLCompareMixin):

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

    full_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
          <day id="Day 1">
            <period id="A">
              <activity title="Maths">
                <resource xlink:type="simple" xlink:href="http://127.0.0.1/resources/room1"
                          xlink:title="Room1"/>
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
                <resource xlink:type="simple" xlink:href="http://127.0.0.1/resources/lab1"
                          xlink:title="Lab1"/>
                <resource xlink:type="simple" xlink:href="http://127.0.0.1/resources/lab2"
                          xlink:title="Lab2"/>
              </activity>
            </period>
            <period id="D">
            </period>
          </day>
        </timetable>
        """

    def setUp(self):
        from schooltool.rest.interfaces import ITimetableFileFactory
        from schooltool.rest.timetable import TimetableFileFactory
        from schooltool.interfaces import ITimetableDict
        from schooltool.app import SchoolToolApplication
        from schooltool.app import Person
        from schooltool.app import Resource
        PlacefulSetup.setUp(self)
        self.app = SchoolToolApplication()
        self.app.setSiteManager(LocalSiteManager(self.app))
        setSite(self.app)
        directlyProvides(self.app, IContainmentRoot)
        self.app["persons"]["john"] = self.person = Person("john", "John Smith")
        self.app["resources"]['room1'] = Resource("Room1")
        self.app["resources"]['lab1'] = Resource("Lab1")
        self.app["resources"]['lab2'] = Resource("Lab2")
        self.schema = self.app["ttschemas"]["schema1"] = self.createSchema()
        self.term = self.app["terms"]["2003 fall"] = self.createTerm()
        self.term2 = self.app["terms"]["2004 fall"] = self.createTerm()

        ztapi.provideAdapter((ITimetableDict, IHTTPRequest),
                              ITimetableFileFactory,
                              TimetableFileFactory)

    def createTerm(self):
        from schooltool.timetable import Term
        return Term("2003 fall",
                    datetime.date(2003, 9, 1),
                    datetime.date(2003, 9, 30))

    def createSchema(self):
        from schooltool.timetable import TimetableSchema, TimetableSchemaDay
        tt = TimetableSchema(['Day 1', 'Day 2'])
        tt['Day 1'] = TimetableSchemaDay(['A', 'B'])
        tt['Day 2'] = TimetableSchemaDay(['C', 'D'])
        return tt

    def createEmpty(self):
        return self.schema.createTimetable()

    def createFull(self, owner=None):
        from schooltool.timetable import TimetableActivity
        tt = self.createEmpty()
        room1 = self.app["resources"]['room1']
        lab1 = self.app["resources"]['lab1']
        lab2 = self.app["resources"]['lab2']
        tt['Day 1'].add('A', TimetableActivity('Maths', owner, [room1]))
        tt['Day 1'].add('B', TimetableActivity('English', owner))
        tt['Day 1'].add('B', TimetableActivity('French', owner))
        tt['Day 2'].add('C', TimetableActivity('CompSci', owner, [lab1, lab2]))
        return tt


class TestTimetableReadView(TimetableTestMixin, unittest.TestCase):

    def createView(self, context, request):
        from schooltool.rest.timetable import TimetableReadView
        return TimetableReadView(context, request)

    def do_test_get(self, context, expected, ctype="text/xml"):
        request = TestRequest()
        view = self.createView(context, request)
        result = view.GET()
        self.assertEquals(request.response.getHeader('content-type'),
                          "%s; charset=UTF-8" % ctype)
        self.assertEqualsXML(result, expected, recursively_sort=['timetable'])

    def test_get(self):
        self.do_test_get(self.createEmpty(), self.empty_xml)
        self.do_test_get(self.createFull(), self.full_xml)


class TimetableSchemaMixin(QuietLibxml2Mixin):

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
        from schooltool.app import SchoolToolApplication
        from schooltool.interfaces import ITimetableSchemaContainer
        from schooltool.rest.timetable import TimetableSchemaFileFactory
        from schooltool.timetable import SequentialDaysTimetableModel
        from schooltool.interfaces import ITimetableModelFactory

        self.app = SchoolToolApplication()
        self.schemaContainer = self.app["ttschemas"]

        setup.placelessSetUp()
        setup.setUpTraversal()

        ztapi.provideAdapter(ITimetableSchemaContainer, IFileFactory,
                             TimetableSchemaFileFactory)

        ztapi.provideUtility(ITimetableModelFactory,
                             SequentialDaysTimetableModel,
                             "SequentialDaysTimetableModel")

        ztapi.provideView(Interface, Interface, ITraversable, 'view',
                          namespace.view)

        directlyProvides(self.schemaContainer, IContainmentRoot)

        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownLibxml2()
        setup.placelessTearDown()

    def createEmptySchema(self):
        from schooltool.timetable import TimetableSchema, TimetableSchemaDay

        timetable = TimetableSchema(['Day 1', 'Day 2'])
        timetable['Day 1'] = TimetableSchemaDay(['A', 'B'])
        timetable['Day 2'] = TimetableSchemaDay(['C', 'D'])
        return timetable

    def createExtendedSchema(self):
        from schooltool.timetable import SequentialDaysTimetableModel
        from schooltool.timetable import SchooldayPeriod, SchooldayTemplate
        from datetime import time, timedelta

        tt = self.createEmptySchema()

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


class TestTimetableSchemaView(TimetableSchemaMixin, XMLCompareMixin,
                              unittest.TestCase):

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

    def test_get(self):
        from schooltool.rest.timetable import TimetableSchemaView
        request = TestRequest()
        view = TimetableSchemaView(self.createExtendedSchema(), request)

        result = view.GET()
        self.assertEquals(request.response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, self.empty_xml,
                             recursively_sort=['timetable'])


class TestTimetableSchemaFileFactory(TimetableSchemaMixin, unittest.TestCase):

    def test(self):
        from schooltool.rest.timetable import TimetableSchemaFileFactory
        from schooltool.rest.interfaces import ITimetableFileFactory
        verifyObject(IFileFactory,
                     TimetableSchemaFileFactory(self.schemaContainer))

    def test_call(self):
        factory = IFileFactory(self.schemaContainer)
        self.assertRaises(RestError, factory, "two_day", "text/plain",
                          self.schema_xml)

    def test_parseXML(self):
        factory = IFileFactory(self.schemaContainer)
        schema = factory("two_day", "text/xml", self.schema_xml)
        self.assertEquals(schema, self.createExtendedSchema())

    def test_invalid_name(self):
        from schoolbell.app.rest.errors import RestError
        self.assertRaises(RestError, IFileFactory(self.schemaContainer),
                          "foo.bar", "text/xml", self.schema_xml)


class TestTimetableSchemaFile(TimetableSchemaMixin, unittest.TestCase):

    def setUp(self):
        TimetableSchemaMixin.setUp(self)
        self.schemaContainer["two_day"] = self.createEmptySchema()

    def test(self):
        from schooltool.rest.timetable import TimetableSchemaFile
        verifyObject(IWriteFile,
                     TimetableSchemaFile(self.schemaContainer["two_day"]))

    def test_write(self):
        from schooltool.rest.timetable import TimetableSchemaFile
        schemaFile = TimetableSchemaFile(self.schemaContainer["two_day"])
        schemaFile.write(self.schema_xml)
        self.assertEquals(self.schemaContainer["two_day"],
                          self.createExtendedSchema())


class TestTimetableFileFactory(TimetableTestMixin, unittest.TestCase):

    namespaces = {'tt': 'http://schooltool.org/ns/timetable/0.1',
                  'xlink': 'http://www.w3.org/1999/xlink'}

    def test(self):
        from schooltool.rest.interfaces import ITimetableFileFactory
        from schooltool.rest.timetable import TimetableFileFactory
        verifyObject(ITimetableFileFactory,
                     TimetableFileFactory(self.person.timetables,
                                          TestRequest()))

    def test_call(self):
        from schooltool.rest.timetable import TimetableFileFactory

        factory = TimetableFileFactory(self.person.timetables,
                                       TestRequest())
        timetable = factory("2003 fall.schema1", "text/xml", self.full_xml)
        self.assertEquals(timetable, self.createFull(self.person))

        timetable = factory("2003 fall.schema1", "text/xml", self.empty_xml)
        self.assertEquals(timetable, self.createEmpty())


class TestTimetablePUT(TimetableTestMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.interfaces import ITimetableDict
        from schooltool.rest.timetable import TimetableFileFactory

        TimetableTestMixin.setUp(self)
        self.timetable =  self.createEmpty()
        self.person.timetables["2003 fall.schema1"] = self.timetable

    def test_put(self):
        from schooltool.rest.timetable import TimetablePUT
        request = TestRequest(StringIO(self.full_xml))
        view = TimetablePUT(self.timetable, request)
        view.PUT()
        self.assertEquals(self.person.timetables["2003 fall.schema1"],
                          self.createFull(self.person))


def doctest_TimetableDictPublishTraverse():
    """Unit tests for TimetableDictPublishTraverse

    Some setup is needed:

        >>> setup.placelessSetUp()

        >>> from zope.app.component.hooks import setSite
        >>> from zope.app.component.site import LocalSiteManager
        >>> from schooltool.app import SchoolToolApplication
        >>> app = SchoolToolApplication()
        >>> app.setSiteManager(LocalSiteManager(app))
        >>> setSite(app)

        >>> from datetime import date
        >>> from schooltool.timetable import Term
        >>> from schooltool.timetable import TimetableSchema
        >>> app['terms']['2005-fall'] = Term('2005 Fall',
        ...         date(2005, 9, 1), date(2005, 12, 31))
        >>> app['terms']['2006-spring'] = Term('2006 Spring',
        ...         date(2006, 2, 1), date(2006, 6, 30))
        >>> app['ttschemas']['default'] = TimetableSchema([])

    TimetableDictPublishTraverse adapts (ITimetableDict, IHTTPRequest)
    pair

        >>> from schooltool.timetable import TimetableDict
        >>> from schooltool.rest.timetable import TimetableDictPublishTraverse
        >>> context = TimetableDict()
        >>> request = TestRequest()
        >>> pt = TimetableDictPublishTraverse(context, request)

    There are three cases.

    1. Existing timetable

        >>> from schooltool.timetable import Timetable
        >>> context['2005-fall.default'] = tt = Timetable([])
        >>> obj = pt.publishTraverse(request, '2005-fall.default')
        >>> obj
        <Timetable: ...>
        >>> obj is tt
        True

    2. Nonexisting timetable

        >>> obj = pt.publishTraverse(request, '2006-spring.default')
        >>> obj
        <...NullTimetable object at ...>
        >>> obj.container is context
        True
        >>> obj.name
        '2006-spring.default'

    3. Undefined term and/or schema

        >>> pt.publishTraverse(request, '2006-sprig.default')
        Traceback (most recent call last):
          ...
        NotFound: Object: <...TimetableDict...>, name: '2006-sprig.default'

        >>> pt.publishTraverse(request, '2006-spring.insane')
        Traceback (most recent call last):
          ...
        NotFound: Object: <...TimetableDict...>, name: '2006-spring.insane'

        >>> pt.publishTraverse(request, 'too.many.dots')
        Traceback (most recent call last):
          ...
        NotFound: Object: <...TimetableDict...>, name: 'too.many.dots'

        >>> pt.publishTraverse(request, 'no dots')
        Traceback (most recent call last):
          ...
        NotFound: Object: <...TimetableDict...>, name: 'no dots'

    Cleanup:

        >>> setup.placelessTearDown()

    """


def doctest_NullTimetablePUT():
    """Unit tests for NullTimetablePUT

    Setup: there should be an adapter from ITimetableDict to
    ITimetableFileFactory.

        >>> setup.placelessSetUp()
        >>> from schooltool.interfaces import ITimetableDict
        >>> from schooltool.rest.interfaces import ITimetableFileFactory
        >>> from schooltool.timetable import Timetable
        >>> from zope.publisher.interfaces.http import IHTTPRequest
        >>> class TimetableFileFactoryStub(object):
        ...     adapts(ITimetableDict)
        ...     implements(ITimetableFileFactory)
        ...     def __init__(self, context, request):
        ...         self.context = context
        ...         self.request = request
        ...     def __call__(self, name, ctype, data):
        ...         print "*** Creating a timetable called %s" % name
        ...         print "    from a %s entity containing %s" % (ctype, data)
        ...         return Timetable([])
        >>> ztapi.provideAdapter((ITimetableDict, IHTTPRequest),
        ...                      ITimetableFileFactory,
        ...                      TimetableFileFactoryStub)

    Also we want to see what events are sent out

        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> def handler(event):
        ...     print "*** Event: %r" % event
        >>> zope.event.subscribers.append(handler)

    NullTimetablePUT is a view on NullTimetable, which in turn knows
    where the new timetable is to be placed, and how it should be
    named.

        >>> from StringIO import StringIO
        >>> from schooltool.rest.timetable import NullTimetablePUT
        >>> from schooltool.rest.timetable import NullTimetable
        >>> from schooltool.timetable import TimetableDict
        >>> container = TimetableDict()
        >>> name = '2005-fall.default'
        >>> context = NullTimetable(container, name)
        >>> request = TestRequest(StringIO('<timetable data>'),
        ...                       environ={'CONTENT_TYPE': 'text/xml'})
        >>> view = NullTimetablePUT(context, request)

        >>> view.PUT()
        *** Creating a timetable called 2005-fall.default
            from a text/xml entity containing <timetable data>
        *** Event: <...ObjectCreatedEvent...>
        ''
        >>> request.response.getStatus()
        201

        >>> container[name]
        <Timetable: ...>

    As per the HTTP spec, NullTimetablePUT barfs if the request contains
    unrecognized Content-* headers.

        >>> request = TestRequest(StringIO('<timetable data>'),
        ...                       environ={'CONTENT_TYPE': 'text/xml',
        ...                                'HTTP_CONTENT_RANGE': 'blah'})
        >>> view = NullTimetablePUT(context, request)
        >>> view.PUT()
        ''
        >>> request.response.getStatus()
        501

    Cleanup:

        >>> zope.event.subscribers[:] = old_subscribers
        >>> setup.placelessTearDown()

    """


class TestTimetableDictView(TimetableTestMixin, unittest.TestCase):

    def createView(self, context, request):
        from schooltool.rest.timetable import TimetableDictView
        return TimetableDictView(context, request)

    def setUp(self):
        TimetableTestMixin.setUp(self)
        self.tt = self.person.timetables["2003 fall.schema1"] = self.createEmpty()

    def test_getTimetables(self):
        view = self.createView(self.person.timetables, TestRequest())
        timetables = view.getTimetables()
        self.assertEquals(len(timetables), 1)
        self.assert_(timetables[0] is self.tt)

    def test_timetables(self):
        view = self.createView(self.person.timetables, TestRequest())
        self.assertEquals(view.timetables, [{
            'url': "http://127.0.0.1/persons/john/timetables/2003%20fall.schema1",
            'term': u'2003 fall',
            'schema': u'schema1'}])

    def test_get(self):
        view = self.createView(self.person.timetables, TestRequest())
        self.assertEqualsXML(
            view.GET(),
            """<timetables xmlns:xlink="http://www.w3.org/1999/xlink">
                 <timetable xlink:type="simple" term="2003 fall"
                            xlink:href="http://127.0.0.1/persons/john/timetables/2003%20fall.schema1"
                            schema="schema1"/>
               </timetables>""")


class TestCompositeTimetabledView(TimetableTestMixin, unittest.TestCase):

    def createView(self, context, request):
        from schooltool.rest.timetable import CompositeTimetabledView
        return CompositeTimetabledView(context, request)

    def setUp(self):
        TimetableTestMixin.setUp(self)
        self.tt = self.person.timetables["2003 fall.schema1"] = self.createEmpty()


    def test_getTimetables(self):
        view = self.createView(self.person, TestRequest())
        timetables = view.getTimetables()
        self.assertEquals(len(timetables), 1)


    def test_timetables(self):
        view = self.createView(self.person, TestRequest())
        self.assertEquals(view.timetables, [{
            'url': "http://127.0.0.1/persons/john/composite-timetables/2003%20fall.schema1",
            'term': u'2003 fall',
            'schema': u'schema1'}])

    def test_get(self):
        view = self.createView(self.person, TestRequest())
        self.assertEqualsXML(
            view.GET(),
            """<timetables xmlns:xlink="http://www.w3.org/1999/xlink">
                 <timetable xlink:type="simple" term="2003 fall"
                            xlink:href="http://127.0.0.1/persons/john/composite-timetables/2003%20fall.schema1"
                            schema="schema1"/>
               </timetables>""")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.rest.timetable',
                               optionflags=ELLIPSIS))
    suite.addTest(DocTestSuite(optionflags=ELLIPSIS))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaFileFactory))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaFile))
    suite.addTest(unittest.makeSuite(TestTimetablePUT))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaView))
    suite.addTest(unittest.makeSuite(TestTimetableReadView))
    suite.addTest(unittest.makeSuite(TestTimetableFileFactory))
    suite.addTest(unittest.makeSuite(TestTimetableDictView))
    suite.addTest(unittest.makeSuite(TestCompositeTimetabledView))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
