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
from pprint import pprint

from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.testing.doctestunit import pprint
from zope.app.testing import ztapi
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.component.hooks import setSite
from zope.app.component.site import LocalSiteManager
from zope.i18n import translate

from schoolbell.app.browser.tests.setup import setUp, tearDown
from schoolbell.app.rest.tests.utils import NiceDiffsMixin


def createSchema(days, *periods_for_each_day):
    """Create a timetable schema.

    Example:

        createSchema(['D1', 'D2', 'D3'], ['A'], ['B', 'C'], ['D'])

    creates a schema with three days, the first of which (D1) has one
    period (A), the second (D2) has two periods (B and C), and the third
    (D3) has again one period (D).
    """

    from schooltool.timetable import TimetableSchema
    from schooltool.timetable import TimetableSchemaDay
    schema = TimetableSchema(days)
    for day, periods in zip(days, periods_for_each_day):
        schema[day] = TimetableSchemaDay(list(periods))
    return schema


def createDayTemplate(periods):
    """Create a SchooldayTemplate.

    Example:

        createDayTemplate([('Period 1', 9, 30, 45),
                           ('Period 2', 10, 30, 45)])

    would create a day template containing two periods, the first one starting
    at 9:30, the second one starting at 10:30, both 45 minutes long.
    """
    from schooltool.timetable import SchooldayTemplate
    from schooltool.timetable import SchooldayPeriod
    day = SchooldayTemplate()
    for period, h, m, duration in periods:
        day.add(SchooldayPeriod(period, datetime.time(h, m),
                                datetime.timedelta(minutes=duration)))
    return day


def doctest_TermView_calendar():
    """Unit tests for TermAddView.calendar

        >>> from schooltool.timetable import Term
        >>> from schooltool.timetable.browser import TermView
        >>> context = Term('Sample', datetime.date(2004, 8, 1),
        ...                        datetime.date(2004, 8, 31))
        >>> request = TestRequest()
        >>> view = TermView(context, request)

    This view has just one method, `calendar`, that invokes TermRenderer
    to give a nice structure of lists and dicts for the page template.

        >>> print_cal(view.calendar())
        *                        August 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 31:                           1
        Week 32:   2   3   4   5   6   7   8
        Week 33:   9  10  11  12  13  14  15
        Week 34:  16  17  18  19  20  21  22
        Week 35:  23  24  25  26  27  28  29
        Week 36:  30  31

    """


def doctest_TermEditView_title():
    """Unit tests for TermEditView.title

        >>> from schooltool.timetable import Term
        >>> from schooltool.timetable.browser import TermEditView
        >>> context = Term('Sample', datetime.date(2004, 8, 1),
        ...                        datetime.date(2004, 8, 31))
        >>> request = TestRequest()
        >>> view = TermEditView(context, request)

    view.title returns a Zope 3 I18N Message ID.

        >>> view.title()
        u'Change Term: $title'
        >>> translate(view.title())
        u'Change Term: Sample'

    """


def doctest_TermEditView_calendar():
    """Unit tests for TermEditView.calendar

        >>> from schooltool.timetable import Term
        >>> from schooltool.timetable.browser import TermEditView
        >>> context = Term('Sample', datetime.date(2004, 8, 4),
        ...                        datetime.date(2004, 8, 6))
        >>> request = TestRequest()
        >>> view = TermEditView(context, request)

    view.calendar() always renders view.term

        >>> view.term = Term('Sample', datetime.date(2004, 8, 1),
        ...                          datetime.date(2004, 8, 12))
        >>> print_cal(view.calendar())
        *                        August 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 31:                           1
        Week 32:   2   3   4   5   6   7   8
        Week 33:   9  10  11  12

    """


def doctest_TermEditView_update():
    """Unit tests for TermEditView.update

        >>> from schooltool.timetable import Term
        >>> from schooltool.timetable.browser import TermEditView
        >>> context = Term('Sample', datetime.date(2004, 8, 4),
        ...                        datetime.date(2004, 8, 6))
        >>> request = TestRequest()
        >>> view = TermEditView(context, request)

    When there are no dates in the request, or when the dates are not valid,
    view.update() sets self.term to self.context (so that the unchanged
    term calendar is then rendered by view.calendar()).  It also sets
    update_status.

        >>> view.update()
        ''
        >>> view.update_status
        ''
        >>> view.term is view.context
        True

    If you call view.update again, it will notice that update_status is
    set and do nothing.

        >>> request.form['field.title'] = 'Sample'
        >>> request.form['field.first'] = '2005-08-01'
        >>> request.form['field.last'] = '2005-08-05'
        >>> view.update()
        ''
        >>> view.term is view.context
        True

    However if you reset update_status back to None, update will 

        >>> view.update_status = None
        >>> view.update()
        ''
        >>> view.term is view.context
        False
        >>> view.term.first
        datetime.date(2005, 8, 1)
        >>> view.term.last
        datetime.date(2005, 8, 5)

    If UPDATE_SUBMIT appears in the request, update changes view.context
    and sends an ObjectModifiedEvent.

        >>> import zope.event
        >>> from zope.app.event.interfaces import IObjectModifiedEvent
        >>> old_subscribers = zope.event.subscribers[:]
        >>> def modified_handler(event):
        ...     if IObjectModifiedEvent.providedBy(event):
        ...         print "*** Object modified ***"
        >>> zope.event.subscribers.append(modified_handler)

        >>> request.form['UPDATE_SUBMIT'] = 'Save'
        >>> request.form['holiday'] = '2005-08-03'
        >>> view.update_status = None
        >>> view.update()
        *** Object modified ***
        u'Saved changes.'
        >>> context.first
        datetime.date(2005, 8, 1)
        >>> context.last
        datetime.date(2005, 8, 5)
        >>> context.isSchoolday(datetime.date(2005, 8, 2))
        True
        >>> context.isSchoolday(datetime.date(2005, 8, 3))
        False

        >>> zope.event.subscribers[:] = old_subscribers

    """


def doctest_TermAddView_update():
    """Unit tests for TermAddView.update

    `update` sets view.term

        >>> from schooltool.timetable import TermContainer
        >>> from schooltool.timetable.browser import TermAddView
        >>> context = TermContainer()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)
        >>> view.update()
        >>> view.term is None
        True

        >>> request.form['field.title'] = 'Sample'
        >>> request.form['field.first'] = '2005-09-01'
        >>> request.form['field.last'] = '2005-10-15'
        >>> view.update()
        >>> view.term
        <...Term object at ...>

    """


def doctest_TermAddView_create():
    """Unit tests for TermAddView.create

    `create` either returns view.term (if it has been successfully built
    by `update` before), or raises a WidgetsError (because `_buildTerm`
    discovered an error in the form).

        >>> from schooltool.timetable import TermContainer
        >>> from schooltool.timetable.browser import TermAddView
        >>> context = TermContainer()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)

        >>> view.term = object()
        >>> view.create() is view.term
        True

        >>> view.term = None
        >>> view.create()
        Traceback (most recent call last):
          ...
        WidgetsError

    """


def doctest_TermAddView_add():
    r"""Unit tests for TermAddView.add

    `add` adds the term to the term service.

        >>> from schooltool.timetable import TermContainer
        >>> from schooltool.timetable import Term
        >>> from schooltool.timetable.browser import TermAddView
        >>> context = TermContainer()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)

        >>> term = Term('Sample', datetime.date(2005, 1, 1),
        ...                     datetime.date(2005, 12, 31))
        >>> view.add(term)

    The standard NameChooser adapter picks the name 'Term'.

        >>> print '\n'.join(context.keys())
        Term

        >>> context['Term'] is term
        True

    """


def doctest_TermAddView_create():
    """Unit tests for TermAddView.create

    `create` either returns view.term (if it has been successfully built
    by `update` before), or raises a WidgetsError (because `_buildTerm`
    discovered an error in the form).

        >>> from schooltool.timetable import TermContainer
        >>> from schooltool.timetable.browser import TermAddView
        >>> context = TermContainer()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)

        >>> view.term = object()
        >>> view.create() is view.term
        True

        >>> view.term = None
        >>> view.create()
        Traceback (most recent call last):
          ...
        WidgetsError

    """


def doctest_TermAddView_nextURL():
    """Unit tests for TermAddView.nextURL

    `nextURL` returns the absolute url of its context.

        >>> from schooltool.timetable import TermContainer
        >>> from schooltool.timetable.browser import TermAddView
        >>> context = TermContainer()
        >>> directlyProvides(context, IContainmentRoot)
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)
        >>> view.nextURL()
        'http://127.0.0.1'

    """


