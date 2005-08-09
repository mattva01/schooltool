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
Unit tests for schooltool.rest.app.

$Id: test_app.py 3526 2005-04-28 17:16:47Z bskahan $
"""

import unittest
import datetime

from StringIO import StringIO
from zope.testing import doctest
from schooltool.common import dedent
from zope.app import zapi
from zope.interface import directlyProvides, Interface
from zope.app.traversing.interfaces import ITraversable
from zope.interface.verify import verifyObject
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.traversing import namespace
from zope.app.testing import setup, ztapi
from zope.publisher.browser import TestRequest
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.filerepresentation.interfaces import IFileFactory

import schooltool.app
from schooltool import timetable
from schooltool.interfaces import ApplicationInitializationEvent
from schoolbell.app.rest.tests.utils import QuietLibxml2Mixin, diff
from schoolbell.app.rest.tests.utils import normalize_xml


def setUpSchool():
    from schooltool.app import SchoolToolApplication
    from zope.app.component.hooks import setSite
    from zope.app.component.site import LocalSiteManager
    app = SchoolToolApplication()

    # Usually automatically called subscribers
    schooltool.app.addCourseContainerToApplication(
        ApplicationInitializationEvent(app))
    schooltool.app.addSectionContainerToApplication(
        ApplicationInitializationEvent(app))
    timetable.addToApplication(ApplicationInitializationEvent(app))

    app.setSiteManager(LocalSiteManager(app))
    directlyProvides(app, IContainmentRoot)
    setSite(app)
    return app


def doctest_SchoolToolApplicationView():
    """SchoolToolApplication

    Lets create a schooltool instance and make a view for it:

        >>> from schooltool.rest.app import SchoolToolApplicationView
        >>> setup.placefulSetUp()
        >>> app = setUpSchool()
        >>> view = SchoolToolApplicationView(app, TestRequest())
        >>> result = view.GET()

    Lets test the XML output:

        >>> from schoolbell.app.rest.xmlparsing import XMLDocument
        >>> doc = XMLDocument(result)
        >>> doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')

    There should only be one set of containers:

        >>> nodes = doc.query('/schooltool/containers')
        >>> len(nodes)
        1

    Let's test our containers:

    persons:

        >>> persons = doc.query('/schooltool/containers/container'
        ...                     '[@xlink:href="http://127.0.0.1/persons"]')[0]
        >>> persons['xlink:type']
        u'simple'
        >>> persons['xlink:title']
        u'persons'

    groups:

        >>> groups = doc.query('/schooltool/containers/container'
        ...                     '[@xlink:href="http://127.0.0.1/groups"]')[0]
        >>> groups['xlink:type']
        u'simple'
        >>> groups['xlink:title']
        u'groups'

    resources:

        >>> resources = doc.query('/schooltool/containers/container'
        ...                     '[@xlink:href="http://127.0.0.1/resources"]')[0]
        >>> resources['xlink:type']
        u'simple'
        >>> resources['xlink:title']
        u'resources'

    sections:

        >>> sections = doc.query('/schooltool/containers/container'
        ...                     '[@xlink:href="http://127.0.0.1/sections"]')[0]
        >>> sections['xlink:type']
        u'simple'
        >>> sections['xlink:title']
        u'sections'

    courses:

        >>> courses = doc.query('/schooltool/containers/container'
        ...                     '[@xlink:href="http://127.0.0.1/courses"]')[0]
        >>> courses['xlink:type']
        u'simple'
        >>> courses['xlink:title']
        u'courses'

    that's all of our containers:

        >>> doc.free()

    XXX this is what our output should look like:





    """


class DatetimeStub:

    def utcnow(self):
        return datetime.datetime(2004, 1, 2, 3, 4, 5)


class TestTermView(QuietLibxml2Mixin, unittest.TestCase):

    def setUp(self):
        from schooltool.timetable import Term, TermContainer
        from schooltool.rest.app import TermView

        self.terms = TermContainer()
        self.terms["calendar"] =  self.term = Term(
            "Test",
            datetime.date(2003, 9, 1),
            datetime.date(2003, 9, 30))

        directlyProvides(self.terms, IContainmentRoot)

        self.view = TermView(self.term, TestRequest())
        self.view.datetime_hook = DatetimeStub()
        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownLibxml2()

    def test_get_empty(self):
        self.assertEqual(
            self.view.GET(),
            dedent(u"""
                BEGIN:VCALENDAR
                PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
                VERSION:2.0
                BEGIN:VEVENT
                UID:school-period-/calendar@127.0.0.1
                SUMMARY:School Period
                DTSTART;VALUE=DATE:20030901
                DTEND;VALUE=DATE:20031001
                DTSTAMP:20040102T030405Z
                END:VEVENT
                END:VCALENDAR
            """).replace("\n", "\r\n"))

    def test_get(self):
        self.term.addWeekdays(0, 1, 2, 3, 4) # Mon to Fri
        expected = dedent(u"""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/calendar@127.0.0.1
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20030901
            DTEND;VALUE=DATE:20031001
            DTSTAMP:20040102T030405Z
            END:VEVENT
        """)
        for date in self.term:
            if date.weekday() not in (5, 6):
                s = date.strftime("%Y%m%d")
                expected += dedent("""
                    BEGIN:VEVENT
                    UID:schoolday-%s-/calendar@127.0.0.1
                    SUMMARY:Schoolday
                    DTSTART;VALUE=DATE:%s
                    DTSTAMP:20040102T030405Z
                    END:VEVENT
                """ % (s, s))
        self.assertEqual(
            self.view.GET(),
            (expected + "END:VCALENDAR\n").replace("\n", "\r\n"))


class TestTermFileFactory(QuietLibxml2Mixin, unittest.TestCase):
    def setUp(self):
        from schooltool.timetable import Term, TermContainer
        from schooltool.rest.app import TermFileFactory
        from schooltool.rest.app import TermFile
        from schooltool.rest.app import TermView

        self.terms = TermContainer()
        self.fileFactory = TermFileFactory(self.terms)
        self.setUpLibxml2()


    def test_isDataICal(self):
        self.assert_(self.fileFactory.isDataICal("BEGIN:VCALENDAR"))
        self.assertEqual(self.fileFactory.isDataICal("<foo />"), False)

    def test_callText(self):
        calendar = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/person/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20040901
            DTEND;VALUE=DATE:20041001
            END:VEVENT
            BEGIN:VEVENT
            UID:random@example.com
            SUMMARY:Doctor's appointment
            DTSTART;VALUE=DATE:20040911
            END:VEVENT
            BEGIN:VEVENT
            UID:random2@example.com
            SUMMARY:Schoolday
            DTSTART;VALUE=DATE:20040912
            END:VEVENT
            BEGIN:VEVENT
            UID:random2@example.com
            SUMMARY:Schoolday
            DTSTART;VALUE=DATE:20040912
            END:VEVENT
            END:VCALENDAR
        """)
        # normalize line endings
        calendar = "\r\n".join(calendar.splitlines()) + "\r\n"

        term = self.fileFactory("calendar", "", calendar)

        self.assertEquals(term.title, "calendar")
        self.assertEquals(term.first, datetime.date(2004, 9, 1))
        self.assertEquals(term.last, datetime.date(2004, 9, 30))
        for date in term:
            if date == datetime.date(2004, 9, 12):
                self.assert_(term.isSchoolday(date))
            else:
                self.assert_(not term.isSchoolday(date))

    def test_callXML(self):
        body = dedent("""
            <schooldays xmlns="http://schooltool.org/ns/schooldays/0.1"
                        first="2003-09-01" last="2003-09-07">
              <title>Test.term!</title>
              <daysofweek>Monday Tuesday Wednesday Thursday Friday</daysofweek>
              <holiday date="2003-09-03">Holiday</holiday>
              <holiday date="2003-09-06">Holiday</holiday>
              <holiday date="2003-09-23">Holiday</holiday>
            </schooldays>
        """)

        term = self.fileFactory("calendar_from_xml", "", body)

        self.assertEquals(term.title, "Test.term!")
        self.assertEquals(term.first, datetime.date(2003, 9, 1))
        self.assertEquals(term.last, datetime.date(2003, 9, 7))
        schooldays = []
        for date in term:
            if term.isSchoolday(date):
                schooldays.append(date)
        expected = [datetime.date(2003, 9, d) for d in 1, 2, 4, 5]
        self.assertEquals(schooldays, expected)

    def test_invalid_name(self):
        from schoolbell.app.rest.errors import RestError
        self.assertRaises(RestError, self.fileFactory, "foo.bar", "", "")


