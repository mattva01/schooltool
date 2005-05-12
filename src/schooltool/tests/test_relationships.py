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
Unit tests for schooltool.relationships

$Id: test_app.py 3504 2005-04-22 16:34:13Z bskahan $
"""

import unittest
from zope.testing import doctest
from zope.app import zapi
from zope.interface.verify import verifyObject


def doctest_Instruction():
    r"""Tests for Instruction URIs and methods

        >>> from schooltool.relationships import *

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()
        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> zope.event.subscribers.append(enforceInstructionConstraints)

    We will need some sample persons and sections for the demonstration

        >>> from schoolbell.app.app import Person
        >>> from schooltool.app import Section
        >>> jonas = Person()
        >>> petras = Person()
        >>> developers = Section()
        >>> admins = Section()

    There are some constraints: Only objects providing ISection can be
    Sections.

        >>> Instruction(instructor=jonas, section=petras)
        Traceback (most recent call last):
          ...
        InvalidRelationship: Sections must provide ISection.

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """


def doctest_CourseSections():
    r"""Tests for CourseSections relationship

    Lets import the pieces of CourseSections

        >>> from schooltool.relationships import URICourseSections, URICourse
        >>> from schooltool.relationships import URISectionOfCourse
        >>> from schooltool.relationships import enforceCourseSectionConstraint

    Relationship tests require some setup:

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()
        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> zope.event.subscribers.append(enforceCourseSectionConstraint)

    We will need a course and several sections:

        >>> from schooltool.app import Course, Section, Person
        >>> history = Course()
        >>> section1 = Section(title = "section1")
        >>> section2 = Section(title = "section2")
        >>> section3 = Section(title = "section3")
        >>> person = Person()

    Our course doesn't have any sections yet:

        >>> for section in history.sections:
        ...     print section

    Lets add one:

        >>> history.sections.add(section1)
        >>> for section in history.sections:
        ...     print section.title
        section1

    Lets try to add a person to the course:

        >>> history.sections.add(person)
        Traceback (most recent call last):
        ...
        InvalidRelationship: Sections must provide ISection.

    Lets try to add a course to the course:

        >>> algebra = Course()
        >>> history.sections.add(algebra)
        Traceback (most recent call last):
        ...
        InvalidRelationship: Sections must provide ISection.

    No luck, you can only add sections:

        >>> history.sections.add(section2)
        >>> history.sections.add(section3)
        >>> for section in history.sections:
        ...     print section.title
        section1
        section2
        section3

    That's it:

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schooltool.relationships',
                                     optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