def doctest_TermEditViewMixin_buildTerm():
    """Unit tests for TermEditViewMixin._buildTerm

    We shall use TermAddView here -- it inherits TermEditViewMixin._buildTerm
    without changing it.

        >>> from schooltool.timetable import TermContainer
        >>> from schooltool.timetable.browser import TermAddView
        >>> context = TermContainer()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)

        >>> request.form['field.title'] = 'Sample'

    When there are no dates in the request, or when the dates are not valid,
    view._buildTerm() returns None.

        >>> view._buildTerm()

        >>> request.form['field.first'] = '2005-09-01'
        >>> request.form['field.last'] = 'not a clue'
        >>> view._buildTerm()

        >>> request.form['field.first'] = 'bogus'
        >>> request.form['field.last'] = '2005-12-31'
        >>> view._buildTerm()

        >>> request.form['field.first'] = '2005-12-31'
        >>> request.form['field.last'] = '2005-09-01'
        >>> view._buildTerm()

    If the dates are valid, but the interval is not, you get None again.

        >>> request.form['field.first'] = '2005-09-02'
        >>> request.form['field.last'] = '2005-09-01'
        >>> view._buildTerm()

    When the dates describe a valid non-empty inclusive time interval,
    view._buildTerm() returns a Term object.

        >>> request.form['field.first'] = '2005-09-01'
        >>> request.form['field.last'] = '2005-10-15'
        >>> term = view._buildTerm()
        >>> term.first
        datetime.date(2005, 9, 1)
        >>> term.last
        datetime.date(2005, 10, 15)
        >>> term.title
        u'Sample'

    When there are no indication about schooldays or holidays in the request,
    all days are marked as schooldays.

        >>> def print_holidays(term):
        ...     all = True
        ...     for day in term:
        ...         if not term.isSchoolday(day):
        ...             print "%s is a holiday" % day
        ...             all = False
        ...     if all:
        ...         print "All days are schooldays."

        >>> print_holidays(term)
        All days are schooldays.

        >>> request.form['holiday'] = u'2005-09-07'
        >>> term = view._buildTerm()
        >>> print_holidays(term)
        2005-09-07 is a holiday

        >>> request.form['holiday'] = [u'2005-10-02', u'2005-09-07']
        >>> term = view._buildTerm()
        >>> print_holidays(term)
        2005-09-07 is a holiday
        2005-10-02 is a holiday

    Ill-formed or out-of-range dates are just ignored

        >>> request.form['holiday'] = [u'2005-10-17', u'2005-09-07', u'foo!']
        >>> term = view._buildTerm()
        >>> print_holidays(term)
        2005-09-07 is a holiday

    The presence of 'TOGGLE_n' (where n is 0..6) in the request requests the
    state of corresponding weekdays (0 = Monday, 6 = Sunday) to be toggled.

        >>> request.form['holiday'] = [u'2005-10-02', u'2005-09-07']
        >>> request.form['TOGGLE_0'] = [u'Monday']
        >>> request.form['TOGGLE_6'] = [u'Sunday']
        >>> term = view._buildTerm()
        >>> print_holidays(term)
        2005-09-04 is a holiday
        2005-09-05 is a holiday
        2005-09-07 is a holiday
        2005-09-11 is a holiday
        2005-09-12 is a holiday
        2005-09-18 is a holiday
        2005-09-19 is a holiday
        2005-09-25 is a holiday
        2005-09-26 is a holiday
        2005-10-03 is a holiday
        2005-10-09 is a holiday
        2005-10-10 is a holiday

    """


def doctest_TermAddView_calendar():
    """Unit tests for TermAddView.calendar

        >>> from schooltool.timetable import TermContainer
        >>> from schooltool.timetable.browser import TermAddView
        >>> context = TermContainer()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)

    When there are no dates in the request, or when the dates are not valid,
    view.caledar() returns None

        >>> view.term = view._buildTerm()
        >>> view.calendar()

        >>> request.form['field.first'] = '2005-09-01'
        >>> request.form['field.last'] = 'not a clue'
        >>> view.term = view._buildTerm()
        >>> view.calendar()

        >>> request.form['field.first'] = 'bogus'
        >>> request.form['field.last'] = '2005-12-31'
        >>> view.term = view._buildTerm()
        >>> view.calendar()

        >>> request.form['field.first'] = '2005-12-31'
        >>> request.form['field.last'] = '2005-09-01'
        >>> view.term = view._buildTerm()
        >>> view.calendar()

        >>> request.form['field.first'] = '2005-09-02'
        >>> request.form['field.last'] = '2005-09-01'
        >>> view.term = view._buildTerm()
        >>> view.calendar()

    When the dates describe a valid non-empty inclusive time interval,
    view.calendar() returns a list of dicts, one for each month.

        >>> request.form['field.title'] = 'Sample'
        >>> request.form['field.first'] = '2004-08-01'
        >>> request.form['field.last'] = '2004-08-31'
        >>> view.term = view._buildTerm()
        >>> print_cal(view.calendar())
        *                        August 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 31:                           1
        Week 32:   2   3   4   5   6   7   8
        Week 33:   9  10  11  12  13  14  15
        Week 34:  16  17  18  19  20  21  22
        Week 35:  23  24  25  26  27  28  29
        Week 36:  30  31

    """


def doctest_TermRenderer_calendar():
    """Unit tests for TermRenderer.calendar

        >>> from schooltool.timetable import Term
        >>> from schooltool.timetable.browser import TermRenderer

        >>> term = Term('Sample', datetime.date(2004, 8, 1),
        ...                     datetime.date(2004, 8, 31))
        >>> print_cal(TermRenderer(term).calendar())
        *                        August 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 31:                           1
        Week 32:   2   3   4   5   6   7   8
        Week 33:   9  10  11  12  13  14  15
        Week 34:  16  17  18  19  20  21  22
        Week 35:  23  24  25  26  27  28  29
        Week 36:  30  31

        >>> term = Term('Sample', datetime.date(2004, 8, 2),
        ...                     datetime.date(2004, 9, 1))
        >>> print_cal(TermRenderer(term).calendar())
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

        >>> term = Term('Sample', datetime.date(2004, 8, 3),
        ...                     datetime.date(2004, 8, 3))
        >>> print_cal(TermRenderer(term).calendar())
        *                        August 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 32:       3

        >>> term = Term('Sample', datetime.date(2004, 12, 30),
        ...                     datetime.date(2005, 1, 3))
        >>> print_cal(TermRenderer(term).calendar())
        *                      December 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 53:              30  31
        *                       January 2005
                 Mon Tue Wed Thu Fri Sat Sun
        Week 53:                       1   2
        Week 1 :   3

    Each day gets a numeric index, used in Javascript

        >>> term = Term('Sample', datetime.date(2004, 12, 30),
        ...                     datetime.date(2005, 1, 3))
        >>> print_cal(TermRenderer(term).calendar(), '%(index)3s')
        *                      December 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 53:               1   2
        *                       January 2005
                 Mon Tue Wed Thu Fri Sat Sun
        Week 53:                       3   4
        Week 1 :   5

    """