class TestTermFile(QuietLibxml2Mixin, unittest.TestCase):

    def setUp(self):
        from schooltool.timetable import Term, TermContainer
        from schooltool.timetable.interfaces import ITermContainer
        from schooltool.rest.app import TermFileFactory
        from schooltool.rest.app import TermFile
        from schooltool.rest.app import TermView

        ztapi.provideAdapter(ITermContainer, IFileFactory, TermFileFactory)

        self.terms = TermContainer()
        self.terms["calendar"] =  self.term = Term(
            "Test",
            datetime.date(2003, 9, 1),
            datetime.date(2003, 9, 30))


        self.file = TermFile(self.term)

        self.setUpLibxml2()

    def test_write(self):
        calendar = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/person/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20040901
            DTEND;VALUE=DATE:20041001
            END:VEVENT
            BEGIN:VEVENT
            UID:random@example.com
            SUMMARY:Doctor's appointment
            DTSTART;VALUE=DATE:20040911
            END:VEVENT
            BEGIN:VEVENT
            UID:random2@example.com
            SUMMARY:Schoolday
            DTSTART;VALUE=DATE:20040912
            END:VEVENT
            BEGIN:VEVENT
            UID:random2@example.com
            SUMMARY:Schoolday
            DTSTART;VALUE=DATE:20040912
            END:VEVENT
            END:VCALENDAR
        """)
        # normalize line endings
        calendar = "\r\n".join(calendar.splitlines()) + "\r\n"

        self.file.write(calendar)

        self.assertEquals(self.term.first, datetime.date(2004, 9, 1))
        self.assertEquals(self.term.last, datetime.date(2004, 9, 30))
        for date in self.term:
            if date == datetime.date(2004, 9, 12):
                self.assert_(self.term.isSchoolday(date))
            else:
                self.assert_(not self.term.isSchoolday(date))

    def test_write_xml(self):
        body = dedent("""
            <schooldays xmlns="http://schooltool.org/ns/schooldays/0.1"
                        first="2003-09-01" last="2003-09-07">
              <title>A super title!</title>
              <daysofweek>Monday Tuesday Wednesday Thursday Friday</daysofweek>
              <holiday date="2003-09-03">Holiday</holiday>
              <holiday date="2003-09-06">Holiday</holiday>
              <holiday date="2003-09-23">Holiday</holiday>
            </schooldays>
        """)

        self.file.write(body)

        self.assertEquals(self.term.first, datetime.date(2003, 9, 1))
        self.assertEquals(self.term.last, datetime.date(2003, 9, 7))
        schooldays = []
        for date in self.term:
            if self.term.isSchoolday(date):
                schooldays.append(date)
        expected = [datetime.date(2003, 9, d) for d in 1, 2, 4, 5]
        self.assertEquals(schooldays, expected)


def compareXML(result, expected, recursively_sort=()):
    """Compare 2 XML snippets for equality.

    This is a doctest version of XMLCompareMixin.assertEqualsXML from
    schoolbell.app.rest.tests.utils.

    If recursively_sort is given, it is a sequence of tags that will have
    test:sort="recursively" appended to their attribute lists in 'result' text.
    See the docstring for normalize_xml for more information about this
    attribute.
    """
    result = normalize_xml(result, recursively_sort=recursively_sort)
    expected = normalize_xml(expected, recursively_sort=recursively_sort)
    if result == expected:
        return True
    else:
        print diff(expected, result)
        return False


def doctest_CourseFileFactory():
    r"""Tests for CourseFileFactory

        >>> from schooltool.app import CourseContainer
        >>> from schooltool.rest.app import CourseFileFactory
        >>> courses = CourseContainer
        >>> factory = CourseFileFactory(courses)

    We can create a few courses
        >>> course = factory("course1", None,
        ...              '''<object xmlns="http://schooltool.org/ns/model/0.1"
        ...                         title="New Course"/>''')
        >>> course.title
        u'New Course'
        >>> course.description

        >>> course = factory("course2", None,
        ...              '''<object xmlns="http://schooltool.org/ns/model/0.1"
        ...                         title="Newer Course"
        ...                         description="Newer, Better"/>''')

        >>> course.title
        u'Newer Course'
        >>> course.description
        u'Newer, Better'

    """


def doctest_CourseFile():
    r"""Tests for CourseFile.

        >>> from schooltool.rest.app import CourseFile, CourseFileFactory
        >>> from schooltool.app import CourseContainer, Course
        >>> from schooltool.interfaces import ICourseContainer
        >>> ztapi.provideAdapter(ICourseContainer,
        ...                      IFileFactory,
        ...                      CourseFileFactory)

        >>> courses = CourseContainer()
        >>> course = Course(title="History", description="US History")
        >>> course.title
        'History'
        >>> course.description
        'US History'

        >>> courses['course'] = course
        >>> file = CourseFile(course)
        >>> file.write('''<object xmlns="http://schooltool.org/ns/model/0.1"
        ...                       title="Herstory"
        ...                       description="Gender Aware History"/>''')
        >>> course.title
        u'Herstory'
        >>> course.description
        u'Gender Aware History'

    """


def doctest_CourseContainerView():
    r"""Tests for RESTive container view.

    Lets create a container and a course:

        >>> from schooltool.rest.app import CourseContainerView
        >>> from schooltool.rest.app import CourseFileFactory
        >>> from schooltool.interfaces import ICourseContainer
        >>> from schooltool.app import Course, CourseContainer
        >>> from schooltool.app import SchoolToolApplication
        >>> setup.placefulSetUp()
        >>> ztapi.provideView(Interface, Interface, ITraversable, 'view',
        ...                   namespace.view)
        >>> ztapi.provideAdapter(ICourseContainer,
        ...                     IFileFactory,
        ...                     CourseFileFactory)

        >>> app = setUpSchool()
        >>> courses = app['courses']
        >>> courses['course1'] = course1 = Course()

    lets create a RESTive view for it:

        >>> view = CourseContainerView(courses, TestRequest())
        >>> result = view.GET()
        >>> response = view.request.response
        >>> response.getHeader('content-type')
        'text/xml; charset=UTF-8'
        >>> compareXML(result,
        ... '''<container xmlns:xlink="http://www.w3.org/1999/xlink">
        ...    <name>courses</name>
        ...    <items>
        ...      <item xlink:href="http://127.0.0.1/courses/course1"
        ...            xlink:type="simple"/>
        ...    </items>
        ...    <acl xlink:href="http://127.0.0.1/courses/acl" xlink:title="ACL"
        ...         xlink:type="simple"/>
        ...  </container>''')
        True

    We can post to the container to create a course:

        >>> len(courses)
        1
        >>> body = '''<object xmlns="http://schooltool.org/ns/model/0.1"
        ...           title="new course" description="something new"/>'''
        >>> view = CourseContainerView(courses,
        ...                          TestRequest(StringIO(body)))
        >>> result = view.POST()
        >>> response = view.request.response
        >>> response.getStatus()
        201
        >>> response._reason
        'Created'
        >>> len(courses)
        2
        >>> courses['Course'].title
        u'new course'
        >>> courses['Course'].description
        u'something new'

    """


def doctest_CourseView():
    r"""Test for RESTive view of courses.

        >>> from schooltool.rest.app import CourseView
        >>> from schooltool.app import Course, CourseContainer
        >>> from schooltool.app import SchoolToolApplication
        >>> setup.placefulSetUp()
        >>> ztapi.provideView(Interface, Interface, ITraversable, 'view',
        ...                   namespace.view)

        >>> app = setUpSchool()
        >>> courses = app['courses']
        >>> courses['course1'] = course1 = Course(title="Course 1",
        ...                                       description="Something")
        >>> view = CourseView(course1, TestRequest())
        >>> result = view.GET()
        >>> response = view.request.response
        >>> response.getHeader('content-type')
        'text/xml; charset=UTF-8'
        >>> compareXML(result,'''
        ... <course xmlns:xlink="http://www.w3.org/1999/xlink">
        ...   <title>
        ...     Course 1
        ...   </title>
        ...   <description>Something</description>
        ...   <relationships
        ...      xlink:href="http://127.0.0.1/courses/course1/relationships"
        ...      xlink:title="Relationships"
        ...      xlink:type="simple"/>
        ...   <acl xlink:href="http://127.0.0.1/courses/course1/acl"
        ...      xlink:title="ACL" xlink:type="simple"/>
        ... </course>
        ... ''')
        True

    """


def doctest_SectionFileFactory():
    r"""Tests for SectionFileFactory

        >>> from schooltool.app import SectionContainer
        >>> from schooltool.rest.app import SectionFileFactory
        >>> sections = SectionContainer
        >>> factory = SectionFileFactory(sections)

    We can create a few sections

        >>> section = factory("section1", None,
        ...              '''<object xmlns="http://schooltool.org/ns/model/0.1"
        ...                         title="New Section"
        ...                         course="history"/>''')
        >>> section.title
        u'New Section'
        >>> section.description

        >>> section = factory("section2", None,
        ...              '''<object xmlns="http://schooltool.org/ns/model/0.1"
        ...                         title="Newer Section"
        ...                         course="history"
        ...                         description="Newer, Better"/>''')

        >>> section.title
        u'Newer Section'
        >>> section.description
        u'Newer, Better'

    We can identify a resource of a section, this requires a little more
    setup:


        >>> app = setUpSchool()
        >>> from schooltool.app import Resource
        >>> import pprint
        >>> app['resources']['room1'] = room1 = Resource("Room 1",
        ...                                               isLocation=True)
        >>> app['resources']['printer'] = printer = Resource("Printer")

        >>> section3 = factory("section3", None,
        ...              '''<object xmlns="http://schooltool.org/ns/model/0.1"
        ...                         title="Newer Section"
        ...                         course="history"
        ...                         location="room1"
        ...                         description="Newer, Better"/>''')

        >>> section3.location.title
        'Room 1'

    You can't add a location that isn't marked isLocation:

        >>> section4 = factory("section4", None,
        ...              '''<object xmlns="http://schooltool.org/ns/model/0.1"
        ...                         title="Newer Section"
        ...                         course="history"
        ...                         location="printer"
        ...                         description="Newer, Better"/>''')
        Traceback (most recent call last):
        ...
        TypeError: Locations must be location resources.

    If there's no location with that ID we get a RestError:

        >>> section4 = factory("section4", None,
        ...              '''<object xmlns="http://schooltool.org/ns/model/0.1"
        ...                         title="Newer Section"
        ...                         course="history"
        ...                         location="not-there"
        ...                         description="Newer, Better"/>''')
        Traceback (most recent call last):
        ...
        RestError: No such location.

    """


def doctest_SectionFile():
    r"""Tests for SectionFile.

        >>> from schooltool.rest.app import SectionFile, SectionFileFactory
        >>> from schooltool.app import SectionContainer, Section
        >>> from schooltool.interfaces import ISectionContainer
        >>> ztapi.provideAdapter(ISectionContainer,
        ...                      IFileFactory,
        ...                      SectionFileFactory)

        >>> sections = SectionContainer()
        >>> section = Section(title="Section 1", description="Good Students")
        >>> section.title
        'Section 1'
        >>> section.description
        'Good Students'

        >>> sections['section'] = section
        >>> file = SectionFile(section)
        >>> file.write('''<object xmlns="http://schooltool.org/ns/model/0.1"
        ...                       title="Section A"
        ...                       course="algebra"
        ...                       description="Still pretty good"/>''')
        >>> section.title
        u'Section A'
        >>> section.description
        u'Still pretty good'

    """


def doctest_SectionContainerView():
    r"""Tests for RESTive section container view.

    Lets create a container and a section:

        >>> from schooltool.rest.app import SectionContainerView
        >>> from schooltool.rest.app import SectionFileFactory
        >>> from schooltool.interfaces import ISectionContainer
        >>> from schooltool.app import Section, SectionContainer
        >>> from schooltool.app import SchoolToolApplication
        >>> setup.placefulSetUp()
        >>> ztapi.provideView(Interface, Interface, ITraversable, 'view',
        ...                   namespace.view)
        >>> ztapi.provideAdapter(ISectionContainer,
        ...                     IFileFactory,
        ...                     SectionFileFactory)

        >>> app = setUpSchool()
        >>> sections = app['sections']
        >>> sections['section1'] = section1 = Section()

    lets create a RESTive view for it:

        >>> view = SectionContainerView(sections, TestRequest())
        >>> result = view.GET()
        >>> response = view.request.response
        >>> response.getHeader('content-type')
        'text/xml; charset=UTF-8'
        >>> compareXML(result,
        ... '''<container xmlns:xlink="http://www.w3.org/1999/xlink">
        ...    <name>sections</name>
        ...    <items>
        ...      <item xlink:href="http://127.0.0.1/sections/section1"
        ...            xlink:title="Section" xlink:type="simple"/>
        ...    </items>
        ...    <acl xlink:href="http://127.0.0.1/sections/acl" xlink:title="ACL"
        ...         xlink:type="simple"/>
        ...  </container>''')
        True

    We can post to the container to create a section:

        >>> len(sections)
        1
        >>> body = '''<object xmlns="http://schooltool.org/ns/model/0.1"
        ...                   title="new section"
        ...                   course="algebra"
        ...                   description="something new"/>'''
        >>> view = SectionContainerView(sections,
        ...                          TestRequest(StringIO(body)))
        >>> result = view.POST()
        >>> response = view.request.response
        >>> response.getStatus()
        201
        >>> response._reason
        'Created'
        >>> len(sections)
        2
        >>> sections['Section'].title
        u'new section'
        >>> sections['Section'].description
        u'something new'

    """


def doctest_SectionView():
    r"""Test for RESTive view of sections.

        >>> from schooltool.rest.app import SectionView
        >>> from schooltool.app import Section, SectionContainer
        >>> from schooltool.app import SchoolToolApplication
        >>> setup.placefulSetUp()
        >>> ztapi.provideView(Interface, Interface, ITraversable, 'view',
        ...                   namespace.view)

        >>> app = setUpSchool()
        >>> sections = app['sections']
        >>> sections['section1'] = section1 = Section(title="Section 1",
        ...                                       description="Something")
        >>> view = SectionView(section1, TestRequest())
        >>> result = view.GET()
        >>> response = view.request.response
        >>> response.getHeader('content-type')
        'text/xml; charset=UTF-8'
        >>> compareXML(result,'''
        ... <section xmlns:xlink="http://www.w3.org/1999/xlink">
        ...   <title>
        ...     Section 1
        ...   </title>
        ...   <description>Something</description>
        ...   <relationships
        ...      xlink:href="http://127.0.0.1/sections/section1/relationships"
        ...      xlink:title="Relationships"
        ...      xlink:type="simple"/>
        ...   <acl xlink:href="http://127.0.0.1/sections/section1/acl"
        ...      xlink:title="ACL" xlink:type="simple"/>
        ... </section>
        ... ''')
        True

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schooltool.rest.app',
                                     optionflags=doctest.ELLIPSIS),
                unittest.makeSuite(TestTermView),
                unittest.makeSuite(TestTermFileFactory),
                unittest.makeSuite(TestTermFile)
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
