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
Unit tests for schoolbell.calendar

When this module grows too big, it will be split into a number of modules in
a package called tests.  Each of those new modules will be named test_foo.py
and will test schoolbell.calendar.foo.

$Id$
"""

import unittest
from zope.testing import doctest


def doctest_interfaces():
    """Look for syntax errors in interfaces.py

        >>> import schoolbell.calendar.interfaces

    """


def doctest_simple_CalendarEventMixin_replace():
    """Make sure CalendarEventMixin.replace does not forget any attributes.

        >>> from schoolbell.calendar.interfaces import ICalendarEvent
        >>> from zope.schema import getFieldNames
        >>> all_attrs = getFieldNames(ICalendarEvent)

    We will use SimpleCalendarEvent which is a trivial subclass of
    CalendarEventMixin

        >>> from datetime import datetime, timedelta
        >>> from schoolbell.calendar.simple import SimpleCalendarEvent
        >>> e1 = SimpleCalendarEvent(datetime(2004, 12, 15, 18, 57),
        ...                          timedelta(minutes=15),
        ...                          'Work on schoolbell.calendar.simple')

        >>> for attr in all_attrs:
        ...     e2 = e1.replace(**{attr: 'new value'})
        ...     assert getattr(e2, attr) == 'new value', attr
        ...     assert e2 != e1, attr
        ...     assert e2.replace(**{attr: getattr(e1, attr)}) == e1, attr

    """


def doctest_weeknum_bounds():
    """Unit test for schoolbell.calendar.utils.weeknum_bounds.

    Check that weeknum_bounds is the reverse of datetime.isocalendar().

        >>> from datetime import date
        >>> from schoolbell.calendar.utils import weeknum_bounds
        >>> d = date(2000, 1, 1)
        >>> while d < date(2010, 1, 1):
        ...     year, weeknum, weekday = d.isocalendar()
        ...     l, h = weeknum_bounds(year, weeknum)
        ...     assert l <= d <= h
        ...     d += d.resolution

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite())
    suite.addTest(doctest.DocFileSuite('../README.txt'))
    suite.addTest(doctest.DocTestSuite('schoolbell.calendar.mixins'))
    suite.addTest(doctest.DocTestSuite('schoolbell.calendar.simple'))
    suite.addTest(doctest.DocTestSuite('schoolbell.calendar.recurrent'))
    suite.addTest(doctest.DocTestSuite('schoolbell.calendar.utils'))
    suite.addTest(doctest.DocTestSuite('schoolbell.calendar.browser',
                        optionflags=doctest.ELLIPSIS | doctest.REPORT_UDIFF))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
