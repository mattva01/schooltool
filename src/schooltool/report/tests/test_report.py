#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
"""
Unit tests for report functionality.

"""
import unittest
import doctest

from zope.app.testing import setup

from schooltool.report import report


def doctest_Something(self):
    """Tests for something.
    """


def setUp(test=None):
    setup.placefulSetUp()


def tearDown(test=None):
    setup.placefulTearDown()


def test_suite():
    optionflags = (doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 setUp=setUp, tearDown=tearDown)
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

