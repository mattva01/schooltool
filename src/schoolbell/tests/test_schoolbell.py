"""
Unit tests for schoolbell

When this module grows too big, it will be split into a number of modules in
a package called tests.  Each of those new modules will be named test_foo.py
and will test schoolbell.foo.
"""

import unittest
from zope.testing import doctest


def doctest_interfaces():
    """Look for syntax errors in interfaces.py

        >>> import schoolbell.interfaces

    """


def doctest_simple_CalendarEventMixin_replace():
    """Make sure CalendarEventMixin.replace does not forget any attributes.

        >>> from schoolbell.interfaces import ICalendarEvent
        >>> from zope.schema import getFieldNames
        >>> all_attrs = getFieldNames(ICalendarEvent)

    We will use SimpleCalendarEvent which is a trivial subclass of
    CalendarEventMixin

        >>> from datetime import datetime, timedelta
        >>> from schoolbell.simple import SimpleCalendarEvent
        >>> e1 = SimpleCalendarEvent(datetime(2004, 12, 15, 18, 57),
        ...                          timedelta(minutes=15),
        ...                          'Work on schoolbell.simple')

        >>> for attr in all_attrs:
        ...     e2 = e1.replace(**{attr: 'new value'})
        ...     assert getattr(e2, attr) == 'new value', attr
        ...     assert e2 != e1, attr
        ...     assert e2.replace(**{attr: getattr(e1, attr)}) == e1, attr

    """


def doctest_weeknum_bounds():
    """Unit test for schoolbell.utils.weeknum_bounds.

    Check that weeknum_bounds is the reverse of datetime.isocalendar().

        >>> from datetime import date
        >>> from schoolbell.utils import weeknum_bounds
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
    suite.addTest(doctest.DocTestSuite('schoolbell.mixins'))
    suite.addTest(doctest.DocTestSuite('schoolbell.simple'))
    suite.addTest(doctest.DocTestSuite('schoolbell.utils'))
    suite.addTest(doctest.DocTestSuite('schoolbell.browser',
                        optionflags=doctest.ELLIPSIS | doctest.REPORT_UDIFF))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
