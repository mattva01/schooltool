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
"""Unit tests for schooltool.term.sampledata

$Id$
"""
import unittest

from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.testing import setup

from schooltool.testing import setup as stsetup

def setUp(test):
    setup.placefulSetUp()


def tearDown(test):
    setup.placefulTearDown()

def doctest_SampleTerms():
    """A sample data plugin that creates terms

        >>> from schooltool.term.sampledata import SampleTerms
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleTerms()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    This plugin generates two terms:

        >>> app = stsetup.setUpSchoolToolSite()
        >>> plugin.generate(app, 42)
        >>> len(app['terms'])
        2

    These terms are 90 schooldays long:

        >>> fall = app['terms']['2005-fall']
        >>> schooldays = [day for day in fall if fall.isSchoolday(day)]
        >>> len(schooldays)
        90

        >>> spring = app['terms']['2006-spring']
        >>> schooldays = [day for day in spring if spring.isSchoolday(day)]
        >>> len(schooldays)
        90

    They span these dates:

        >>> print fall.first, fall.last
        2005-08-22 2005-12-23
        >>> print spring.first, spring.last
        2006-01-26 2006-05-31

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
