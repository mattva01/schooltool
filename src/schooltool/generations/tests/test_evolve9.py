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
Unit tests for schooltool.generations.evolve6

$Id$
"""

import unittest

from zope.app.testing import setup
from zope.testing import doctest
from zope.app.container.btree import BTreeContainer
from zope.interface import implements

from schooltool.resource.resource import Resource
from schooltool.course.section import Section
from schooltool.generations.tests import ContextStub


def setUp(test):
    setup.placelessSetUp()
    setup.setUpAnnotations()


def tearDown(test):
    setup.placelessTearDown()


def doctest_evolve9_book_location():
    """Evolution to generation 9.

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> class MockSchoolTool(dict):
        ...     implements(ISchoolToolApplication)

        >>> context = ContextStub()
        >>> app = MockSchoolTool()
        >>> app['sections'] = BTreeContainer()
        >>> app['resources'] = BTreeContainer()
        >>> context.root_folder['app'] = app

        >>> from schooltool.relationship.interfaces import IRelationshipLinks
        >>> from schooltool.course.interfaces import ISection
        >>> class ResourceStub:
        ...     def __repr__(self):
        ...         return 'resource'
        >>> class SectionStub:
        ...     def __init__(self):
        ...         self.resources = set()

    Let's create a few sections and resources:

        >>> s1 = app['sections']['section1'] = SectionStub()
        >>> s2 = app['sections']['section2'] = SectionStub()
        >>> r1 = app['resources']['r1'] = ResourceStub()

        >>> s1.location = r1
        >>> s1.resources
        set([])

    Shazam!

        >>> from schooltool.generations.evolve9 import evolve
        >>> evolve(context)

    Let's check the first section (with a location).  The resource should now
    be booked:

        >>> s1.resources
        set([resource])

    And the locations attribute went away:

        >>> s1.location
        Traceback (most recent call last):
            ...
        AttributeError: SectionStub instance has no attribute 'location'

    The second section didn't gain a booking and lost its attribute too:

        >>> s2.resources
        set([])
        >>> s2.location
        Traceback (most recent call last):
            ...
        AttributeError: SectionStub instance has no attribute 'location'

    """


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
