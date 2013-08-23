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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""Unit tests for schooltool.term.sampledata
"""
import unittest
import doctest

from zope.component import provideAdapter
from zope.interface import Interface
from zope.interface.verify import verifyObject
from zope.app.testing import setup

from schooltool.schoolyear.schoolyear import getSchoolYearContainer
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.term.term import getTermContainer
from schooltool.term.interfaces import ITermContainer
from schooltool.testing import setup as stsetup


def setUp(test):
    setup.placefulSetUp()
    provideAdapter(getTermContainer, [Interface], ITermContainer)
    provideAdapter(getSchoolYearContainer)


def tearDown(test):
    setup.placefulTearDown()


def doctest_SampleTerms():
    """A sample data plugin that creates terms

        >>> from schooltool.term.sampledata import SampleTerms
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleTerms()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    This plugin generates a school year:

        >>> app = stsetup.setUpSchoolToolSite()
        >>> plugin.generate(app, 42)
        >>> list(ISchoolYearContainer(app))
        [u'2005-2006']

    The school year contains three terms:

        >>> len(ITermContainer(app))
        3

    These terms are 90 schooldays long:

        >>> fall = ITermContainer(app)['2005-fall']
        >>> schooldays = [day for day in fall if fall.isSchoolday(day)]
        >>> len(schooldays)
        90

        >>> spring = ITermContainer(app)['2006-spring']
        >>> schooldays = [day for day in spring if spring.isSchoolday(day)]
        >>> len(schooldays)
        90

        >>> fall6 = ITermContainer(app)['2006-fall']
        >>> schooldays = [day for day in fall6 if fall6.isSchoolday(day)]
        >>> len(schooldays)
        90

    They span these dates:

        >>> print fall.first, fall.last
        2005-08-22 2005-12-23
        >>> print spring.first, spring.last
        2006-01-26 2006-05-31
        >>> print fall6.first, fall6.last
        2006-08-21 2006-12-22

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
