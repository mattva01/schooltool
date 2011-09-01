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
Unit tests for schooltool.generations.evolve36
"""
import unittest
import doctest

from zope.app.testing import setup
from zope.interface import implements
from zope.container.contained import Contained
from zope.container.btree import BTreeContainer

from schooltool.relationship.tests import setUpRelationships
from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.course.interfaces import ICourse


class AppStub(BTreeContainer):
    implements(ISchoolToolApplication)


class CourseStub(Contained):
    implements(ICourse)
    credits = None

    def __repr__(self):
        return '<CourseStub(__name__="%s", credits="%r")>' % (
            self.__name__, self.credits)


def doctest_evolve36():
    """Evolution to generation 36.

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()

    Set up courses with integer credits:

        >>> courses = app['courses'] = BTreeContainer()
        >>> courses['c1'] = CourseStub()
        >>> courses['c1'].credits = 5
        >>> courses['c2'] = CourseStub()
        >>> courses['c3'] = CourseStub()
        >>> courses['c3'].credits = 10
        >>> courses['c4'] = CourseStub()
        >>> courses['c4'].credits = 0
        >>> list(courses.values())
        [<CourseStub(__name__="c1", credits="5")>,
         <CourseStub(__name__="c2", credits="None")>,
         <CourseStub(__name__="c3", credits="10")>,
         <CourseStub(__name__="c4", credits="0")>]

    Let's evolve now.

        >>> from schooltool.generations.evolve36 import evolve
        >>> evolve(context)

    Course credits are now updated to Decimal values.

        >>> list(courses.values())
        [<CourseStub(__name__="c1", credits="Decimal('5')")>,
         <CourseStub(__name__="c2", credits="None")>,
         <CourseStub(__name__="c3", credits="Decimal('10')")>,
         <CourseStub(__name__="c4", credits="Decimal('0')")>]

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
