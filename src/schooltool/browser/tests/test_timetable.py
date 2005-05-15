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

from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.testing.doctestunit import pprint
from zope.app.testing import ztapi
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.component.hooks import setSite
from zope.app.component.site import LocalSiteManager

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

    from schooltool.timetable import Timetable
    from schooltool.timetable import TimetableDay
    schema = Timetable(days)
    for day, periods in zip(days, periods_for_each_day):
        schema[day] = TimetableDay(list(periods))
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
        >>> from schooltool.browser.timetable import TermView
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
        >>> from schooltool.browser.timetable import TermEditView
        >>> context = Term('Sample', datetime.date(2004, 8, 1),
        ...                        datetime.date(2004, 8, 31))
        >>> request = TestRequest()
        >>> view = TermEditView(context, request)

    view.title returns a Zope 3 I18N Message ID.

        >>> from zope.i18n import translate
        >>> view.title()
        u'Change Term: $title'
        >>> translate(view.title())
        u'Change Term: Sample'

    """


def doctest_TermEditView_calendar():
    """Unit tests for TermEditView.calendar

        >>> from schooltool.timetable import Term
        >>> from schooltool.browser.timetable import TermEditView
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
        >>> from schooltool.browser.timetable import TermEditView
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
        >>> from schooltool.browser.timetable import TermAddView
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
        >>> from schooltool.browser.timetable import TermAddView
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
        >>> from schooltool.browser.timetable import TermAddView
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
        >>> from schooltool.browser.timetable import TermAddView
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
        >>> from schooltool.browser.timetable import TermAddView
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
        >>> from schooltool.browser.timetable import TermAddView
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
        >>> from schooltool.browser.timetable import TermAddView
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
        >>> from schooltool.browser.timetable import TermRenderer

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
        >>> from schooltool.browser.timetable import TermRenderer
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
        >>> from schooltool.browser.timetable import TermRenderer
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


class TestTimetableSchemaWizard(NiceDiffsMixin, unittest.TestCase):

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
        from schooltool.interfaces import ITimetableModelFactory
        ztapi.provideUtility(ITimetableModelFactory,
                             SequentialDaysTimetableModel,
                             'SequentialDaysTimetableModel')
        ztapi.provideUtility(ITimetableModelFactory,
                             WeeklyTimetableModel,
                             'WeeklyTimetableModel')

    def tearDown(self):
        tearDown()

    def createView(self, request=None):
        from schooltool.browser.timetable import TimetableSchemaWizard
        context = self.app["ttschemas"]
        context['default'] = createSchema(['Day 1'], ['Period 1'])
        if request is None:
            request = TestRequest()
        view = TimetableSchemaWizard(context, request)
        return view

    def test(self):
        view = self.createView()
        result = view()
        self.assert_('name="field.name" size="20" type="text" value="default"'
                     in result)

    def test_with_data(self):
        request = TestRequest(form={'day1': 'Monday',
                                    'field.name': 'something',
                                    'model': 'SequentialDaysTimetableModel',
                                    'time1.period': 'Period 1',
                                    'time1.day0': '9:00-9:45',
                                    })
        view = self.createView(request)
        result = view()
        self.assertEquals(view.ttschema,
                          createSchema(['Monday'], ['Period 1']))
        self.assert_('value="something"' in result, result)
        self.assertEquals(view.name_widget.error(), '')
        self.assertEquals(view.model_name, 'SequentialDaysTimetableModel')
        self.assertEquals(view.model_error, None)
        self.assertEquals(view.day_templates,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45)])})

    def test_creation(self):
        request = TestRequest(form={'day1': 'Monday',
                                    'field.name': 'something',
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

    def XXXtest_name_missing(self):
        request = TestRequest(form={'name': ''})
        view = self.createView(request)
        view()
        self.assertEquals(view.name_widget.error,
                          "Timetable schema name must not be empty")

    def XXXtest_name_error(self):
        view = self.createView(TestRequest(form={'name': 'not valid'}))
        view()
        self.assert_(view.name_widget.error().startswith(
                            "Timetable schema name can only contain "))

    def XXXtest_name_duplicate(self):
        view = self.createView(TestRequest(form={'name': 'default'}))
        view()
        self.assertEquals(view.name_widget.error,
                          "Timetable schema with this name already exists.")

    def test_model_error(self):
        request = TestRequest(form={'model': 'xxx',
                                    'CREATE': 'Create'})
        view = self.createView(request)
        view()
        self.assertEquals(view.model_error, "Please select a value")

    def test_model_error_ignored_unless_this_is_the_final_submit(self):
        view = self.createView(TestRequest(form={'model': 'xxx'}))
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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    suite.addTest(doctest.DocTestSuite('schooltool.browser.timetable',
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaWizard))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