def doctest_TermRenderer_month():
    """Unit test for TermRenderer.month

        >>> from schooltool.timetable import Term
        >>> from schooltool.timetable.browser import TermRenderer
        >>> term = Term('Sample', datetime.date(2005, 1, 1),
        ...                     datetime.date(2005, 12, 31))
        >>> month = TermRenderer(term).month

    The month function goes through all weeks between mindate and maxdate.

        >>> def print_month(month, day_format='%(number)3d'):
        ...     title = '%s %d' % (month['month'], month['year'])
        ...     print '*%35s' % title
        ...     print '         Mon Tue Wed Thu Fri Sat Sun'
        ...     for week in month['weeks']:
        ...         s = ['Week %-2d:' % week['number']]
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


def doctest_TermRenderer_week():
    """Unit test for TermRenderer.week

        >>> from schooltool.timetable import Term
        >>> from schooltool.timetable.browser import TermRenderer
        >>> term = Term('Sample', datetime.date(2005, 5, 1),
        ...                     datetime.date(2005, 5, 31))
        >>> term.addWeekdays(0, 1, 2, 3, 4)
        >>> week = TermRenderer(term).week

    The week function is pretty simple.  First we will try to pass Monday
    as start_of_week.

        >>> def print_week(week):
        ...     print 'Week %d' % week['number']
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
        6 2005-05-07 7 True holiday javascript:toggle(6)
        7 2005-05-08 8 True holiday javascript:toggle(7)

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
        12 2005-05-07 7 True holiday javascript:toggle(12)
        13 2005-05-08 8 True holiday javascript:toggle(13)

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
        18 2005-05-01 1 True holiday javascript:toggle(18)
        19 2005-05-02 2 False schoolday javascript:toggle(19)
        20 2005-05-03 3 False schoolday javascript:toggle(20)
        21 2005-05-04 4 False schoolday javascript:toggle(21)
        22 2005-05-05 5 False schoolday javascript:toggle(22)
        23 2005-05-06 6 False schoolday javascript:toggle(23)
        24 2005-05-07 7 True holiday javascript:toggle(24)

    """


def print_cal(calendar, day_format='%(number)3d'):
    """Print a calendar as returned by TermRenderer.calendar."""
    for month in calendar:
        title = '%s %d' % (month['month'], month['year'])
        print '*%35s' % title
        print '         Mon Tue Wed Thu Fri Sat Sun'
        for week in month['weeks']:
            s = ['Week %-2d:' % week['number']]
            for day in week['days']:
                if day['number'] is None:
                    s.append('   ')
                else:
                    s.append(day_format % day)
            print ' '.join(s).rstrip()


def doctest_TimetableView():
    """Test for TimetableView.

        >>> from schooltool.timetable.browser import TimetableView
        >>> from schooltool.timetable import Timetable
        >>> from schooltool.timetable import TimetableDay, TimetableActivity
        >>> from schooltool.app import Section

    Create some context:

        >>> s = Section()
        >>> s.timetables['term.schema'] = tt = Timetable(['day 1'])
        >>> tt['day 1'] = ttd = TimetableDay(['A'])
        >>> ttd.add('A', TimetableActivity('Something'))

        >>> request = TestRequest()
        >>> view = TimetableView(tt, request)

    title() returns the view's title:

        >>> translate(view.title())
        u"Section\'s timetable"

    rows() delegates the job to format_timetable_for_presentation:

        >>> view.rows()
        [[{'period': 'A', 'activity': 'Something'}]]

    """


def doctest_TimetableSchemaView():
    """Test for TimetableView.

        >>> from schooltool.timetable.browser import TimetableSchemaView
        >>> from schooltool.timetable import TimetableSchema
        >>> from schooltool.timetable import TimetableSchemaDay
        >>> from schooltool.timetable import TimetableActivity

    Create some context:

        >>> tts = TimetableSchema(['day 1'])
        >>> tts.__name__ = 'some-schema'
        >>> tts['day 1'] = ttd = TimetableSchemaDay(['A'])

        >>> request = TestRequest()
        >>> view = TimetableSchemaView(tts, request)

    title() returns the view's title:

        >>> translate(view.title())
        u'Timetable schema some-schema'

    rows() delegates the job to format_timetable_for_presentation:

        >>> view.rows()
        [[{'period': 'A', 'activity': ''}]]

    """


class TestAdvancedTimetableSchemaAdd(NiceDiffsMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.app import SchoolToolApplication
        setUp()
        self.app = SchoolToolApplication()
        directlyProvides(self.app, IContainmentRoot)
        self.app.setSiteManager(LocalSiteManager(self.app))
        setSite(self.app)

        # Register the timetable models
        from schooltool.timetable import SequentialDaysTimetableModel
        from schooltool.timetable import WeeklyTimetableModel
        from schooltool.timetable.interfaces import ITimetableModelFactory
        ztapi.provideUtility(ITimetableModelFactory,
                             SequentialDaysTimetableModel,
                             'SequentialDaysTimetableModel')
        ztapi.provideUtility(ITimetableModelFactory,
                             WeeklyTimetableModel,
                             'WeeklyTimetableModel')
        from schooltool.timetable.interfaces import ITimetableSchemaContainer
        from schoolbell.app.app import SimpleNameChooser
        from zope.app.container.interfaces import INameChooser
        ztapi.provideAdapter(ITimetableSchemaContainer,
                             INameChooser,
                             SimpleNameChooser)
        from schooltool.tests import setUpApplicationPreferences
        setUpApplicationPreferences()

    def tearDown(self):
        tearDown()

    def createView(self, request=None):
        from schooltool.timetable.browser import AdvancedTimetableSchemaAdd
        context = self.app["ttschemas"]
        context['default'] = createSchema(['Day 1'], ['Period 1'])
        if request is None:
            request = TestRequest()
        view = AdvancedTimetableSchemaAdd(context, request)
        return view

    def test(self):
        view = self.createView()
        result = view()
        self.assert_('name="field.title" size="20" type="text" value="default"'
                     in result)

    def test_with_data(self):
        request = TestRequest(form={'day1': 'Monday',
                                    'field.title': 'something',
                                    'model': 'SequentialDaysTimetableModel',
                                    'time1.period': 'Period 1',
                                    'time1.day0': '9:00-9:45',
                                    })
        view = self.createView(request)
        result = view()
        self.assertEquals(view.ttschema,
                          createSchema(['Monday'], ['Period 1']))
        self.assert_('value="something"' in result, result)
        self.assertEquals(view.title_widget.error(), '')
        self.assertEquals(view.model_name, 'SequentialDaysTimetableModel')
        self.assertEquals(view.model_error, None)
        self.assertEquals(view.day_templates,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45)])})

    def test_creation(self):
        request = TestRequest(form={'day1': 'Monday',
                                    'field.title': 'some.thing',
                                    'model': 'SequentialDaysTimetableModel',
                                    'time1.period': 'Period 1',
                                    'time1.day0': '9:00-9:45',
                                    'CREATE': 'Create', })
        view = self.createView(request)
        result = view()
        self.assertEquals(view.model_error, None)
        self.assertEquals(request.response.getStatus(), 302)
        self.assertEquals(request.response.getHeader('location'),
                          'http://127.0.0.1/ttschemas')
        schema = view.context['something']
        self.assertEquals(schema, view.ttschema)
        self.assertEquals(schema.model.timetableDayIds, view.ttschema.keys())
        self.assertEquals(schema.model.dayTemplates, view.day_templates)

    def test_model_error(self):
        request = TestRequest(form={'model': 'xxx',
                                    'CREATE': 'Create'})
        view = self.createView(request)
        view()
        self.assertEquals(view.model_error, "Please select a value")

    def test_model_error_ignored_unless_this_is_the_final_submit(self):
        view = self.createView(TestRequest(form={'field.title': 'Schema',
                                                 'model': 'xxx'}))
        view()
        self.assertEquals(view.model_error, None)

    def test_buildDayTemplates_empty(self):
        view = self.createView()
        dt = view._buildDayTemplates()
        self.assertEquals(dt, {None: createDayTemplate([])})

    def test_buildDayTemplates_simple(self):
        request = TestRequest(form={
            'time1.period': 'Period 1',
            'time1.day0': '9:00',
            'time2.period': 'Period 2',
            'time2.day0': '10:00-10:45',
            'time2.day6': '10:30-11:10',
            'field.duration': '45'})
        view = self.createView(request)
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)]),
                           6: createDayTemplate([('Period 2', 10, 30, 40)])})
        self.assert_(not view.discarded_some_periods)

    def test_buildDayTemplates_copy_day(self):
        request = TestRequest(form={'time1.period': 'Period 1',
                                     'time1.day0': '9:00-9:45',
                                     'time1.day1': '13:00-13:45',
                                     'time2.period': 'Period 2',
                                     'time2.day0': '10:00-10:45',
                                     'time2.day6': '10:30-11:10',
                                     'COPY_PERIODS_1': 'C'})
        view = self.createView(request)
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)]),
                           1: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)]),
                           6: createDayTemplate([('Period 2', 10, 30, 40)])})

    def test_buildDayTemplates_copy_empty_day(self):
        request = TestRequest(form={
            'time1.period': 'Period 1',
            'time1.day0': '9:00-9:45',
            'time2.period': 'Period 2',
            'time2.day0': '10:00-10:45',
            'time2.day6': '10:30-11:10',
            'COPY_PERIODS_6': 'C'})
        view = self.createView(request)
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)])})

    def test_buildDayTemplates_copy_empty_day_over_empty_day(self):
        request = TestRequest(form={
            'time1.period': 'Period 1',
            'time1.day0': '9:00-9:45',
            'time2.period': 'Period 2',
            'time2.day0': '10:00-10:45',
            'time2.day6': '10:30-11:10',
            'COPY_PERIODS_4': 'C'})
        view = self.createView(request)
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)]),
                           6: createDayTemplate([('Period 2', 10, 30, 40)])})

    def test_buildDayTemplates_copy_first_day_ignored(self):
        request = TestRequest(form={
            'time1.period': 'Period 1',
            'time1.day0': '9:00-9:45',
            'time2.period': 'Period 2',
            'time2.day0': '10:00-10:45',
            'time2.day6': '10:30-11:10',
            'COPY_PERIODS_0': 'C'})
        view = self.createView(request)
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)]),
                           6: createDayTemplate([('Period 2', 10, 30, 40)])})

    def test_buildDayTemplates_errors(self):
        request = TestRequest(form={
            'time1.period': 'Period 1',
            'time1.day0': 'foo',
            # When duration_widget.value is None, both endpoints are required
            'time1.day1': '9:00'
            })
        view = self.createView(request)
        dt = view._buildDayTemplates()
        self.assertEquals(dt, {None: createDayTemplate([])})
        self.assert_(view.discarded_some_periods)

    def test_buildSchema_empty(self):
        view = self.createView()
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1'], ['Period 1']))

    def test_buildSchema_from_request(self):
        request = TestRequest(form={
            'day1': 'Monday',
            'day2': ' Tuesday ',
            'day1.period1': 'A',
            'day1.period2': ' B ',
            'day2.period1': 'C',
            'day2.period2': ''})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Tuesday'],
                                               ['A', 'B'], ['C']))

    def test_buildSchema_empty_day(self):
        request = TestRequest(form={
            'day1': 'Monday',
            'day2': 'Tuesday',
            'day1.period1': 'A',
            'day1.period2': 'B',
            'day2.period1': '',
            'day2.period2': ''})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Tuesday'],
                                               ['A', 'B'], ['Period 1']))

    def test_buildSchema_repeated_day_name(self):
        request = TestRequest(form={
            'day1': 'D',
            'day2': 'D',
            'day3': 'D',
            'day1.period1': 'A',
            'day2.period1': 'B',
            'day3.period1': 'C'})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['D', 'D (2)', 'D (3)'],
                                               ['A'], ['B'], ['C']))

    def test_buildSchema_repeated_period_nam(self):
        request = TestRequest(form={
            'day1': 'D',
            'day1.period1': 'A',
            'day1.period2': 'A'})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['D'], ['A', 'A (2)']))

    def test_buildSchema_add_day(self):
        request = TestRequest(form={
            'day1': 'Monday',
            'ADD_DAY': "Add"})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Day 2'],
                                               ['Period 1'], ['Period 1']))

    def test_buildSchema_add_period(self):
        request = TestRequest(form={
            'day1': 'Monday',
            'day2': 'Tuesday',
            'day1.period1': 'A',
            'day1.period2': 'B',
            'day2.period1': 'C',
            'day2.period2': '',
            'ADD_PERIOD': "Add"})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Tuesday'],
                                               ['A', 'B', 'Period 3'], ['C']))

    def test_buildSchema_add_period_not_first_day(self):
        request = TestRequest(form={
            'day1': 'Monday',
            'day2': 'Tuesday',
            'day1.period1': 'A',
            'day2.period1': 'C',
            'day2.period2': 'D',
            'ADD_PERIOD': "Add"})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Tuesday'],
                                               ['A'], ['C', 'D', 'Period 3']))

    def test_buildSchema_delete_day(self):
        request = TestRequest(form={
            'day1': 'Day 1',
            'day2': 'Day 1',
            'day1.period1': 'A',
            'day1.period2': 'B',
            'day2.period1': 'C',
            'day2.period2': 'D',
            'DELETE_DAY_1': "Delete"})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1'], ['C', 'D']))

    def test_buildSchema_copy_day(self):
        request = TestRequest(form={
            'day1': 'Day 1',
            'day2': 'Day 2',
            'day1.period1': 'A',
            'day1.period2': 'B',
            'day2.period1': 'C',
            'day2.period2': 'D',
            'COPY_DAY_1': "Copy"})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1', 'Day 2'],
                                               ['A', 'B'], ['A', 'B']))

    def test_buildSchema_copy_first_day_ignored(self):
        request = TestRequest(form={
            'day1': 'Day 1',
            'day2': 'Day 2',
            'day1.period1': 'A',
            'day1.period2': 'B',
            'day2.period1': 'C',
            'day2.period2': 'D',
            'COPY_DAY_0': "Copy"})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1', 'Day 2'],
                                               ['A', 'B'], ['C', 'D']))

    def test_all_periods(self):
        view = self.createView()
        view.ttschema = createSchema(['Day 1', 'Day 2', 'Day 3'],
                                     ['A', 'C'], ['B', 'D'], ['A', 'F'])
        self.assertEquals(view.all_periods(), ['A', 'C', 'B', 'D', 'F'])

    def test_period_times(self):
        view = self.createView()
        view.ttschema = createSchema(['Day 1', 'Day 2', 'Day 3'],
                                     ['A', 'C'], ['B', 'D'], ['A', 'F'])
        view.day_templates = {}
        titles = [p['title'] for p in view.period_times()]
        self.assertEquals(titles, ['A', 'C', 'B', 'D', 'F'])
        for p in view.period_times():
            self.assertEquals(p['times'], 7 * [None])

    def test_period_times_with_data(self):
        view = self.createView()
        view.ttschema = createSchema(['Day 1', 'Day 2', 'Day 3'],
                                     ['A', 'C'], ['B', 'D'], ['A', 'F'])
        view.day_templates = {0: createDayTemplate([('A', 9, 0, 45),
                                                    ('F', 10, 30, 40),
                                                    ('X', 11, 22, 33)]),
                              6: createDayTemplate([('A', 8, 55, 45),
                                                    ('D', 0, 0, 24*60)])}
        times = view.period_times()
        titles = [p['title'] for p in times]
        self.assertEquals(titles, ['A', 'C', 'B', 'D', 'F'])
        self.assertEquals(times[0]['times'], ['09:00-09:45', None, None, None,
                                              None, None, '08:55-09:40'])  # A
        self.assertEquals(times[1]['times'], [None] * 7)                   # C
        self.assertEquals(times[2]['times'], [None] * 7)                   # B
        self.assertEquals(times[3]['times'], [None] * 6 + ['00:00-24:00']) # D
        self.assertEquals(times[4]['times'], ['10:30-11:10'] + [None] * 6) # F


def doctest_SimpleTimetableSchemaAdd():
    r"""Doctest for the SimpleTimetableSchemaAdd view

        >>> from schooltool.tests import setUpApplicationPreferences
        >>> setUpApplicationPreferences()

        >>> from schooltool.timetable import WeeklyTimetableModel
        >>> from schooltool.timetable.interfaces import ITimetableModelFactory
        >>> ztapi.provideUtility(ITimetableModelFactory,
        ...                      WeeklyTimetableModel,
        ...                      'WeeklyTimetableModel')
        >>> from schooltool.timetable.interfaces import \
        ...                           ITimetableSchemaContainer
        >>> from schoolbell.app.app import SimpleNameChooser
        >>> from zope.app.container.interfaces import INameChooser
        >>> ztapi.provideAdapter(ITimetableSchemaContainer,
        ...                      INameChooser,
        ...                      SimpleNameChooser)

    Suppose we have a SchoolTool instance, and create a view for its
    timetable schemas container:

        >>> from schooltool.app import SchoolToolApplication
        >>> from schooltool.timetable.browser import SimpleTimetableSchemaAdd
        >>> app = SchoolToolApplication()
        >>> directlyProvides(app, IContainmentRoot)
        >>> app.setSiteManager(LocalSiteManager(app))
        >>> setSite(app)
        >>> request = TestRequest()
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)

    Let's render it.  There is a widget for title there:

        >>> print view()
        <BLANKLINE>
        ...
                  <div class="field"><input class="textType"
                             id="field.title"
                             name="field.title" size="20" type="text"
                             value="default"  /></div>
        ...
          <tr>
            <th>
              <div><input class="textType" id="field.period_name_1"
                          name="field.period_name_1" size="20" type="text"
                          value=""  /></div>
            </th>
            <th>
              <div><input class="textType" id="field.period_start_1"
                          name="field.period_start_1" size="20"
                          type="text" value="" /></div>
            </th>
            <th>
              <div><input class="textType" id="field.period_finish_1"
                          name="field.period_finish_1" size="20"
                          type="text" value="" /></div>
            </th>
          </tr>
        ...

    getPeriods returns None, as the form is not yet filled:

        >>> view.getPeriods()
        []

    Now, let's create a simple case with all the fields filled:

        >>> request = TestRequest(form={'field.title': 'default',
        ...                             'field.period_name_1': 'Period 1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '9:45',
        ...                             'field.period_name_2': 'Period 2',
        ...                             'field.period_start_2': '10:00',
        ...                             'field.period_finish_2': '10:45',
        ...                             'field.period_name_3': '',
        ...                             'field.period_name_4': '',
        ...                             'CREATE': 'Go'
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)

    getPeriods should extract a list of periods:

        >>> pprint(view.getPeriods())
        [(u'Period 1',
          datetime.time(9, 0),
          datetime.timedelta(0, 2700)),
         (u'Period 2',
          datetime.time(10, 0),
          datetime.timedelta(0, 2700))]

    If we call the view, a new timetable schema is created:

        >>> result = view()
        >>> list(view.context.keys())
        [u'default']
        >>> schema = view.context['default']
        >>> print " ".join(schema.day_ids)
        Monday Tuesday Wednesday Thursday Friday
        >>> print ", ".join(schema['Monday'].periods)
        Period 1, Period 2

    All days are the same

        >>> for day_id, day in schema.items():
        ...     assert day == schema['Monday']

    The schema uses the weekly timetable model

        >>> print schema.model.__class__.__name__
        WeeklyTimetableModel
        >>> print " ".join(schema.model.timetableDayIds)
        Monday Tuesday Wednesday Thursday Friday
        >>> for period in schema.model.dayTemplates[None]:
        ...     print period.title, period.tstart, period.duration
        Period 1 09:00:00 0:45:00
        Period 2 10:00:00 0:45:00

    We should get redirected to the ttschemas index:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/ttschemas'

    If period names are not provided, use start times:

        >>> request = TestRequest(form={'field.title': 'default',
        ...                             'field.period_name_1': '',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '9:45',
        ...                             'field.period_name_2': '',
        ...                             'field.period_start_2': '10:00',
        ...                             'field.period_finish_2': '10:45',
        ...                             'CREATE': 'Go'
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)

        >>> pprint(view.getPeriods())
        [(u'9:00',
          datetime.time(9, 0),
          datetime.timedelta(0, 2700)),
         (u'10:00',
          datetime.time(10, 0),
          datetime.timedelta(0, 2700))]

    If a cancel button is pressed, nothing is done and the user is
    redirected to ttschemas index:

        >>> request = TestRequest(form={'field.title': 'default2',
        ...                             'field.period_name_1': 'Period 1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '9:45',
        ...                             'field.period_name_2': 'Period 2',
        ...                             'field.period_start_2': '10:00',
        ...                             'field.period_finish_2': '10:45',
        ...                             'field.period_name_3': '',
        ...                             'field.period_name_4': '',
        ...                             'CANCEL': 'Cancel'
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)
        >>> result = view()
        >>> list(view.context.keys())
        [u'default']

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/ttschemas'

    If there's a period skipped in a form, consequent periods are not included:

        >>> request = TestRequest(form={'field.title': 'default',
        ...                             'field.period_name_1': 'Period 1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '9:45',
        ...                             'field.period_name_3': 'Period 2',
        ...                             'field.period_start_3': '10:00',
        ...                             'field.period_finish_3': '10:45',
        ...                             'field.period_name_4': '',
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)
        >>> view.getPeriods()
        [(u'Period 1',
          datetime.time(9, 0),
          datetime.timedelta(0, 2700)),
         (u'Period 2',
          datetime.time(10, 0),
          datetime.timedelta(0, 2700))]

    If a period does not have a start time or end time specified, it
    is skipped:

        >>> request = TestRequest(form={'field.title': 'default',
        ...                             'field.period_name_1': 'Period 1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '9:45',
        ...                             'field.period_name_2': 'Period 2',
        ...                             'field.period_start_2': '',
        ...                             'field.period_finish_2': '10:45',
        ...                             'field.period_name_3': 'Period 3',
        ...                             'field.period_start_3': '11:00',
        ...                             'field.period_finish_3': '',
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)
        >>> view.getPeriods()
        [(u'Period 1',
          datetime.time(9, 0),
          datetime.timedelta(0, 2700))]

    Incorrect start and end times are handled gracefully:

        >>> request = TestRequest(form={'field.title': 'default',
        ...                             'field.period_name_1': 'Period 1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '9:45',
        ...                             'field.period_name_2': '',
        ...                             'field.period_start_2': '10h',
        ...                             'field.period_finish_2': '',
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)

    getPeriods fails:

        >>> view.getPeriods()
        [(u'Period 1', datetime.time(9, 0), datetime.timedelta(0, 2700))]

    The widgets responsible get an error set on them:

        >>> print view()
        <BLANKLINE>
        ...
            <div class="error">Please use HH:MM format for period start
                               and end times</div>
        ...

        >>> request.response.getStatus() != 302
        True


   One can provide the same title more than once (thought it is not
   advised to do so):

        >>> request = TestRequest(form={
        ...                             'field.title': 'already',
        ...                             'field.period_name_1': 'p1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '10:00',
        ...                             'CREATE': 'Create'
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)
        >>> from schooltool.timetable import TimetableSchema
        >>> app['ttschemas']['already'] = TimetableSchema([])
        >>> result = view()
        >>> request.response.getStatus() == 302
        True
        >>> 'already-2' in app['ttschemas']
        True

    """


def doctest_SimpleTimetableSchemaAdd_errors():
    """Doctest for the SimpleTimetableSchemaAdd view

        >>> from schooltool.tests import setUpApplicationPreferences
        >>> setUpApplicationPreferences()

        >>> from schooltool.timetable import WeeklyTimetableModel
        >>> from schooltool.timetable.interfaces import ITimetableModelFactory
        >>> ztapi.provideUtility(ITimetableModelFactory,
        ...                      WeeklyTimetableModel,
        ...                      'WeeklyTimetableModel')

    Suppose we have a SchoolTool instance, and create a view for its
    timetable schemas container:

        >>> from schooltool.app import SchoolToolApplication
        >>> from schooltool.timetable.browser import SimpleTimetableSchemaAdd
        >>> app = SchoolToolApplication()
        >>> directlyProvides(app, IContainmentRoot)
        >>> app.setSiteManager(LocalSiteManager(app))
        >>> setSite(app)

    No name specified:

        >>> request = TestRequest(form={
        ...                             'field.title': '',
        ...                             'field.period_name_1': 'p1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '10:00',
        ...                             'CREATE': 'Create'
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)
        >>> print view()
        <BLANKLINE>
        ...
                 <div class="label">
                    <label for="field.title" title="">Title</label>
                  </div>
                  <span class="error">Required input is missing.</span>
                  <div class="field"><input class="textType" id="field.title"
                                            name="field.title" size="20"
                                            type="text" value=""  /></div>
        ...
          <tr>
            <th>
              <div><input class="textType" id="field.period_name_1"
                          name="field.period_name_1" size="20" type="text"
                          value="p1"  /></div>
            </th>
            <th>
              <div><input class="textType" id="field.period_start_1"
                          name="field.period_start_1" size="20"
                          type="text" value="9:00" /></div>
            </th>
            <th>
              <div><input class="textType" id="field.period_finish_1"
                          name="field.period_finish_1" size="20"
                          type="text" value="10:00" /></div>
            </th>
          </tr>
        ...

        >>> request.response.getStatus() != 302
        True

    No periods:

        >>> request = TestRequest(form={
        ...                             'field.title': 'empty',
        ...                             'field.period_name_1': '',
        ...                             'field.period_start_1': '',
        ...                             'field.period_finish_1': '',
        ...                             'CREATE': 'Create'
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)
        >>> print view()
        <BLANKLINE>
        ...
            <div class="error">You must specify at least one period.</div>
        ...
                  <div class="label">
                    <label for="field.title" title="">Title</label>
                  </div>
                  <div class="field"><input class="textType" id="field.title"
                                            name="field.title" size="20"
                                            type="text" value="empty"
                                            /></div>
        ...

        >>> request.response.getStatus() != 302
        True

    """


def doctest_PersonTimetableSetupView():
    """Doctest for the PersonTimetableSetupView view

    Setup the ApplicationPreferences adapter

        >>> from schooltool.tests import setUpApplicationPreferences
        >>> setUpApplicationPreferences()

    We will need an application object

        >>> from schooltool.app import SchoolToolApplication
        >>> app = SchoolToolApplication()
        >>> directlyProvides(app, IContainmentRoot)
        >>> app.setSiteManager(LocalSiteManager(app))
        >>> setSite(app)

    and a Person from that application

        >>> from schooltool.app import Person
        >>> context = Person("student", "Steven Udent")
        >>> app["persons"]["whatever"] = context

    We will need some sections

        >>> from schooltool.app import Section
        >>> app["sections"]["math"] = math = Section("Math")
        >>> app["sections"]["biology"] = biology = Section("Biology")
        >>> app["sections"]["physics"] = physics = Section("Physics")

    We will also need a timetable schema, and a term.  Two of each, in fact.

        >>> app["ttschemas"]["default"] = createSchema(["Mon", "Tue"],
        ...                                            ["9:00", "10:00"],
        ...                                            ["9:00", "10:00"])
        >>> app["ttschemas"]["other"] = createSchema([], [])

        >>> from schooltool.timetable import Term
        >>> app["terms"]["2005-spring"] = Term('2005 Spring',
        ...                                    datetime.date(2004, 2, 1),
        ...                                    datetime.date(2004, 6, 30))
        >>> app["terms"]["2005-fall"] = Term('2005 Fall',
        ...                                    datetime.date(2004, 9, 1),
        ...                                    datetime.date(2004, 12, 31))

    We can now create the view.

        >>> from schooltool.timetable.browser import PersonTimetableSetupView
        >>> request = TestRequest()
        >>> view = PersonTimetableSetupView(context, request)

    There are two helper methods, getSchema and getTerm, that extract the
    schema and term from the request, or pick suitable defaults.

        >>> view.getSchema() is app["ttschemas"].getDefault()
        True
        >>> request.form['ttschema'] = 'other'
        >>> view.getSchema() is app["ttschemas"]["other"]
        True
        >>> request.form['ttschema'] = 'default'
        >>> view.getSchema() is app["ttschemas"]["default"]
        True

    The default for a term is "the current term", or, if there's none, the next
    one.  Since this depends on today's date, we can't explicitly test it here.

        >>> (view.getTerm() is app["terms"]["2005-spring"] or
        ...  view.getTerm() is app["terms"]["2005-fall"])
        True
        >>> request.form['term'] = '2005-spring'
        >>> view.getTerm() is app["terms"]["2005-spring"]
        True
        >>> request.form['term'] = '2005-fall'
        >>> view.getTerm() is app["terms"]["2005-fall"]
        True

    sectionMap finds out which sections are scheduled in which timetable slots.

        >>> term = app["terms"]["2005-fall"]
        >>> ttschema = app["ttschemas"]["default"]
        >>> section_map = view.sectionMap(term, ttschema)

        >>> from zope.testing.doctestunit import pprint
        >>> pprint(section_map)
        {('Mon', '10:00'): Set([]),
         ('Mon', '9:00'): Set([]),
         ('Tue', '10:00'): Set([]),
         ('Tue', '9:00'): Set([])}

    It gets more interesting when sections actually have some scheduled
    activities:

        >>> from schooltool.timetable import TimetableActivity
        >>> ttkey = "2005-fall.default"
        >>> math.timetables[ttkey] = ttschema.createTimetable()
        >>> math.timetables[ttkey]['Tue'].add('10:00',
        ...                                   TimetableActivity('Math'))

        >>> section_map = view.sectionMap(term, ttschema)
        >>> pprint(section_map)
        {('Mon', '10:00'): Set([]),
         ('Mon', '9:00'): Set([]),
         ('Tue', '10:00'): Set([<schooltool.app.Section object at ...>]),
         ('Tue', '9:00'): Set([])}

    allSections simply takes a union of a number of sets containing sections.

        >>> from sets import Set
        >>> sections = view.allSections({1: Set([math]),
        ...                              2: Set([math, biology]),
        ...                              3: Set([])})
        >>> sections = [s.title for s in sections]
        >>> sections.sort()
        >>> sections
        ['Biology', 'Math']

    getDays does most of the work

        >>> def printDays(days):
        ...     for day in days:
        ...         print day['title']
        ...         for period in day['periods']:
        ...             sections = [s.title for s in period['sections']]
        ...             selected = [s and s.title or "none"
        ...                         for s in period['selected']]
        ...             print "%7s: [%s] [%s]" % (period['title'],
        ...                                       ', '.join(sections),
        ...                                       ', '.join(selected))

        >>> days = view.getDays(ttschema, section_map)
        >>> printDays(days)
        Mon
           9:00: [] [none]
          10:00: [] [none]
        Tue
           9:00: [] [none]
          10:00: [Math] [none]

        >>> math.members.add(context)

        >>> days = view.getDays(ttschema, section_map)
        >>> printDays(days)
        Mon
           9:00: [] [none]
          10:00: [] [none]
        Tue
           9:00: [] [none]
          10:00: [Math] [Math]

    And finally, __call__ ties everything together -- it processes the form and
    renders a page template.

        >>> print view()
        <BLANKLINE>
        ...
        <title> Scheduling for Steven Udent </title>
        ...
        <h1> Scheduling for Steven Udent </h1>
        ...
        <form class="plain" method="post" action="http://127.0.0.1">
        ...
            <label for="term">Term</label>
            <select id="term" name="term">
              <option value="2005-spring">2005 Spring</option>
              <option selected="selected" value="2005-fall">2005 Fall</option>
            </select>
            <label for="ttschema">Schema</label>
            <select id="ttschema" name="ttschema">
              <option selected="selected" value="default">default</option>
              <option value="other">other</option>
            </select>
        ...
        </form>
        <form class="plain" method="post" action="http://127.0.0.1">
          <input type="hidden" name="term" value="2005-fall" />
          <input type="hidden" name="ttschema" value="default" />
        ...
            <h2>Mon</h2>
        ...
                <th>9:00</th>
                <td>
                  <select name="sections:list">
                    <option value="" selected="selected">none</option>
                  </select>
        ...
            <h2>Tue</h2>
        ...
                <th>10:00</th>
                <td>
                  <select name="sections:list">
                    <option value="">none</option>
                    <option selected="selected" value="math"> -- </option>
                  </select>
        ...
        </form>
        ...

    If the form contains 'SAVE', the form gets processed.  Suppose we unselect
    Math

        >>> request.form['SAVE'] = 'Save'
        >>> request.form['sections'] = ['']
        >>> content = view()

        >>> context in math.members
        False

    If we select it back

        >>> request.form['SAVE'] = 'Save'
        >>> request.form['sections'] = ['math']
        >>> content = view()

        >>> context in math.members
        True

    """


def doctest_PersonTimetableSetupView_no_timetables():
    """Doctest for the PersonTimetableSetupView view

    What if there are no terms/timetable schemas?

    Setup the ApplicationPreferences adapter

        >>> from schooltool.tests import setUpApplicationPreferences
        >>> setUpApplicationPreferences()

    We will need an application object

        >>> from schooltool.app import SchoolToolApplication
        >>> app = SchoolToolApplication()
        >>> directlyProvides(app, IContainmentRoot)
        >>> app.setSiteManager(LocalSiteManager(app))
        >>> setSite(app)

    and a Person from that application

        >>> from schooltool.app import Person
        >>> context = Person("student", "Steven Udent")
        >>> app["persons"]["whatever"] = context

    We can now create the view.

        >>> from schooltool.timetable.browser import PersonTimetableSetupView
        >>> request = TestRequest()
        >>> view = PersonTimetableSetupView(context, request)

    What does __call__ do?

        >>> print view()
        <BLANKLINE>
        ...
        <title> Scheduling for Steven Udent </title>
        ...
        <h1> Scheduling for Steven Udent </h1>
        ...
        <p>There are no terms or timetable schemas defined.</p>
        ...

    """


def doctest_PersonTimetableSetupView_no_default_ttschema():
    """Doctest for the PersonTimetableSetupView view

    What if there is no default timetable schema?

    We will need an application object

        >>> from schooltool.app import SchoolToolApplication
        >>> app = SchoolToolApplication()
        >>> directlyProvides(app, IContainmentRoot)
        >>> app.setSiteManager(LocalSiteManager(app))
        >>> setSite(app)

    and a Person from that application

        >>> from schooltool.app import Person
        >>> context = Person("student", "Steven Udent")
        >>> app["persons"]["whatever"] = context

    There is one timetable schema, but it is not the default one.

        >>> app["ttschemas"]["default"] = createSchema(["Mon", "Tue"],
        ...                                            ["9:00", "10:00"],
        ...                                            ["9:00", "10:00"])
        >>> app["ttschemas"]["other"] = createSchema([], [])
        >>> del app["ttschemas"]["default"]
        >>> app["ttschemas"].default_id is None
        True

    We can now create the view.

        >>> from schooltool.timetable.browser import PersonTimetableSetupView
        >>> request = TestRequest()
        >>> view = PersonTimetableSetupView(context, request)

    What does getSchema return?

        >>> view.getSchema() is app["ttschemas"]["other"]
        True

    """


def doctest_TimetableSchemaContainerView():
    """A test for TimetableSchemaContainer view

    We will need an application:

        >>> from schooltool.app import SchoolToolApplication
        >>> app = SchoolToolApplication()

    Some timetable schemas:

        >>> from schooltool.timetable import TimetableSchema
        >>> app["ttschemas"]["schema1"] = TimetableSchema([])
        >>> app["ttschemas"]["schema2"] = TimetableSchema([])

    Let's create our view:

        >>> from schooltool.timetable.browser import TimetableSchemaContainerView
        >>> from zope.publisher.browser import TestRequest
        >>> view = TimetableSchemaContainerView(app["ttschemas"], TestRequest())

    The default ttschema id should be "schema1":

        >>> app["ttschemas"].default_id
        'schema1'

    If the view is submited without any data - the default ttschema
    should not change:

        >>> view.update()
        ''
        >>> app["ttschemas"].default_id
        'schema1'

    We can change the default schema:

        >>> view.request = TestRequest(form={
        ...                                  'ttschema': 'schema2',
        ...                                  'UPDATE_SUBMIT': 'Change'
        ...                                 })
        >>> view.update()
        ''
        >>> app["ttschemas"].default_id
        'schema2'

    We can set the default_id to none:

        >>> view.request = TestRequest(form={
        ...                                  'ttschema': '',
        ...                                  'UPDATE_SUBMIT': 'Change'
        ...                                 })
        >>> view.update()
        ''
        >>> app["ttschemas"].default_id is None
        True

    """


def doctest_SectionTimetableSetupView():
    """Doctest for the SectionTimetableSetupView view

    Setup the ApplicationPreferences adapter

        >>> from schooltool.tests import setUpApplicationPreferences
        >>> setUpApplicationPreferences()

    We will need an application object

        >>> from schooltool.app import SchoolToolApplication
        >>> app = SchoolToolApplication()
        >>> directlyProvides(app, IContainmentRoot)
        >>> app.setSiteManager(LocalSiteManager(app))
        >>> setSite(app)

    We will need a section

        >>> from schooltool.app import Section
        >>> app["sections"]["math"] = math = Section("Math")
        >>> math.timetables.keys()
        []

    We will also need a timetable schema, and a term.  Two of each, in fact.

        >>> app["ttschemas"]["default"] = createSchema(["Mon", "Tue"],
        ...                                            ["9:00", "10:00"],
        ...                                            ["9:00", "10:00"])
        >>> app["ttschemas"]["other"] = createSchema([], [])

        >>> from schooltool.timetable import Term
        >>> app["terms"]["2005-spring"] = Term('2005 Spring',
        ...                                    datetime.date(2004, 2, 1),
        ...                                    datetime.date(2004, 6, 30))
        >>> app["terms"]["2005-fall"] = Term('2005 Fall',
        ...                                    datetime.date(2004, 9, 1),
        ...                                    datetime.date(2004, 12, 31))

    We can now create the view to look at the Math timetable

        >>> from schooltool.timetable.browser import SectionTimetableSetupView
        >>> context = math
        >>> request = TestRequest()
        >>> view = SectionTimetableSetupView(context, request)

    We have getSchema from the Mixin class to get the schema from the request
    or choose a default.

        >>> view.getSchema() is app["ttschemas"].getDefault()
        True
        >>> request.form['ttschema'] = 'other'
        >>> view.getSchema() is app["ttschemas"]["other"]
        True
        >>> request.form['ttschema'] = 'default'
        >>> view.getSchema() is app["ttschemas"]["default"]
        True

    getTerms will give us a list of available terms from the request or a list
    with just the current term if we're working at a time not during any term.

    Without any terms in the request we get the output of getNextTermForDate
    today

        >>> import datetime
        >>> from schooltool.timetable import getNextTermForDate
        >>> getNextTermForDate(datetime.date.today()) in view.getTerms()
        True
        >>> len(view.getTerms())
        1

        >>> request.form['terms'] = ['2005-spring', '2005-fall']
        >>> [t.__name__ for t in view.getTerms()]
        [u'2005-spring', u'2005-fall']

        >>> request.form['terms'] = ['2005-spring']
        >>> [t.__name__ for t in view.getTerms()]
        [u'2005-spring']

        >>> request.form['terms'] = ['2005-fall']
        >>> [t.__name__ for t in view.getTerms()]
        [u'2005-fall']

    Single terms may be returned as a single string, rather than a list:

        >>> request.form['terms'] = '2005-spring'
        >>> [t.__name__ for t in view.getTerms()]
        [u'2005-spring']

    If we cancel the form, we get redirected to the section

        >>> request = TestRequest(form={'CANCEL': 'Cancel'})
        >>> view = SectionTimetableSetupView(context, request)
        >>> result = view()

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/sections/math'

    If we save the form, we're redirected to the timetable view for the schema
    that we just saved:

        >>> request = TestRequest(form={'SAVE': 'Save'})
        >>> view = SectionTimetableSetupView(context, request)
        >>> result = view()

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/sections/math/timetables/2005-fall.default'

    An empty save request will create an empty timetable:

        >>> math.timetables['2005-fall.default']
        <Timetable: ...>
        >>> math.timetables['2005-fall.default']['Mon'].items()
        [('9:00', Set([])), ('10:00', Set([]))]
        >>> math.timetables['2005-fall.default']['Tue'].items()
        [('9:00', Set([])), ('10:00', Set([]))]

    Let's add some scheduled classes:

        >>> request = TestRequest(form={'ttschema': 'default',
        ...                             'term': '2005-fall',
        ...                             'Mon.9:00':'ON',
        ...                             'Tue.9:00':'ON',
        ...                             'SAVE': 'Save'})

        >>> view = SectionTimetableSetupView(context, request)

    The first time we view the page all the events are off:

        >>> print view()
        ...
        <BLANKLINE>
        ...
                            id="Mon.9:00" value="Mon.9:00"
        ...
                            id="Mon.10:00" value="Mon.10:00"
        ...
                            id="Tue.9:00" value="Tue.9:00"
        ...
                            id="Tue.10:00" value="Tue.10:00"
        ...


    Now we have a schedule for our course:

        >>> math.timetables['2005-fall.default']['Mon']['9:00']
        Set([TimetableActivity('', ...
        >>> math.timetables['2005-fall.default']['Mon']['10:00']
        Set([])
        >>> math.timetables['2005-fall.default']['Tue']['9:00']
        Set([TimetableActivity('', ...
        >>> math.timetables['2005-fall.default']['Tue']['10:00']
        Set([])

        >>> request = TestRequest(form={'ttschema': 'default',
        ...                             'term': '2005-fall',
        ...                             'Mon.9:00':'ON',
        ...                             'SAVE': 'Save'})

    Since we don't have an update() method, we call the page again to see our
    last changes, all the periods that were 'ON' are now checked:

        >>> view = SectionTimetableSetupView(context, request)
        >>> print view()
        ...
        <BLANKLINE>
        ...
                            checked="checked" id="Mon.9:00"
        ...
                            id="Mon.10:00" value="Mon.10:00"
        ...
                            checked="checked" id="Tue.9:00"
        ...
                            id="Tue.10:00" value="Tue.10:00"
        ...

    To remove a period from our schedule we create a new save request without
    that period listed.

        >>> view = SectionTimetableSetupView(context, request)
        >>> print view()
        ...
        <BLANKLINE>
        ...
                            checked="checked" id="Mon.9:00"
        ...
                            id="Mon.10:00" value="Mon.10:00"
        ...
                            id="Tue.9:00" value="Tue.9:00"
        ...
                            id="Tue.10:00" value="Tue.10:00"
        ...

    Tuesday's Activity is no longer there:

        >>> math.timetables['2005-fall.default']['Tue']['9:00']
        Set([])


    """

def doctest_SpecialDayView():
    """SpecialDayView tests.

    Special days are days for which some periods are shortened or
    cancelled altogether.  Our view for that presents the
    administrator with a way to alter the schoolday template for this
    day.

    First of all, we need an app object:

        >>> from schooltool.tests import setUpApplicationPreferences
        >>> setUpApplicationPreferences()

        >>> from schooltool.app import SchoolToolApplication
        >>> app = SchoolToolApplication()
        >>> directlyProvides(app, IContainmentRoot)
        >>> app.setSiteManager(LocalSiteManager(app))
        >>> setSite(app)

    We have a timetable schema to put the view on:

        >>> from schooltool.timetable.browser import SpecialDayView
        >>> ttschema = createSchema(['Day 1', 'Day 2'],
        ...                         ['First',
        ...                          'Second',
        ...                          'Third',
        ...                          'Fourth'])
        >>> app['ttschemas']['usual'] = ttschema

    The schema has a model attribute:

        >>> from schooltool.timetable import SequentialDaysTimetableModel
        >>> default = createDayTemplate([('First', 9, 0, 45),
        ...                              ('Second', 10, 0, 45),
        ...                              ('Third', 11, 0, 45),
        ...                              ('Fourth', 12, 0, 45)])
        >>> ttschema.model = SequentialDaysTimetableModel(['Day 1', 'Day 2'],
        ...                                               {None: default})

    We will need a term:

        >>> from schooltool.timetable import Term
        >>> app["terms"]["2005-summer"] = Term('2005 summer',
        ...                                    datetime.date(2005, 6, 1),
        ...                                    datetime.date(2005, 8, 31))
        >>> app["terms"]["2005-summer"].addWeekdays(0, 1, 2, 3, 4)

    Now we can call the view.  First we get asked what day do we want
    to change:

        >>> request = TestRequest()
        >>> view = SpecialDayView(ttschema, request)
        >>> print view()
        <BLANKLINE>
        ...
          <p>
            Please enter the date when the periods need to be changed below.
          </p>
        <BLANKLINE>
          <div class="row">
            <label>Date</label>
            <input type="text" name="date" />
          </div>
        <BLANKLINE>
          <div class="controls">
            <input type="submit" class="button-ok" name="CHOOSE"
                   value="Proceed" />
            <input type="submit" class="button-cancel" name="CANCEL"
                   value="Cancel" />
          </div>
        ...

        >>> `view.template` == `view.select_template`
        True

    If we pass a correct date to the view, it gets set as an attribute:

        >>> request = TestRequest(form={'date': '2005-07-05'})
        >>> view = SpecialDayView(ttschema, request)
        >>> view.update()
        >>> view.date
        datetime.date(2005, 7, 5)
        >>> `view.template` == `view.form_template`
        True

    Our view now can get a list of period titles, start and end times:

        >>> pprint(view.getPeriods())
        [('First', '09:00', '09:45', '09:00', '09:45'),
         ('Second', '10:00', '10:45', '10:00', '10:45'),
         ('Third', '11:00', '11:45', '11:00', '11:45'),
         ('Fourth', '12:00', '12:45', '12:00', '12:45')]

    The user is taken to the next step.  He gets a table with period
    names and times, and fields for new start and end times:

        >>> print view()
        <BLANKLINE>
        ...
           <input type="hidden" name="date" value="2005-07-05" />
           <table>
             <tr>
               <th>Period title</th>
               <th>Original start</th>
               <th>Original end</th>
               <th>New start</th>
               <th>New end</th>
             </tr>
             <tr>
               <td>First</td>
               <td>09:00</td>
               <td>09:45</td>
               <td>
                 <input type="text" name="First_start" value="09:00" />
               </td>
               <td>
                 <input type="text" name="First_end" value="09:45" />
               </td>
             </tr>
             <tr>
               <td>Second</td>
               <td>10:00</td>
               <td>10:45</td>
               <td>
                 <input type="text" name="Second_start"
                        value="10:00" />
               </td>
               <td>
                 <input type="text" name="Second_end" value="10:45" />
               </td>
             </tr>
             <tr>
               <td>Third</td>
               <td>11:00</td>
               <td>11:45</td>
               <td>
                 <input type="text" name="Third_start" value="11:00" />
               </td>
               <td>
                 <input type="text" name="Third_end" value="11:45" />
               </td>
             </tr>
             <tr>
               <td>Fourth</td>
               <td>12:00</td>
               <td>12:45</td>
               <td>
                 <input type="text" name="Fourth_start"
                        value="12:00" />
               </td>
               <td>
                 <input type="text" name="Fourth_end" value="12:45" />
               </td>
             </tr>
           </table>
        ...
            <input type="submit" class="button-ok" name="SUBMIT"
                   value="Modify" />
        ...

    Now the user can fill in the form and create an exception template
    for this day.

        >>> request = TestRequest(form={'date': '2005-07-05',
        ...                             'SUBMIT': 'next',
        ...                             'First_start': '8:00',
        ...                             'First_end': '8:30',
        ...                             'Second_start': '8:45',
        ...                             'Second_end': '9:15',
        ...                             'Third_start': '9:30',
        ...                             'Third_end': '10:00',
        ...                             'Fourth_start': '',
        ...                             'Fourth_end': '',
        ...                             })
        >>> view = SpecialDayView(ttschema, request)
        >>> from datetime import time, date, timedelta
        >>> view.update()
        >>> pprint(view.extractPeriods())
        [('First', datetime.time(8, 0), datetime.timedelta(0, 1800)),
         ('Second', datetime.time(8, 45), datetime.timedelta(0, 1800)),
         ('Third', datetime.time(9, 30), datetime.timedelta(0, 1800))]

    The processing does not raise:

        >>> result = view()

    There are no field errors:

        >>> view.field_errors
        []

    The actual exception gets added:

        >>> exception = ttschema.model.exceptionDays[datetime.date(2005, 7, 5)]
        >>> exception
        <schooltool.timetable.SchooldayTemplate object at ...>
        >>> for period in exception:
        ...     print period.title, period.tstart, period.duration
        First 08:00:00 0:30:00
        Second 08:45:00 0:30:00
        Third 09:30:00 0:30:00

    The user is redirected to the schema main page:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/ttschemas/usual'

    If we revisit this date, we see the original times on the left,
    and the times of the exceptional template filled in in the form:

        >>> request = TestRequest(form={'date': '2005-07-05'})
        >>> view = SpecialDayView(ttschema, request)
        >>> print view()
        <BLANKLINE>
        ...
           <table>
             <tr>
               <th>Period title</th>
               <th>Original start</th>
               <th>Original end</th>
               <th>New start</th>
               <th>New end</th>
             </tr>
             <tr>
               <td>First</td>
               <td>09:00</td>
               <td>09:45</td>
               <td>
                 <input type="text" name="First_start" value="08:00" />
               </td>
               <td>
                 <input type="text" name="First_end" value="08:30" />
               </td>
             </tr>
             <tr>
               <td>Second</td>
               <td>10:00</td>
               <td>10:45</td>
               <td>
                 <input type="text" name="Second_start" value="08:45" />
               </td>
               <td>
                 <input type="text" name="Second_end" value="09:15" />
               </td>
             </tr>
             <tr>
               <td>Third</td>
               <td>11:00</td>
               <td>11:45</td>
               <td>
                 <input type="text" name="Third_start" value="09:30" />
               </td>
               <td>
                 <input type="text" name="Third_end" value="10:00" />
               </td>
             </tr>
             <tr>
               <td>Fourth</td>
               <td>12:00</td>
               <td>12:45</td>
               <td>
                 <input type="text" name="Fourth_start" value="" />
               </td>
               <td>
                 <input type="text" name="Fourth_end" value="" />
               </td>
             </tr>
           </table>
        ...
            <input type="submit" class="button-ok" name="SUBMIT"
                   value="Modify" />
        ...

    The disabled periods can be reenabled:

        >>> request = TestRequest(form={'date': '2005-07-05',
        ...                             'SUBMIT': 'next',
        ...                             'First_start': '8:00',
        ...                             'First_end': '8:30',
        ...                             'Second_start': '8:45',
        ...                             'Second_end': '9:15',
        ...                             'Third_start': '9:30',
        ...                             'Third_end': '10:00',
        ...                             'Fourth_start': '11:00',
        ...                             'Fourth_end': '12:00',
        ...                             })
        >>> view = SpecialDayView(ttschema, request)
        >>> from datetime import time, date, timedelta
        >>> view.update()
        >>> pprint(view.extractPeriods())
        [('First', datetime.time(8, 0), datetime.timedelta(0, 1800)),
         ('Second', datetime.time(8, 45), datetime.timedelta(0, 1800)),
         ('Third', datetime.time(9, 30), datetime.timedelta(0, 1800)),
         ('Fourth', datetime.time(11, 0), datetime.timedelta(0, 3600))]

    =============
    Cancel button
    =============

    If the user hits the Cancel button, he gets redurected to the
    ttschema default view:

        >>> request = TestRequest(form={'date': '2005-07-06',
        ...                             'CANCEL': 'next',
        ...                             'First_start': '8:00',
        ...                             'First_end': '8:30',
        ...                             'Second_start': '8:45',
        ...                             'Second_end': '9:15',
        ...                             'Third_start': '9:30',
        ...                             'Third_end': '10:00',
        ...                             'Fourth_start': '',
        ...                             'Fourth_end': '',
        ...                             })
        >>> view = SpecialDayView(ttschema, request)
        >>> result = view()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/ttschemas/usual'

    No exception gets added:

        >>> ttschema.model.exceptionDays[datetime.date(2005, 7, 6)]
        Traceback (most recent call last):
          ...
        KeyError: datetime.date(2005, 7, 6)


    ==========================================
    The Boring Bit -- Various Error Conditions
    ==========================================

    What if the date is incorrect?

        >>> request = TestRequest(form={'date': 'Your father was a hamster'})
        >>> view = SpecialDayView(ttschema, request)
        >>> result = view()
        >>> view.error == 'Invalid date. Please use YYYY-MM-DD format.'
        True
        >>> view.error in result
        True
        >>> `view.template` == `view.select_template`
        True

    What if the date is not in a term?

        >>> request = TestRequest(form={'date': '2004-01-01'})
        >>> view = SpecialDayView(ttschema, request)
        >>> result = view()
        >>> view.error == 'The date does not belong to any term.'
        True
        >>> view.error in result
        True

    We're courteous enough though to leave the date intact in the input field:

        >>> 'value="2004-01-01"' in result
        True

    What if the start/end times are incorrect?  Highlight them with a
    red border.

    If either a start or an end time is provided, the other must be
    provided as well.  Otherwise it is considered an error.

        >>> request = TestRequest(form={'date': '2005-07-13',
        ...                             'SUBMIT': 'next',
        ...                             'First_start': '800',
        ...                             'First_end': '8:30',
        ...                             'Second_start': '',
        ...                             'Second_end': '9:15',
        ...                             'Third_start': '9:30',
        ...                             'Third_end': '',
        ...                             'Fourth_start': '14:00',
        ...                             'Fourth_end': '15:00',
        ...                             })
        >>> view = SpecialDayView(ttschema, request)
        >>> result = view()

    Update did not happen:

        >>> ttschema.model.exceptionDays[datetime.date(2005, 7, 13)]
        Traceback (most recent call last):
          ...
        KeyError: datetime.date(2005, 7, 13)

    The erroneous fields are noticed:

        >>> view.field_errors
        ['First_start', 'Second_start', 'Third_end']

        >>> view.error
        u'Some values were invalid.  They are highlighted in red.'

        >>> print result
        <BLANKLINE>
        ...
           <table>
             <tr>
               <th>Period title</th>
               <th>Original start</th>
               <th>Original end</th>
               <th>New start</th>
               <th>New end</th>
             </tr>
             <tr>
               <td>First</td>
               <td>09:00</td>
               <td>09:45</td>
               <td class="error">
                 <input type="text" name="First_start" value="800" />
               </td>
               <td>
                 <input type="text" name="First_end" value="8:30" />
               </td>
             </tr>
             <tr>
               <td>Second</td>
               <td>10:00</td>
               <td>10:45</td>
               <td class="error">
                 <input type="text" name="Second_start" value="" />
               </td>
               <td>
               <input type="text" name="Second_end" value="9:15" />
               </td>
             </tr>
             <tr>
               <td>Third</td>
               <td>11:00</td>
               <td>11:45</td>
               <td>
                 <input type="text" name="Third_start" value="9:30" />
               </td>
               <td class="error">
                 <input type="text" name="Third_end" value="" />
               </td>
             </tr>
             <tr>
               <td>Fourth</td>
               <td>12:00</td>
               <td>12:45</td>
               <td>
                 <input type="text" name="Fourth_start"
                        value="14:00" />
               </td>
               <td>
                 <input type="text" name="Fourth_end" value="15:00" />
               </td>
             </tr>
           </table>
        ...

    """


def doctest_EmergencyDayView():
    """
    Emergency days
    ~~~~~~~~~~~~~~

    Set up
    ======

        >>> from schooltool.tests import setUpApplicationPreferences
        >>> setUpApplicationPreferences()

    First of all, we need an app object:

        >>> from schooltool.app import SchoolToolApplication
        >>> app = SchoolToolApplication()
        >>> directlyProvides(app, IContainmentRoot)
        >>> app.setSiteManager(LocalSiteManager(app))
        >>> setSite(app)

    We have a timetable schema to put the view on:

        >>> from schooltool.timetable.browser import SpecialDayView
        >>> ttschema = createSchema(['Day 1', 'Day 2'],
        ...                         ['First',
        ...                          'Second',
        ...                          'Third',
        ...                          'Fourth'],
        ...                         ['First',
        ...                          'Second',
        ...                          'Third',
        ...                          'Fourth'])
        >>> app['ttschemas']['usual'] = ttschema

    The schema has a model attribute:

        >>> from schooltool.timetable import SequentialDaysTimetableModel
        >>> default = createDayTemplate([('First', 9, 0, 45),
        ...                              ('Second', 10, 0, 45),
        ...                              ('Third', 11, 0, 45),
        ...                              ('Fourth', 12, 0, 45)])
        >>> ttschema.model = SequentialDaysTimetableModel(['Day 1', 'Day 2'],
        ...                                               {None: default})

    We will need a term:

        >>> from schooltool.timetable import Term
        >>> term = Term('2005 summer',
        ...             datetime.date(2005, 6, 1),
        ...             datetime.date(2005, 8, 31))
        >>> app["terms"]["2005-summer"] = term
        >>> term.addWeekdays(0, 1, 2, 3, 4, 5)

    Now we can create the view:

        >>> from schooltool.timetable.browser import EmergencyDayView
        >>> request = TestRequest()
        >>> view = EmergencyDayView(ttschema, request)
        >>> print view()
        <BLANKLINE>
        ...
        <p>
        This form allows you to mark a date as an emergency non-schoolday and
        add a replacement day to the term.
        </p>
        ...
          <div class="row">
            <label>Date</label>
            <input type="text" name="date" />
          </div>
        <BLANKLINE>
          <div class="controls">
            <input type="submit" class="button-ok" name="CHOOSE"
                   value="Proceed" />
            <input type="submit" class="button-cancel" name="CANCEL"
                   value="Cancel" />
          </div>
        ...

    When we enter the emergency date, we get to choose the replacement day:

        >>> request = TestRequest(form={'date': '2005-07-07'})
        >>> view = EmergencyDayView(ttschema, request)
        >>> view.update()
        >>> view.date
        datetime.date(2005, 7, 7)

    The view now can offer a choice of replacements after this day.
    These will be all non-schooldays in the term and 3 days after the term:

        >>> view.replacements()
        [datetime.date(2005, 7, 10),
         datetime.date(2005, 7, 17),
         datetime.date(2005, 7, 24),
         datetime.date(2005, 7, 31),
         datetime.date(2005, 8, 7),
         datetime.date(2005, 8, 14),
         datetime.date(2005, 8, 21),
         datetime.date(2005, 8, 28),
         datetime.date(2005, 9, 1),
         datetime.date(2005, 9, 2),
         datetime.date(2005, 9, 3)]


    The page presented next contains a selection of these dates:

        >>> print view()
        <BLANKLINE>
        ...
          <input type="hidden" name="date" value="2005-07-07" />
        ...
          <div class="row">
            <label>Replacement</label>
            <select name="replacement">
              <option>2005-07-10</option>
              <option>2005-07-17</option>
              <option>2005-07-24</option>
              <option>2005-07-31</option>
              <option>2005-08-07</option>
              <option>2005-08-14</option>
              <option>2005-08-21</option>
              <option>2005-08-28</option>
              <option>2005-09-01</option>
              <option>2005-09-02</option>
              <option>2005-09-03</option>
            </select>
          </div>
          ...

    The original day id of the emergency day was:

         >>> def getDayId(date):
         ...     return ttschema.model._periodsInDay(term, ttschema, date)[0]
         >>> getDayId(datetime.date(2005, 7, 7))
         'Day 2'

    The ids of some other days before and after the planned
    replacement day:

         >>> getDayId(datetime.date(2005, 7, 8))
         'Day 1'
         >>> getDayId(datetime.date(2005, 7, 11))
         'Day 1'

    If the user selects a replacement day and calls the view, several
    things happen:

        >>> request = TestRequest(form={'date': '2005-07-07',
        ...                             'replacement': '2005-07-10'})
        >>> view = EmergencyDayView(ttschema, request)
        >>> result = view()
        >>> view.date
        datetime.date(2005, 7, 7)
        >>> view.replacement
        datetime.date(2005, 7, 10)

    The user gets redirected:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/ttschemas/usual'

    The replacement day gets added to the calendar, and the emergency
    day gets an empty day template:

        >>> term.isSchoolday(datetime.date(2005, 7, 10))
        True
        >>> term.isSchoolday(datetime.date(2005, 7, 7))
        True
        >>> ttschema.model.periodsInDay(term, ttschema,
        ...                             datetime.date(2005, 7, 7))
        []

    The day id of the replacement day is the same as that of the
    emergency day:

         >>> getDayId(datetime.date(2005, 7, 7))
         'Day 2'

    Day ids of the days before and after the replacement day are unchanged:

         >>> getDayId(datetime.date(2005, 7, 8))
         'Day 1'
         >>> getDayId(datetime.date(2005, 7, 11))
         'Day 1'

    All day events get posted to the schoolwide calendar on both days,
    notifying of the shift:

        XXX: Tvon has not made the schoolwide calendar yet!
        #>>> cal = getSchoolToolApplication().calendar
        #>>> for event in calendar:
        #...     print event.dtstart, event.title
        2005-07-07 00:00 UTC School is cancelled
        2005-07-10 00:00 UTC Replacement schoolday for emergency day 2005-07-07

    When the replacement day is outside the term, the end date of the
    term gets adjusted:

        >>> request = TestRequest(form={'date': '2005-07-08',
        ...                             'replacement': '2005-09-03'})
        >>> view = EmergencyDayView(ttschema, request)
        >>> result = view()
        >>> getDayId(datetime.date(2005, 9, 3))
        'Day 1'
        >>> term.last
        datetime.date(2005, 9, 3)

    The days that might have been implicitly added to the term (might
    have been a weekend) are not marked as schooldays:

        >>> term.isSchoolday(datetime.date(2005, 9, 1))
        False
        >>> term.isSchoolday(datetime.date(2005, 9, 2))
        False
        >>> term.isSchoolday(datetime.date(2005, 9, 3))
        True

    ======
    Cancel
    ======

    If the cancel button is pressed, nothing is changed, and the user
    is redirected:

        >>> request = TestRequest(form={'date': '2005-07-09',
        ...                             'replacement': '2005-09-04',
        ...                             'CANCEL': 'Cancel'})
        >>> view = EmergencyDayView(ttschema, request)
        >>> result = view()
        >>> ttschema.model.periodsInDay(term, ttschema,
        ...                             datetime.date(2005, 7, 9))
        [<schooltool.timetable.SchooldayPeriod object at ...>,
         <schooltool.timetable.SchooldayPeriod object at ...>,
         <schooltool.timetable.SchooldayPeriod object at ...>,
         <schooltool.timetable.SchooldayPeriod object at ...>]
        >>> term.last
        datetime.date(2005, 9, 3)

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/ttschemas/usual'

    ======
    Errors
    ======

    If date is invalid, the user sees a nice error:

        >>> request = TestRequest(form={'date': '07/09/05'})
        >>> view = EmergencyDayView(ttschema, request)
        >>> print view()
        <BLANKLINE>
        ...
        <div class="error">The date you entered is invalid.
           Please use the YYYY-MM-DD format.</div>
        ...


    If the date is not in term, the user sees the appropriate message:

        >>> request = TestRequest(form={'date': '1999-12-31'})
        >>> view = EmergencyDayView(ttschema, request)
        >>> print view()
        <BLANKLINE>
        ...
        <div class="error">The date you entered does not belong
        to any term.</div>
        ...

    If the date is not a schoolday, we tell that:

        >>> request = TestRequest(form={'date': '2005-07-17'})
        >>> view = EmergencyDayView(ttschema, request)
        >>> print view()
        <BLANKLINE>
        ...
        <div class="error">The date you entered is not a schoolday.</div>
        ...

    If replacement is invalid, the user gets to enter it again:

        >>> request = TestRequest(form={'date': '2005-07-19',
        ...                             'replacement': 'whatever'})
        >>> view = EmergencyDayView(ttschema, request)
        >>> print view()
        <BLANKLINE>
        ...
        <div class="error">The replacement date you entered is invalid.</div>
        ...

    """


def test_suite():
    suite = unittest.TestSuite()
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=optionflags
                                            | doctest.NORMALIZE_WHITESPACE))
    suite.addTest(doctest.DocTestSuite('schooltool.timetable.browser',
                                       optionflags=optionflags))
    suite.addTest(unittest.makeSuite(TestAdvancedTimetableSchemaAdd))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
