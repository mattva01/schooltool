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
Tests for schooltool timetabling views.

$Id$
"""

import unittest
import datetime
import itertools

from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.testing.doctestunit import pprint

from schoolbell.app.browser.tests.setup import setUp, tearDown


def doctest_TermAddView_buildTerm():
    """Unit tests for TermAddView._buildTerm

        >>> from schooltool.timetable import TermService
        >>> from schooltool.browser.timetable import TermAddView
        >>> context = TermService()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)

    When there are no dates in the request, or when the dates are not valid,
    view._buildTerm() returns None

        >>> view._buildTerm()

        >>> request.form['field.start_date'] = '2005-09-01'
        >>> request.form['field.end_date'] = 'not a clue'
        >>> view._buildTerm()

        >>> request.form['field.start_date'] = 'bogus'
        >>> request.form['field.end_date'] = '2005-12-31'
        >>> view._buildTerm()

        >>> request.form['field.start_date'] = '2005-12-31'
        >>> request.form['field.end_date'] = '2005-09-01'
        >>> view._buildTerm()

        >>> request.form['field.start_date'] = '2005-09-02'
        >>> request.form['field.end_date'] = '2005-09-01'
        >>> view._buildTerm()

    When the dates describe a valid non-empty inclusive time interval,
    view.calendar() returns a list of dicts, one for each month

        >>> request.form['field.start_date'] = '2005-09-01'
        >>> request.form['field.end_date'] = '2005-10-15'
        >>> term = view._buildTerm()
        >>> term.first
        datetime.date(2005, 9, 1)
        >>> term.last
        datetime.date(2005, 10, 15)

    """


def doctest_TermAddView_calendar():
    """Unit tests for TermAddView.calendar

        >>> from schooltool.timetable import TermService
        >>> from schooltool.browser.timetable import TermAddView
        >>> context = TermService()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)

    When there are no dates in the request, or when the dates are not valid,
    view.caledar() returns None

        >>> view.calendar()

        >>> request.form['field.start_date'] = '2005-09-01'
        >>> request.form['field.end_date'] = 'not a clue'
        >>> view.calendar()

        >>> request.form['field.start_date'] = 'bogus'
        >>> request.form['field.end_date'] = '2005-12-31'
        >>> view.calendar()

        >>> request.form['field.start_date'] = '2005-12-31'
        >>> request.form['field.end_date'] = '2005-09-01'
        >>> view.calendar()

        >>> request.form['field.start_date'] = '2005-09-02'
        >>> request.form['field.end_date'] = '2005-09-01'
        >>> view.calendar()

    When the dates describe a valid non-empty inclusive time interval,
    view.calendar() returns a list of dicts, one for each month.

        >>> def print_cal(calendar, day_format='%(number)3d'):
        ...     for month in calendar:
        ...         print '*%35s' % month['title']
        ...         print '         Mon Tue Wed Thu Fri Sat Sun'
        ...         for week in month['weeks']:
        ...             s = ['%-7s:' % week['title']]
        ...             for day in week['days']:
        ...                 if day['number'] is None:
        ...                     s.append('   ')
        ...                 else:
        ...                     s.append(day_format % day)
        ...             print ' '.join(s).rstrip()

        >>> request.form['field.start_date'] = '2004-08-01'
        >>> request.form['field.end_date'] = '2004-08-31'
        >>> print_cal(view.calendar())
        *                        August 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 31:                           1
        Week 32:   2   3   4   5   6   7   8
        Week 33:   9  10  11  12  13  14  15
        Week 34:  16  17  18  19  20  21  22
        Week 35:  23  24  25  26  27  28  29
        Week 36:  30  31

        >>> request.form['field.start_date'] = '2004-08-02'
        >>> request.form['field.end_date'] = '2004-09-01'
        >>> print_cal(view.calendar())
        *                        August 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 32:   2   3   4   5   6   7   8
        Week 33:   9  10  11  12  13  14  15
        Week 34:  16  17  18  19  20  21  22
        Week 35:  23  24  25  26  27  28  29
        Week 36:  30  31
        *                     September 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 36:           1

        >>> request.form['field.start_date'] = '2004-08-03'
        >>> request.form['field.end_date'] = '2004-08-03'
        >>> print_cal(view.calendar())
        *                        August 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 32:       3

        >>> request.form['field.start_date'] = '2004-12-30'
        >>> request.form['field.end_date'] = '2005-01-03'
        >>> print_cal(view.calendar())
        *                      December 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 53:              30  31
        *                       January 2005
                 Mon Tue Wed Thu Fri Sat Sun
        Week 53:                       1   2
        Week 1 :   3

    Each day gets a numeric index, used in Javascript

        >>> request.form['field.start_date'] = '2004-12-30'
        >>> request.form['field.end_date'] = '2005-01-03'
        >>> print_cal(view.calendar(), '%(index)3s')
        *                      December 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 53:               1   2
        *                       January 2005
                 Mon Tue Wed Thu Fri Sat Sun
        Week 53:                       3   4
        Week 1 :   5

    """


def doctest_TermAddView_month():
    """Unit test for TermAddView.month

        >>> from schooltool.browser.timetable import TermAddView
        >>> month = TermAddView.month

    The month function goes through all weeks between mindate and maxdate.

        >>> def print_month(month, day_format='%(number)3d'):
        ...     print '*%35s' % month['title']
        ...     print '         Mon Tue Wed Thu Fri Sat Sun'
        ...     for week in month['weeks']:
        ...         s = ['%-7s:' % week['title']]
        ...         for day in week['days']:
        ...             if day['number'] is None:
        ...                 s.append('   ')
        ...             else:
        ...                 s.append(day_format % day)
        ...         print ' '.join(s).rstrip()

        >>> counter = itertools.count(1)

        >>> print_month(month(datetime.date(2005, 5, 1),
        ...                   datetime.date(2005, 5, 31), counter))
        *                           May 2005
                 Mon Tue Wed Thu Fri Sat Sun
        Week 17:                           1
        Week 18:   2   3   4   5   6   7   8
        Week 19:   9  10  11  12  13  14  15
        Week 20:  16  17  18  19  20  21  22
        Week 21:  23  24  25  26  27  28  29
        Week 22:  30  31

        >>> print_month(month(datetime.date(2005, 5, 2),
        ...                   datetime.date(2005, 5, 30), counter))
        *                           May 2005
                 Mon Tue Wed Thu Fri Sat Sun
        Week 18:   2   3   4   5   6   7   8
        Week 19:   9  10  11  12  13  14  15
        Week 20:  16  17  18  19  20  21  22
        Week 21:  23  24  25  26  27  28  29
        Week 22:  30

        >>> print_month(month(datetime.date(2005, 5, 3),
        ...                   datetime.date(2005, 5, 29), counter))
        *                           May 2005
                 Mon Tue Wed Thu Fri Sat Sun
        Week 18:       3   4   5   6   7   8
        Week 19:   9  10  11  12  13  14  15
        Week 20:  16  17  18  19  20  21  22
        Week 21:  23  24  25  26  27  28  29

        >>> print_month(month(datetime.date(2005, 5, 10),
        ...                   datetime.date(2005, 5, 11), counter))
        *                           May 2005
                 Mon Tue Wed Thu Fri Sat Sun
        Week 19:      10  11

        >>> print_month(month(datetime.date(2005, 5, 17),
        ...                   datetime.date(2005, 5, 17), counter))
        *                           May 2005
                 Mon Tue Wed Thu Fri Sat Sun
        Week 20:      17

    """


def doctest_TermAddView_week():
    """Unit test for TermAddView.week

        >>> from schooltool.browser.timetable import TermAddView
        >>> week = TermAddView.week

    The week function is pretty simple.  First we will try to pass Monday
    as start_of_week.

        >>> def print_week(week):
        ...     print week['title']
        ...     print 'index date number checked class onclick'
        ...     for day in week['days']:
        ...         print ('%(index)s %(date)s %(number)s %(checked)s'
        ...                ' %(class)s %(onclick)s') % day

        >>> counter = itertools.count(1)

        >>> print_week(week(datetime.date(2005, 5, 2),
        ...                 datetime.date(2005, 5, 2),
        ...                 datetime.date(2005, 5, 8),
        ...                 counter))
        Week 18
        index date number checked class onclick
        1 2005-05-02 2 False schoolday javascript:toggle(1)
        2 2005-05-03 3 False schoolday javascript:toggle(2)
        3 2005-05-04 4 False schoolday javascript:toggle(3)
        4 2005-05-05 5 False schoolday javascript:toggle(4)
        5 2005-05-06 6 False schoolday javascript:toggle(5)
        6 2005-05-07 7 False schoolday javascript:toggle(6)
        7 2005-05-08 8 False schoolday javascript:toggle(7)

    min_date is handled

        >>> print_week(week(datetime.date(2005, 5, 2),
        ...                 datetime.date(2005, 5, 3),
        ...                 datetime.date(2005, 5, 8),
        ...                 counter))
        Week 18
        index date number checked class onclick
        None None None None None None
        8 2005-05-03 3 False schoolday javascript:toggle(8)
        9 2005-05-04 4 False schoolday javascript:toggle(9)
        10 2005-05-05 5 False schoolday javascript:toggle(10)
        11 2005-05-06 6 False schoolday javascript:toggle(11)
        12 2005-05-07 7 False schoolday javascript:toggle(12)
        13 2005-05-08 8 False schoolday javascript:toggle(13)

    max_date is handled too

        >>> print_week(week(datetime.date(2005, 5, 2),
        ...                 datetime.date(2005, 5, 3),
        ...                 datetime.date(2005, 5, 6),
        ...                 counter))
        Week 18
        index date number checked class onclick
        None None None None None None
        14 2005-05-03 3 False schoolday javascript:toggle(14)
        15 2005-05-04 4 False schoolday javascript:toggle(15)
        16 2005-05-05 5 False schoolday javascript:toggle(16)
        17 2005-05-06 6 False schoolday javascript:toggle(17)
        None None None None None None
        None None None None None None

    Weeks can start on Sundays too

        >>> print_week(week(datetime.date(2005, 5, 1),
        ...                 datetime.date(2005, 5, 1),
        ...                 datetime.date(2005, 5, 8),
        ...                 counter))
        Week 18
        index date number checked class onclick
        18 2005-05-01 1 False schoolday javascript:toggle(18)
        19 2005-05-02 2 False schoolday javascript:toggle(19)
        20 2005-05-03 3 False schoolday javascript:toggle(20)
        21 2005-05-04 4 False schoolday javascript:toggle(21)
        22 2005-05-05 5 False schoolday javascript:toggle(22)
        23 2005-05-06 6 False schoolday javascript:toggle(23)
        24 2005-05-07 7 False schoolday javascript:toggle(24)

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite



if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
