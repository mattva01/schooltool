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
Tests for SchoolBell calendaring views.

$Id$
"""

import unittest
from zope.testing import doctest


def doctest_PlainCalendarView():
    """Tests for PlainCalendarView.

        >>> from schoolbell.app.browser.cal import PlainCalendarView
        >>> from schoolbell.app.app import Person
        >>> from zope.publisher.browser import TestRequest
        >>> person = Person()
        >>> request = TestRequest()
        >>> view = PlainCalendarView(person, request)
        >>> view.update()
        >>> len(person.calendar)
        0

        >>> request = TestRequest()
        >>> request.form = {'GENERATE': ''}
        >>> view = PlainCalendarView(person, request)
        >>> view.update()
        >>> len(person.calendar)
        5

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite())
    suite.addTest(doctest.DocTestSuite('schoolbell.app.browser.cal'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
