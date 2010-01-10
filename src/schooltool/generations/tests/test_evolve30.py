#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve30
"""
import unittest
import doctest

from zope.app.testing import setup
from zope.interface import implements
from zope.app.container import btree
from zope.app.container.contained import Contained
from zope.component import provideHandler

from schooltool.relationship.tests import setUpRelationships
from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.person import BasicPerson
from schooltool.group.group import Group
from schooltool.relationship.interfaces import IRelationshipRemovedEvent
from schooltool.relationship.interfaces import IRelationshipAddedEvent
from schooltool.relationship.relationship import relate
from schooltool.app.membership import URIMember, URIGroup, URIMembership
from schooltool.course.interfaces import ICourse


class AppStub(btree.BTreeContainer):
    implements(ISchoolToolApplication)


class CourseStub(Contained):
    implements(ICourse)
    course_id = None

    def __repr__(self):
        return '<CourseStub(__name__="%s", course_id="%s")>' % (
            self.__name__, self.course_id)


def printRelationshipAdded(event):
    if event.rel_type != URIMembership:
        return
    print 'ADD: %15s to   %s' % (
        event[URIMember].title, event[URIGroup].title)


def printRelationshipRemoved(event):
    if event.rel_type != URIMembership:
        return
    print 'REMOVE: %12s from %s' % (
        event[URIMember].title, event[URIGroup].title)


def doctest_evolve30():
    """Evolution to generation 30.

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()

        >>> persons = app['persons'] = btree.BTreeContainer()
        >>> persons['will'] = BasicPerson("will", "William", "Straus")
        >>> persons['vlad'] = BasicPerson("vlad", "Vladimir", "Rubov")
        >>> persons['john'] = BasicPerson("john", "Johny", "John")
        >>> persons['pete'] = BasicPerson("pete", "Petey", "Pete")
        >>> persons['bill'] = BasicPerson("bill", "Billy", "Bill")

        >>> groups = app['groups'] = btree.BTreeContainer()
        >>> groups['guests'] = Group('Guests')
        >>> groups['students'] = Group('Students')

        >>> sections = app['sections'] = btree.BTreeContainer()
        >>> sections['section_1'] = Group('Section ONE')
        >>> sections['section_2'] = Group('Section TWO')

        >>> def addMember(member, group):
        ...     relate(URIMembership,
        ...            (member, URIMember),
        ...            (group, URIGroup))

        >>> addMember(persons['john'], groups['students'])
        >>> addMember(persons['pete'], groups['students'])
        >>> addMember(persons['bill'], groups['students'])

        >>> addMember(persons['will'], groups['guests'])
        >>> addMember(persons['vlad'], groups['guests'])

    Set up section relationships.

    Add one guest to Section ONE, but not the group.

        >>> addMember(persons['vlad'], sections['section_1'])

    Add both guests to Section TWO and the group.

        >>> addMember(groups['guests'], sections['section_2'])
        >>> addMember(persons['vlad'], sections['section_2'])
        >>> addMember(persons['will'], sections['section_2'])

    Add just the students group to Section ONE.

        >>> addMember(groups['students'], sections['section_1'])

    Add two of three students to Section TWO, and the students group.

        >>> addMember(groups['students'], sections['section_2'])
        >>> addMember(persons['bill'], sections['section_2'])
        >>> addMember(persons['pete'], sections['section_2'])

    We will also update course ids, so let's set up some.

        >>> courses = app['courses'] = btree.BTreeContainer()
        >>> courses['c1'] = CourseStub()
        >>> courses['c2'] = CourseStub()
        >>> courses['c3'] = CourseStub()
        >>> courses['c3'].course_id = 'custom'
        >>> list(courses.values())
        [<CourseStub(__name__="c1", course_id="None")>,
         <CourseStub(__name__="c2", course_id="None")>,
         <CourseStub(__name__="c3", course_id="custom")>]

    Let's evolve now.

        >>> provideHandler(printRelationshipAdded,
        ...                [IRelationshipAddedEvent])
        >>> provideHandler(printRelationshipRemoved,
        ...                [IRelationshipRemovedEvent])

        >>> from schooltool.generations.evolve30 import evolve
        >>> evolve(context)
        REMOVE:       Guests from Section TWO
        <BLANKLINE>
        ADD:     John, Johny to   Section ONE
        ADD:     Pete, Petey to   Section ONE
        ADD:     Bill, Billy to   Section ONE
        REMOVE:     Students from Section ONE
        <BLANKLINE>
        ADD:     John, Johny to   Section TWO
        REMOVE:     Students from Section TWO

    Course ids are also updated.

        >>> list(courses.values())
        [<CourseStub(__name__="c1", course_id="c1")>,
         <CourseStub(__name__="c2", course_id="c2")>,
         <CourseStub(__name__="c3", course_id="custom")>]

    """


def setUp(test):
    setup.placelessSetUp()
    setup.setUpAnnotations()
    setUpRelationships()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=optionflags)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
