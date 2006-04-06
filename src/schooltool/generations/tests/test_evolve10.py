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
Unit tests for schooltool.generations.evolve10

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


def doctest_evolve10():
    """Evolution to generation 10.

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> from schooltool.timetable.interfaces import ITimetables
        >>> from schooltool.timetable.interfaces import IHaveTimetables

        >>> class TimetableStub:
        ...     pass

        >>> class TimetabledStub:
        ...     implements(ITimetables, IHaveTimetables)
        ...     timetables = {'foo.bar': TimetableStub(),
        ...                   'baz.quux': TimetableStub()}
        ...     def __init__(self, name):
        ...        self.name = name
        ...     def __repr__(self):
        ...        return 'Timetabled(%r)' % self.name

        >>> class MockSchoolTool(dict):
        ...     implements(ISchoolToolApplication, IApplicationPreferences,
        ...                IHaveTimetables, ITimetables)
        ...     timezone = 'Asia/Tokyo'
        ...     timetables = {'foo.bar': TimetableStub(),
        ...                   'baz.quux': TimetableStub()}

        >>> context = ContextStub()
        >>> app = MockSchoolTool()
        >>> app['ttschemas'] = BTreeContainer()
        >>> app['persons'] = BTreeContainer()
        >>> app['groups'] = BTreeContainer()
        >>> app['sections'] = BTreeContainer()
        >>> app['resources'] = BTreeContainer()
        >>> context.root_folder['app'] = app

    Let's create a few objects:

        >>> s1 = app['sections']['section1'] = TimetabledStub('s1')
        >>> s2 = app['sections']['section2'] = TimetabledStub('s1')
        >>> r1 = app['resources']['r1'] = TimetabledStub('r1')
        >>> p1 = app['persons']['p1'] = TimetabledStub('p1')
        >>> g1 = app['groups']['g1'] = TimetabledStub('g1')

        >>> app['ttschemas']['foo'] = TimetableStub()
        >>> app['ttschemas']['bar'] = TimetableStub()

    Shazam!

        >>> from schooltool.generations.evolve10 import evolve
        >>> evolve(context)

        >>> for ob in app, s1, s2, r1, p1, g1:
        ...    assert ob.timetables['foo.bar'].timezone == 'Asia/Tokyo', ob
        ...    assert ob.timetables['baz.quux'].timezone == 'Asia/Tokyo', ob
        >>> for ob in app['ttschemas'].values():
        ...    assert ob.timezone == 'Asia/Tokyo'

    """


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
