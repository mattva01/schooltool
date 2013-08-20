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
"""
Tests for schooltool.app.browser.skin.
"""

import unittest
import doctest


def doctest_CalendarEventViewletManager():
    """Tests for CalendarEventViewletManager.

        >>> from schooltool.app.browser.skin import CalendarEventViewletManager
        >>> from schooltool.app.browser.skin import ICalendarEventContext
        >>> viewletManager = CalendarEventViewletManager(None, None, None)
        >>> ICalendarEventContext.providedBy(viewletManager)
        True

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(),
           ])


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
