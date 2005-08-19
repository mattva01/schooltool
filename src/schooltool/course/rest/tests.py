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
Tests for course-related RESTive views.

$Id: test_app.py 4691 2005-08-12 18:59:44Z srichter $
"""
import unittest
from cStringIO import StringIO

from zope.interface import Interface
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.filerepresentation.interfaces import IFileFactory
from zope.app.testing import setup, ztapi
from zope.app.traversing import namespace
from zope.app.traversing.interfaces import ITraversable

from schooltool.testing import setup as sbsetup
from schooltool.app.rest.testing import compareXML

from schooltool.course.course import Course, CourseContainer
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.rest.course import CourseFile, CourseFileFactory
from schooltool.course.rest.course import CourseView, CourseContainerView

from schooltool.course.section import Section, SectionContainer
from schooltool.course.interfaces import ISectionContainer
from schooltool.course.rest.section import SectionFile, SectionFileFactory
from schooltool.course.rest.section import SectionView, SectionContainerView


def doctest_CourseFileFactory():
    r"""Tests for CourseFileFactory

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

        >>> from schooltool.app.app import SchoolToolApplication
        >>> setup.placefulSetUp()
        >>> ztapi.provideView(Interface, Interface, ITraversable, 'view',
        ...                   namespace.view)
        >>> ztapi.provideAdapter(ICourseContainer,
        ...                     IFileFactory,
        ...                     CourseFileFactory)

        >>> app = sbsetup.setupSchoolToolSite()
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

        >>> from schooltool.app.app import SchoolToolApplication
        >>> setup.placefulSetUp()
        >>> ztapi.provideView(Interface, Interface, ITraversable, 'view',
        ...                   namespace.view)

        >>> app = sbsetup.setupSchoolToolSite()
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


        >>> app = sbsetup.setupSchoolToolSite()
        >>> from schooltool.resource.resource import Resource

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

        >>> from schooltool.app.app import SchoolToolApplication
        >>> setup.placefulSetUp()
        >>> ztapi.provideView(Interface, Interface, ITraversable, 'view',
        ...                   namespace.view)
        >>> ztapi.provideAdapter(ISectionContainer,
        ...                     IFileFactory,
        ...                     SectionFileFactory)

        >>> app = sbsetup.setupSchoolToolSite()
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

        >>> from schooltool.app.app import SchoolToolApplication
        >>> setup.placefulSetUp()
        >>> ztapi.provideView(Interface, Interface, ITraversable, 'view',
        ...                   namespace.view)

        >>> app = sbsetup.setupSchoolToolSite()
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
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
