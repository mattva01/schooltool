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
from datetime import datetime, date, timedelta
from zope.testing import doctest
from zope.publisher.browser import TestRequest
from zope.interface import directlyProvides
from zope.interface.verify import verifyObject
from zope.app.tests import setup, ztapi
from zope.app.publisher.browser import BrowserView
from zope.app.traversing.interfaces import IContainmentRoot

# Used in defining CalendarEventAddTestView
from schoolbell.app.browser.cal import CalendarEventAddView
from schoolbell.app.browser.cal import ICalendarEventAddForm
from schoolbell.app.cal import CalendarEvent
from schoolbell.app.cal import Calendar

# Used in defining CalendarEventEditTestView
from schoolbell.app.browser.cal import CalendarEventEditView
from schoolbell.app.browser.cal import ICalendarEventEditForm
from schoolbell.app.browser.tests.setup import setUp, tearDown

# Used for the PrincipalStub
from schoolbell.app.app import Person
from schoolbell.app.interfaces import IPerson

def doctest_CalendarOwnerTraverser():
    """Tests for CalendarOwnerTraverser.

    CalendarOwnerTraverser allows you to traverse directly to the calendar
    of a calendar owner.

        >>> from schoolbell.app.browser.cal import CalendarOwnerTraverser
        >>> from schoolbell.app.app import Person
        >>> person = Person()
        >>> request = TestRequest()
        >>> traverser = CalendarOwnerTraverser(person, request)
        >>> traverser.context is person
        True
        >>> traverser.request is request
        True

    The traverser should implement IBrowserPublisher:

        >>> from zope.publisher.interfaces.browser import IBrowserPublisher
        >>> verifyObject(IBrowserPublisher, traverser)
        True

    Let's check that browserDefault suggests 'index.html':

        >>> context, path = traverser.browserDefault(request)
        >>> context is person
        True
        >>> path
        ('index.html',)

    The whole point of this class is that we can ask for the calendar:

        >>> traverser.publishTraverse(request, 'calendar') is person.calendar
        True

    We can also get the calendar as iCalendar:

        >>> from schoolbell.app.interfaces import ISchoolBellCalendar
        >>> ztapi.browserView(ISchoolBellCalendar, 'calendar.ics', BrowserView)
        >>> view = traverser.publishTraverse(request, 'calendar.ics')
        >>> view.context is traverser.context.calendar
        True
        >>> view.request is traverser.request
        True

    However, we should be able to access other views of the object:

        >>> from schoolbell.app.interfaces import IPerson
        >>> ztapi.browserView(IPerson, 'some_view.html', BrowserView)

        >>> view = traverser.publishTraverse(request, 'some_view.html')
        >>> view.context is traverser.context
        True
        >>> view.request is traverser.request
        True

    If we try to look up a nonexistent view, we should get a NotFound error:

        >>> traverser.publishTraverse(request,
        ...                           'nonexistent.html') # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        NotFound: Object: <...Person object at ...>, name: 'nonexistent.html'

    """


def doctest_CalendarTraverser():
    """Tests for CalendarTraverser.

    CalendarTraverser allows you to traverse directly various calendar views:

        >>> from schoolbell.app.browser.cal import CalendarTraverser
        >>> from schoolbell.app.cal import Calendar
        >>> cal = Calendar()
        >>> request = TestRequest()
        >>> traverser = CalendarTraverser(cal, request)
        >>> traverser.context is cal
        True
        >>> traverser.request is request
        True

    The traverser should implement IBrowserPublisher:

        >>> from zope.publisher.interfaces.browser import IBrowserPublisher
        >>> verifyObject(IBrowserPublisher, traverser)
        True

    Let's check that browserDefault suggests 'daily.html':

        >>> context, path = traverser.browserDefault(request)
        >>> context is cal
        True
        >>> path
        ('daily.html',)

    The traverser is smart enough to parse date-like URLs.  It will choose
    the right view and add the 'date' argument to the request.

        >>> def queryMultiStub((context, request), name):
        ...     print name
        >>> traverser.queryMultiAdapter = queryMultiStub

        >>> view = traverser.publishTraverse(request, '2003')
        yearly.html
        >>> request['date']
        '2003-01-01'

    The getViewByDate() method is responsible for recognizing dates.  It
    may return a view if it recognizes a date, or None.

    The yearly view is returned when only a year is provided:

        >>> traverser.getViewByDate(request, '2002')
        'yearly.html'
        >>> request['date']
        '2002-01-01'

    The monthly view is supported too:

        >>> traverser.getViewByDate(request, '2002-07')
        'monthly.html'
        >>> request['date']
        '2002-07-01'

    The weekly view can be accessed by adding 'w' in front of the week number:

      >>> traverser.getViewByDate(request, '2002-w11')
      'weekly.html'
      >>> request['date']
      '2002-03-11'

    The daily view is supported too:

        >>> traverser.getViewByDate(request, '2002-07-03')
        'daily.html'
        >>> request['date']
        '2002-07-03'

    Invalid dates are not touched:

        >>> for name in ['', 'abc', 'index.html', '', '200a', '2004-1a',
        ...              '2001-02-03-04', '2001/02/03', '2001-w3a', 'a-w2',
        ...              '1000', '3000']:
        ...     assert traverser.getViewByDate(request, name) is None

    If we try to look up a nonexistent view, we should get a NotFound error:

        >>> traverser.publishTraverse(request,
        ...                           'nonexistent.html') # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        NotFound: Object: <...Calendar object at ...>, name: 'nonexistent.html'

    You can traverse into calendar events by their unique id:

        >>> from schoolbell.app.cal import CalendarEvent
        >>> event = CalendarEvent(datetime(2002, 2, 2, 2, 2),
        ...                       timedelta(hours=2), "Some event",
        ...                       unique_id="it's me!")
        >>> cal.addEvent(event)
        >>> traverser.publishTraverse(request, "it's me!") is event
        True

    """


def doctest_EventForDisplay():
    """A wrapper for calendar events.

        >>> from schoolbell.app.browser.cal import EventForDisplay
        >>> e1 = createEvent('2004-01-02 14:45:50', '5min', 'yawn')
        >>> e1 = EventForDisplay(e1, 'red', 'green')

    EventForDisplay lets us access all the usual attributes

        >>> e1.dtstart
        datetime.datetime(2004, 1, 2, 14, 45, 50)
        >>> e1.title
        'yawn'

    It adds some additional attributes

        >>> e1.dtend
        datetime.datetime(2004, 1, 2, 14, 50, 50)
        >>> e1.color1
        'red'
        >>> e1.color2
        'green'
        >>> e1.shortTitle
        'yawn'

    shortTitle is ellipsized if the title is long

        >>> e2 = createEvent('2004-01-02 12:00:00', '15min',
        ...                  'sleeping for a little while because I was tired')
        >>> e2 = EventForDisplay(e2, 'blue', 'yellow')
        >>> e2.shortTitle
        'sleeping for a ...'

    Lists of EventForDisplay objects can be sorted by start time

        >>> e1 > e2
        True

    The `renderShort` method is used to render the event in the monthly
    calendar view.

        >>> print e2.renderShort().replace('&ndash;', '--')
        sleeping for a ... (12:00--12:15)

    """


def doctest_CalendarDay():
    """A calendar day is a set of events that took place on a particular day.

        >>> from schoolbell.app.browser.cal import CalendarDay
        >>> day1 = CalendarDay(date(2004, 8, 5))
        >>> day1.date
        datetime.date(2004, 8, 5)
        >>> day1.title
        u'Thursday, 2004-08-05'
        >>> day1.events
        []

        >>> day2 = CalendarDay(date(2004, 7, 15), ["abc", "def"])
        >>> day2.date
        datetime.date(2004, 7, 15)
        >>> day2.title
        u'Thursday, 2004-07-15'
        >>> day2.events
        ['abc', 'def']

    You can sort a list of CalendarDay objects.

        >>> day1 > day2 and not day1 < day2
        True
        >>> day2 == CalendarDay(date(2004, 7, 15))
        True

    You can test a calendar day to see if its date is today
    TODO: I'm not sure that this test is i18n safe, it passes here but maybe
    not in other locales

        >>> day3 = CalendarDay(datetime.now().date())
        >>> day3.isToday()
        True

    """


def createEvent(dtstart, duration, title, **kw):
    """Create a CalendarEvent.

      >>> from schoolbell.app.cal import CalendarEvent
      >>> e1 = createEvent('2004-01-02 14:45:50', '5min', 'title')
      >>> e1 == CalendarEvent(datetime(2004, 1, 2, 14, 45, 50),
      ...                timedelta(minutes=5), 'title', unique_id=e1.unique_id)
      True

      >>> e2 = createEvent('2004-01-02 14:45', '3h', 'title')
      >>> e2 == CalendarEvent(datetime(2004, 1, 2, 14, 45),
      ...                timedelta(hours=3), 'title', unique_id=e2.unique_id)
      True

      >>> e3 = createEvent('2004-01-02', '2d', 'title')
      >>> e3 == CalendarEvent(datetime(2004, 1, 2),
      ...                timedelta(days=2), 'title', unique_id=e3.unique_id)
      True

    createEvent is very strict about the format of it arguments, and terse in
    error reporting, but it's OK, as it is only used in unit tests.
    """
    from schoolbell.app.cal import CalendarEvent
    from schoolbell.calendar.utils import parse_datetime
    if dtstart.count(':') == 0:         # YYYY-MM-DD
        dtstart = parse_datetime(dtstart+' 00:00:00') # add hh:mm:ss
    elif dtstart.count(':') == 1:       # YYYY-MM-DD HH:MM
        dtstart = parse_datetime(dtstart+':00') # add seconds
    else:                               # YYYY-MM-DD HH:MM:SS
        dtstart = parse_datetime(dtstart)
    dur = timedelta(0)
    for part in duration.split('+'):
        part = part.strip()
        if part.endswith('d'):
            dur += timedelta(days=int(part.rstrip('d')))
        elif part.endswith('h'):
            dur += timedelta(hours=int(part.rstrip('h')))
        elif part.endswith('sec'):
            dur += timedelta(seconds=int(part.rstrip('sec')))
        else:
            dur += timedelta(minutes=int(part.rstrip('min')))
    return CalendarEvent(dtstart, dur, title, **kw)


class PrincipalStub:

    _person = Person()

    def __conform__(self, interface):
        if interface is IPerson:
            return self._person


class TestCalendarViewBase(unittest.TestCase):
    # Legacy unit tests from SchoolTool.

    def setUp(self):
        setup.placelessSetUp()
        setup.setUpTraversal()
        setup.setUpAnnotations()

    def tearDown(self):
        setup.placelessTearDown()

    def test_dayTitle(self):
        from schoolbell.app.browser.cal import CalendarViewBase
        from schoolbell.app.app import getPersonPreferences
        from schoolbell.app.interfaces import IPersonPreferences
        from schoolbell.app.interfaces import IHavePreferences

        ztapi.provideAdapter(IHavePreferences, IPersonPreferences,
                             getPersonPreferences)

        request = TestRequest()
        request.setPrincipal(PrincipalStub())
        view = CalendarViewBase(None, request)
        dt = datetime(2004, 7, 1)
        self.assertEquals(view.dayTitle(dt), "Thursday, 2004-07-01")

        # set the dateformat preference to the long format
        prefs = IPersonPreferences(request.principal._person)
        prefs.dateformat = "Day Month, Year"

        self.assertEquals(view.dayTitle(dt), "Thursday, 01 July, 2004")

    def test_prev_next(self):
        from schoolbell.app.browser.cal import CalendarViewBase
        from schoolbell.app.app import getPersonPreferences
        from schoolbell.app.interfaces import IPersonPreferences
        from schoolbell.app.interfaces import IHavePreferences

        ztapi.provideAdapter(IHavePreferences, IPersonPreferences,
                             getPersonPreferences)

        request = TestRequest()
        request.setPrincipal(PrincipalStub())
        view = CalendarViewBase(None, request)

        view.cursor = date(2004, 8, 18)
        self.assertEquals(view.prevMonth(), date(2004, 7, 1))
        self.assertEquals(view.nextMonth(), date(2004, 9, 1))
        self.assertEquals(view.prevDay(), date(2004, 8, 17))
        self.assertEquals(view.nextDay(), date(2004, 8, 19))

    def test_getWeek(self):
        from schoolbell.app.browser.cal import CalendarViewBase, CalendarDay
        from schoolbell.app.cal import Calendar
        from schoolbell.app.app import getPersonPreferences
        from schoolbell.app.interfaces import IPersonPreferences
        from schoolbell.app.interfaces import IHavePreferences

        ztapi.provideAdapter(IHavePreferences, IPersonPreferences,
                             getPersonPreferences)

        request = TestRequest()
        request.setPrincipal(PrincipalStub())

        cal = Calendar()
        view = CalendarViewBase(cal, request)
        self.assertEquals(view.first_day_of_week, 0) # Monday by default

        # set the weekstart to sunday
        prefs = IPersonPreferences(request.principal._person)
        prefs.weekstart = "Sunday"

        view_sunday = CalendarViewBase(cal, request)
        self.assertEquals(view_sunday.first_day_of_week, 6)

        def getDaysStub(start, end):
            return [CalendarDay(start), CalendarDay(end)]
        view.getDays = getDaysStub

        for dt in (date(2004, 8, 9), date(2004, 8, 11), date(2004, 8, 15)):
            week = view.getWeek(dt)
            self.assertEquals(week,
                              [CalendarDay(date(2004, 8, 9)),
                               CalendarDay(date(2004, 8, 16))])

        dt = date(2004, 8, 16)
        week = view.getWeek(dt)
        self.assertEquals(week,
                          [CalendarDay(date(2004, 8, 16)),
                           CalendarDay(date(2004, 8, 23))])

    def test_getWeek_first_day_of_week(self):
        from schoolbell.app.browser.cal import CalendarViewBase, CalendarDay
        from schoolbell.app.cal import Calendar
        from schoolbell.app.app import getPersonPreferences
        from schoolbell.app.interfaces import IPersonPreferences
        from schoolbell.app.interfaces import IHavePreferences

        ztapi.provideAdapter(IHavePreferences, IPersonPreferences,
                             getPersonPreferences)

        request = TestRequest()
        request.setPrincipal(PrincipalStub())

        cal = Calendar()
        view = CalendarViewBase(cal, request)
        view.first_day_of_week = 2 # Wednesday

        def getDaysStub(start, end):
            return [CalendarDay(start), CalendarDay(end)]
        view.getDays = getDaysStub

        for dt in (date(2004, 8, 11), date(2004, 8, 14), date(2004, 8, 17)):
            week = view.getWeek(dt)
            self.assertEquals(week, [CalendarDay(date(2004, 8, 11)),
                                     CalendarDay(date(2004, 8, 18))],
                              "%s: %s -- %s"
                              % (dt, week[0].date, week[1].date))

        dt = date(2004, 8, 10)
        week = view.getWeek(dt)
        self.assertEquals(week,
                          [CalendarDay(date(2004, 8, 4)),
                           CalendarDay(date(2004, 8, 11))])

        dt = date(2004, 8, 18)
        week = view.getWeek(dt)
        self.assertEquals(week,
                          [CalendarDay(date(2004, 8, 18)),
                           CalendarDay(date(2004, 8, 25))])

    def test_getMonth(self):
        from schoolbell.app.browser.cal import CalendarViewBase, CalendarDay
        from schoolbell.app.cal import Calendar
        from schoolbell.app.app import getPersonPreferences
        from schoolbell.app.interfaces import IPersonPreferences
        from schoolbell.app.interfaces import IHavePreferences

        ztapi.provideAdapter(IHavePreferences, IPersonPreferences,
                             getPersonPreferences)

        request = TestRequest()
        request.setPrincipal(PrincipalStub())

        cal = Calendar()
        view = CalendarViewBase(cal, request)

        def getDaysStub(start, end):
            return [CalendarDay(start), CalendarDay(end)]
        view.getDays = getDaysStub

        weeks = view.getMonth(date(2004, 8, 11))
        self.assertEquals(len(weeks), 6)
        bounds = [(d1.date, d2.date) for d1, d2 in weeks]
        self.assertEquals(bounds,
                          [(date(2004, 7, 26), date(2004, 8, 2)),
                           (date(2004, 8, 2), date(2004, 8, 9)),
                           (date(2004, 8, 9), date(2004, 8, 16)),
                           (date(2004, 8, 16), date(2004, 8, 23)),
                           (date(2004, 8, 23), date(2004, 8, 30)),
                           (date(2004, 8, 30), date(2004, 9, 6))])

        # October 2004 ends with a Sunday, so we use it to check that
        # no days from the next month are included.
        weeks = view.getMonth(date(2004, 10, 1))
        bounds = [(d1.date, d2.date) for d1, d2 in weeks]
        self.assertEquals(bounds[4],
                          (date(2004, 10, 25), date(2004, 11, 1)))

        # Same here, just check the previous month.
        weeks = view.getMonth(date(2004, 11, 1))
        bounds = [(d1.date, d2.date) for d1, d2 in weeks]
        self.assertEquals(bounds[0],
                          (date(2004, 11, 1), date(2004, 11, 8)))

    def test_getYear(self):
        from schoolbell.app.browser.cal import CalendarViewBase, CalendarDay
        from schoolbell.app.cal import Calendar
        from schoolbell.app.app import getPersonPreferences
        from schoolbell.app.interfaces import IPersonPreferences
        from schoolbell.app.interfaces import IHavePreferences

        ztapi.provideAdapter(IHavePreferences, IPersonPreferences,
                             getPersonPreferences)

        request = TestRequest()
        request.setPrincipal(PrincipalStub())

        cal = Calendar()
        view = CalendarViewBase(cal, request)

        def getMonthStub(dt):
            return dt
        view.getMonth = getMonthStub

        year = view.getYear(date(2004, 03, 04))
        self.assertEquals(len(year), 4)
        months = []
        for quarter in year:
            self.assertEquals(len(quarter), 3)
            months.extend(quarter)
        for i, month in enumerate(months):
            self.assertEquals(month, date(2004, i+1, 1))

    def assertEqualEventLists(self, result, expected):
        fmt = lambda x: '[%s]' % ', '.join([e.title for e in x])
        self.assertEquals(result, expected,
                          '%s != %s' % (fmt(result), fmt(expected)))

    def doctest_getCalendars(self):
        """Test for CalendarViewBase.getCalendars

        CalendarViewBase.getCalendars returns a list of calendars that
        should be displayed.  This list always includes the context of
        the view, but it may also include other calendars as well.

            >>> from schoolbell.app.browser.cal import CalendarViewBase
            >>> class CalendarStub:
            ...     def __init__(self, title):
            ...         self.title = title
            >>> calendar = CalendarStub('My Calendar') 
            >>> request = TestRequest()
            >>> view = CalendarViewBase(calendar, request)
            >>> for c, col1, col2 in view.getCalendars():
            ...     print '%s (%s, %s)' % (c.title, col1, col2)
            My Calendar (#9db8d2, #7590ae)

        If the authenticated user is looking at his own calendar, then
        a list of overlaid calendars is taken into consideration

            >>> class OverlayInfoStub:
            ...     def __init__(self, title, color1, color2, show=True):
            ...         self.calendar = CalendarStub(title)
            ...         self.color1 = color1
            ...         self.color2 = color2
            ...         self.show = show
            >>> class PreferenceStub:
            ...     def __init__(self):
            ...         self.weekstart = "Monday"
            >>> from schoolbell.app.interfaces import IPersonPreferences
            >>> class PersonStub:
            ...     def __conform__(self, interface):
            ...         if interface is IPersonPreferences:
            ...             return PreferenceStub()
            ...     calendar = calendar
            ...     overlaid_calendars = [
            ...         OverlayInfoStub('Other Calendar', 'red', 'blue'),
            ...         OverlayInfoStub('Hidden', 'green', 'red', False)]
            >>> from schoolbell.app.interfaces import IPerson
            >>> class PrincipalStub:
            ...     def __conform__(self, interface):
            ...         if interface is IPerson:
            ...             return PersonStub()
            >>> request.setPrincipal(PrincipalStub())
            >>> for c, col1, col2 in view.getCalendars():
            ...     print '%s (%s, %s)' % (c.title, col1, col2)
            My Calendar (#9db8d2, #7590ae)
            Other Calendar (red, blue)

        No calendars are overlaid if the user is looking at a different
        calendar

            >>> view = CalendarViewBase(CalendarStub('Some Calendar'),
            ...                         request)
            >>> for c, col1, col2 in view.getCalendars():
            ...     print '%s (%s, %s)' % (c.title, col1, col2)
            Some Calendar (#9db8d2, #7590ae)

        """

    def test_getEvents(self):
        """Test for CalendarViewBase.getEvents

        CalendarViewBase.getEvents returns a list of wrapped calendar
        events.

            >>> from schoolbell.app.browser.cal import CalendarViewBase
            >>> from schoolbell.app.cal import Calendar
            >>> cal1 = Calendar()
            >>> cal1.addEvent(createEvent('2005-02-26 19:39', '1h', 'code'))
            >>> cal1.addEvent(createEvent('2005-02-20 16:00', '1h', 'walk'))
            >>> view = CalendarViewBase(cal1, TestRequest())
            >>> for e in view.getEvents(datetime(2005, 2, 21),
            ...                         datetime(2005, 3, 1)):
            ...     print e.title
            code

        We will stub view.getCalendars to simulate overlayed calendars

            >>> cal2 = Calendar()
            >>> cal2.addEvent(createEvent('2005-02-27 12:00', '1h', 'rest'))
            >>> view.getCalendars = lambda:[(cal1, 'r', 'g'), (cal2, 'b', 'y')]
            >>> for e in view.getEvents(datetime(2005, 2, 21),
            ...                         datetime(2005, 3, 1)):
            ...     print e.title, '(%s)' % e.color1
            code (r)
            rest (b)

        """

    def test_getDays(self):
        from schoolbell.app.browser.cal import CalendarViewBase
        from schoolbell.app.cal import Calendar

        e0 = createEvent('2004-08-10 11:00', '1h', "e0")
        e2 = createEvent('2004-08-11 11:00', '1h', "e2")
        e3 = createEvent('2004-08-12 23:00', '4h', "e3")
        e4 = createEvent('2004-08-15 11:00', '1h', "e4")
        e5 = createEvent('2004-08-10 09:00', '3d', "e5")
        e6 = createEvent('2004-08-13 00:00', '1d', "e6")
        e7 = createEvent('2004-08-12 00:00', '1d+1sec', "e7")
        e8 = createEvent('2004-08-15 00:00', '0sec', "e8")

        cal = Calendar()
        for e in [e0, e2, e3, e4, e5, e6, e7, e8]:
            cal.addEvent(e)

        request = TestRequest()
        view = CalendarViewBase(cal, request)

        start = date(2004, 8, 10)
        days = view.getDays(start, start)
        self.assertEquals(len(days), 0)

        start = date(2004, 8, 10)
        end = date(2004, 8, 16)
        days = view.getDays(start, end)

        self.assertEquals(len(days), 6)
        for i, day in enumerate(days):
            self.assertEquals(day.date, date(2004, 8, 10 + i))

        self.assertEqualEventLists(days[0].events, [e5, e0])            # 10
        self.assertEqualEventLists(days[1].events, [e5, e2])            # 11
        self.assertEqualEventLists(days[2].events, [e5, e7, e3])        # 12
        self.assertEqualEventLists(days[3].events, [e5, e7, e3, e6])    # 13
        self.assertEqualEventLists(days[4].events, [])                  # 14
        self.assertEqualEventLists(days[5].events, [e8, e4])            # 15

        start = date(2004, 8, 11)
        end = date(2004, 8, 12)
        days = view.getDays(start, end)
        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, start)
        self.assertEqualEventLists(days[0].events, [e5, e2])

    def test_getJumpToYears(self):
        from schoolbell.app.cal import Calendar
        from schoolbell.app.browser.cal import CalendarViewBase
        cal = Calendar()
        directlyProvides(cal, IContainmentRoot)

        first_year = datetime.today().year - 2
        last_year = datetime.today().year + 2

        view = CalendarViewBase(cal, TestRequest())

        displayed_years = view.getJumpToYears()

        self.assertEquals(displayed_years[0]['label'], first_year)
        self.assertEquals(displayed_years[0]['href'],
                          'http://127.0.0.1/calendar/%s' % first_year)
        self.assertEquals(displayed_years[-1]['label'], last_year)
        self.assertEquals(displayed_years[-1]['href'],
                          'http://127.0.0.1/calendar/%s' % last_year)

    def test_getJumpToMonths(self):
        from schoolbell.app.cal import Calendar
        from schoolbell.app.browser.cal import CalendarViewBase
        cal = Calendar()
        directlyProvides(cal, IContainmentRoot)

        view = CalendarViewBase(cal, TestRequest())
        view.cursor = date(2005, 3, 1)

        displayed_months = view.getJumpToMonths()

        self.assertEquals(displayed_months[0]['href'],
                          'http://127.0.0.1/calendar/2005-01')
        self.assertEquals(displayed_months[-1]['href'],
                          'http://127.0.0.1/calendar/2005-12')


class CalendarEventAddTestView(CalendarEventAddView):
    """Class for testing CalendarEventAddView.

    We extend CalendarEventAddView so we could supply arguments normaly
    provided in ZCML.
    """

    schema = ICalendarEventAddForm
    _factory = CalendarEvent
    _arguments = []
    _keyword_arguments = ['title', 'start_date', 'start_time', 'duration',
                          'recurrence', 'location', 'recurrence_type',
                          'interval', 'range', 'until', 'count', 'exceptions']
    _set_before_add = []
    _set_after_add = []


def doctest_CalendarEventAddView_add():
    r"""Tests for CalendarEventAddView adding of new event.

    First, let's simply render the CalendarEventAddTestView.

        >>> view = CalendarEventAddTestView(Calendar(), TestRequest())
        >>> view.update()

    Let's try to add an event:

        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Add'})

        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        ''

        >>> print view.errors
        ()
        >>> print view.error
        None
        >>> len(calendar)
        1
        >>> event = list(calendar)[0]
        >>> event.title
        u'Hacking'
        >>> event.dtstart
        datetime.datetime(2004, 8, 13, 15, 30)
        >>> event.duration
        datetime.timedelta(0, 3000)
        >>> event.location is None
        True

    We should have been redirected to the calendar view:
    (TODO: redirect to the day when the event occurs)

        >>> view.request.response.getStatus()
        302
        >>> view.request.response.getHeaders()['Location']
        'http://127.0.0.1/calendar/2004-08-13'

    We can cowardly run away if we decide so, i.e., cancel our request.
    In that case we are redirected to today's calendar.
    # TODO: it would be better to redirect to the date the user was on
    #       before he decided to add an event.

        >>> request = TestRequest(form={'CANCEL': 'Cancel'})
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        ''
        >>> view.request.response.getStatus()
        302
        >>> location = view.request.response.getHeaders()['Location']
        >>> expected = 'http://127.0.0.1/calendar/%s' % date.today()
        >>> (location == expected) or location
        True

    Let's try to add an event with an optional location field:

        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'field.location': 'Moon',
        ...                             'field.weekdays-empty-marker': '1',
        ...                             'UPDATE_SUBMIT': 'Add'})

        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        ''

        >>> print view.errors
        ()
        >>> print view.error
        None
        >>> len(calendar)
        1
        >>> event = list(calendar)[0]
        >>> event.location
        u'Moon'


        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '50',
        ...                             'field.recurrence_type': 'daily',})
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.title_widget.getInputValue()
        u'Hacking'
        >>> view.location_widget.getInputValue()
        u'Kitchen'
        >>> view.start_date_widget.getInputValue()
        datetime.date(2004, 8, 13)
        >>> view.start_time_widget.getInputValue()
        u'15:30'
        >>> view.duration_widget.getInputValue()
        50

    """


def doctest_CalendarEventAddView_add_validation():
    r"""Tests for CalendarEventAddView form validation.

    Let's try to add an event without a required field:

        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Add'})

        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occured.'

        >>> print view.errors
        MissingInputError: ('field.start_time', 'Time', None)
        >>> print view.error
        None
        >>> len(calendar)
        0

        >>> request = TestRequest(form={'field.title': '',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '50',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occured.'
        >>> view.errors
        WidgetInputError: ('title', 'Title', )
        >>> view.error is None
        True


        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.start_date': '2004-31-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '50',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occured.'
        >>> view.errors                                # doctest: +ELLIPSIS
        ConversionError: ('Invalid datetime data', <...>)
        >>> view.error is None
        True


        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '100h',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occured.'
        >>> view.errors                                # doctest: +ELLIPSIS
        ConversionError: ('Invalid integer data', <...>)
        >>> view.error is None
        True

        >>> request = TestRequest(form={'field.title': '',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '1530',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '60',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occured.'
        >>> view.errors
        WidgetInputError: ('title', 'Title', )
        ConversionError: (u'Invalid time', None)
        >>> view.error is None
        True

        >>> request = TestRequest(form={'field.title': '',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '1530',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '60',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE': 'update'})
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occured.'
        >>> view.errors
        WidgetInputError: ('title', 'Title', )
        ConversionError: (u'Invalid time', None)
        >>> view.error is None
        True

    """


def doctest_CalendarEventAddView_add_recurrence():
    r"""Tests for CalendarEventAddView adding of recurring event.

    Let's try to add a recurring event:

        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.duration': '50',
        ...                             'field.location': 'Moon',
        ...                             'field.recurrence': 'on',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'field.interval': '1',
        ...                             'field.range': 'forever',
        ...                             'UPDATE_SUBMIT': 'Add'})

        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        ''

        >>> print view.errors
        ()
        >>> print view.error
        None
        >>> len(calendar)
        1
        >>> event = list(calendar)[0]
        >>> event.recurrence
        DailyRecurrenceRule(1, None, None, ())

        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        ''

        >>> print view.errors
        ()
        >>> print view.error
        None
        >>> len(calendar)
        1
        >>> event = list(calendar)[0]
        >>> event.title
        u'Hacking'
        >>> event.location
        u'Kitchen'
        >>> event.dtstart
        datetime.datetime(2004, 8, 13, 15, 30)
        >>> event.duration
        datetime.timedelta(0, 3000)

        >>> event.recurrence is None
        True

        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '50',
        ...                             'field.recurrence': 'on',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'field.interval': '2',
        ...                             'field.range': 'forever',
        ...                             'UPDATE_SUBMIT': 'Add'})


        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        ''

        >>> print view.errors
        ()
        >>> print view.error
        None
        >>> len(calendar)
        1
        >>> event = list(calendar)[0]
        >>> event.title
        u'Hacking'
        >>> event.location
        u'Kitchen'
        >>> event.dtstart
        datetime.datetime(2004, 8, 13, 15, 30)
        >>> event.duration
        datetime.timedelta(0, 3000)
        >>> event.recurrence
        DailyRecurrenceRule(2, None, None, ())

    """


def doctest_CalendarEventAddView_recurrence_exceptions():
    r"""Tests for CalendarEventAddView adding of new event.

    Lets add a simple even with some exceptions:

        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...               'field.start_date': '2004-08-13',
        ...               'field.start_time': '15:30',
        ...               'field.location': 'Kitchen',
        ...               'field.duration': '50',
        ...               'field.recurrence': 'on',
        ...               'field.recurrence.used': '',
        ...               'field.recurrence_type': 'daily',
        ...               'field.interval': '1',
        ...               'field.range': 'forever',
        ...               'field.exceptions': '2004-08-14\n2004-08-19\n2004-08-20',
        ...               'UPDATE_SUBMIT': 'Add'})


        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        ''

        >>> print view.errors
        ()
        >>> print view.error
        None
        >>> len(calendar)
        1
        >>> event = list(calendar)[0]
        >>> event.recurrence
        DailyRecurrenceRule(1, None, None, (datetime.date(2004, 8, 14), datetime.date(2004, 8, 19), datetime.date(2004, 8, 20)))

    We should skip additional newlines when parsing the input:

        >>> request.form['field.exceptions'] = '2004-08-14\n\n2004-08-19\n\n\n2004-08-20'
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        ''

        >>> print view.errors
        ()
        >>> print view.error
        None
        >>> len(calendar)
        1
        >>> event = list(calendar)[0]
        >>> event.recurrence
        DailyRecurrenceRule(1, None, None, (datetime.date(2004, 8, 14), datetime.date(2004, 8, 19), datetime.date(2004, 8, 20)))

    If the any of the lines contains an invalid date - ConversionError
    is signaled:

        >>> request.form['field.exceptions'] = '2004-08-14\n2004'
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occured.'

        >>> view.errors
        ConversionError: (u'Invalid date.  Please specify YYYY-MM-DD, one per line.', None)
        >>> len(calendar)
        0

    """


def doctest_CalendarEventAddView_getMonthDay():
    r"""Tests for CalendarEventAddView.getMonthDay().

        >>> calendar = Calendar()
        >>> request = TestRequest()
        >>> request.form['field.start_date'] = u''
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.getMonthDay()
        '??'
        >>> request.form['field.start_date'] = u'2005-02-21'
        >>> view.getMonthDay()
        '21'
        >>> request.form['field.start_date'] = u''
        >>> view.getMonthDay()
        '??'

    """


def doctest_CalendarEventAddView_weekdayChecked():
    r"""Tests for CalendarEventAddView.weekdayChecked().

        >>> calendar = Calendar()
        >>> request = TestRequest()
        >>> request.form['field.start_date'] = u''
        >>> view = CalendarEventAddTestView(calendar, request)

    When the form is empty, no days are checked.

        >>> [day for day in range(7) if view.weekdayChecked(str(day))]
        []

        >>> request.form['field.start_date'] = u''
        >>> [day for day in range(7) if view.weekdayChecked(str(day))]
        []

    February 21, 2005 is a Monday.

        >>> request.form['field.start_date'] = u'2005-02-21'
        >>> [day for day in range(7) if view.weekdayChecked(str(day))]
        [0]

    Also checked are those weekdays that appear in the form

        >>> request.form['field.weekdays'] = [u'5', u'6']
        >>> [day for day in range(7) if view.weekdayChecked(str(day))]
        [0, 5, 6]

    """


def doctest_CalendarEventAddView_weekdayDisabled():
    r"""Tests for CalendarEventAddView.weekdayDisabled().

        >>> calendar = Calendar()
        >>> request = TestRequest()
        >>> request.form['field.start_date'] = u''
        >>> view = CalendarEventAddTestView(calendar, request)

    When the form is empty, no days are disabled.

        >>> [day for day in range(7) if view.weekdayDisabled(str(day))]
        []

        >>> request.form['field.start_date'] = u''
        >>> [day for day in range(7) if view.weekdayDisabled(str(day))]
        []

    February 21, 2005 is a Monday.

        >>> request.form['field.start_date'] = u'2005-02-21'
        >>> [day for day in range(7) if view.weekdayDisabled(str(day))]
        [0]

    Other weekdays are always enabled.

        >>> request.form['field.weekdays'] = [u'5', u'6']
        >>> [day for day in range(7) if view.weekdayDisabled(str(day))]
        [0]

    """


def doctest_CalendarEventAddView_getWeekDay():
    r"""Tests for CalendarEventAddView.getWeekDay().

        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.start_date': '2004-10-01',
        ...                             'field.start_time': '15:30',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '50',
        ...                             'field.recurrence': 'on',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'field.interval': '2',
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> calendar = Calendar()
        >>> view = CalendarEventAddTestView(calendar, request)

        >>> request.form['field.start_date'] = "2004-10-01"
        >>> view.getWeekDay()
        u'1st Friday'

        >>> request.form['field.start_date'] = "2004-10-13"
        >>> view.getWeekDay()
        u'2nd Wednesday'

        >>> request.form['field.start_date'] = "2004-10-16"
        >>> view.getWeekDay()
        u'3rd Saturday'

        >>> request.form['field.start_date'] = "2004-10-26"
        >>> view.getWeekDay()
        u'4th Tuesday'

        >>> request.form['field.start_date'] = "2004-10-28"
        >>> view.getWeekDay()
        u'4th Thursday'

        >>> request.form['field.start_date'] = "2004-10-29"
        >>> view.getWeekDay()
        u'5th Friday'

        >>> request.form['field.start_date'] = "2004-10-31"
        >>> view.getWeekDay()
        u'5th Sunday'

        >>> request.form['field.start_date'] = ""
        >>> view.getWeekDay()
        u'same weekday'

        >>> del request.form['field.start_date']
        >>> view.getWeekDay()
        u'same weekday'

    """


def doctest_CalendarEventAddView_getLastWeekDay():
    r"""Tests for CalendarEventAddView.getLastWeekDay().

        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.start_date': '2004-10-01',
        ...                             'field.start_time': '15:30',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '50',
        ...                             'field.recurrence': 'on',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'field.interval': '2',
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> calendar = Calendar()

        >>> request.form['field.start_date'] = ""
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.getLastWeekDay()
        u'last weekday'

        >>> request.form['field.start_date'] = "2004-10-24"
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.getLastWeekDay() is None
        True

        >>> request.form['field.start_date'] = "2004-10-25"
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.getLastWeekDay()
        u'Last Monday'

        >>> request.form['field.start_date'] = "2004-10-31"
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.getLastWeekDay()
        u'Last Sunday'

    """


def doctest_CalendarEventAddView_cross_validation():
    r"""Tests for CalendarEventAddView cross validation.

        >>> request = TestRequest(form={'field.title': 'Foo',
        ...                             'field.start_date': '2003-12-01',
        ...                             'field.start_time': '15:30',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '59',
        ...                             'field.recurrence': 'on',
        ...                             'field.recurrence_type': 'daily',
        ...                             'field.interval': '',
        ...                             'field.range': 'count',
        ...                             'field.count': '6',
        ...                             'field.until': '2004-01-01',
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> calendar = Calendar()
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occured.'
        >>> view.errors
        WidgetInputError: ('interval', u'Repeat every', )
        >>> view.error is None
        True

        >>> request = TestRequest(form={'field.title': 'Foo',
        ...                             'field.start_date': '2003-12-01',
        ...                             'field.start_time': '15:30',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '59',
        ...                             'field.recurrence': 'on',
        ...                             'field.recurrence_type' : 'daily',
        ...                             'field.interval': '1',
        ...                             'field.range': 'until',
        ...                             'field.until': '2002-01-01',
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> calendar = Calendar()
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occured.'
        >>> view.errors
        WidgetInputError: ('until', 'Repeat until', End date is earlier than start date)
        >>> view.error is None
        True

        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.location': 'Kitchen',
        ...                             'field.duration': '100',
        ...                             'field.recurrence': 'on',
        ...                             'field.recurrence_type' : 'daily',
        ...                             'field.range': 'until',
        ...                             'field.count': '23',
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> calendar = Calendar()
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occured.'
        >>> view.errors
        MissingInputError: ('field.interval', u'Repeat every', None)
        MissingInputError: ('field.until', 'Repeat until', None)
        >>> view.error is None
        True

    """


class CalendarEventEditTestView(CalendarEventEditView):
    """Class for testing CalendarEventEditView.

    We extend CalendarEventEditView so we could supply arguments normaly
    provided in ZCML.
    """

    schema = ICalendarEventEditForm
    _factory = CalendarEvent
    _arguments = []
    _keyword_arguments = ['title', 'start_date', 'start_time', 'duration',
                          'recurrence', 'location', 'recurrence_type',
                          'interval', 'range', 'until', 'count', 'exceptions']
    _set_before_add = []
    _set_after_add = []

def doctest_CalendarEventEditView_edit():
    r"""Tests for CalendarEventEditView editing of an event.

    Let's create an event:

        >>> import datetime
        >>> event = CalendarEvent(title="Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(minutes=60))

    Let's try to edit the event:

        >>> request = TestRequest(form={'field.title': 'NonHacking',
        ...                             'field.start_date': '2004-09-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Edit'})

        >>> directlyProvides(event, IContainmentRoot)
        >>> view = CalendarEventEditTestView(event, request)

        >>> view.update()
        u'Updated on ${date_time}'

        >>> print view.errors
        ()
        >>> print view.error
        None

        >>> event.title
        u'NonHacking'
        >>> event.dtstart
        datetime.datetime(2004, 9, 13, 15, 30)
        >>> event.duration
        datetime.timedelta(0, 3000)
        >>> event.location is None
        True

     Now a recurring event:

        >>> from schoolbell.app.browser.cal import makeRecurrenceRule
        >>> rule = makeRecurrenceRule(recurrence_type='yearly', interval=2,
        ...                           range='until', until='2004-01-02')
        >>> event = CalendarEvent(title="Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(minutes=60),
        ...                       recurrence=rule)
        >>> request = TestRequest(form={'field.title': 'NonHacking',
        ...                             'field.start_date': '2004-09-19',
        ...                             'field.start_time': '15:35',
        ...                             'field.duration': '50',
        ...                             'field.location': 'Kitchen',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Edit'})

        >>> directlyProvides(event, IContainmentRoot)
        >>> view = CalendarEventEditTestView(event, request)

        >>> view.update()
        u'Updated on ${date_time}'

        >>> print view.errors
        ()
        >>> print view.error
        None

        >>> event.title
        u'NonHacking'
        >>> event.dtstart
        datetime.datetime(2004, 9, 19, 15, 35)
        >>> event.duration
        datetime.timedelta(0, 3000)
        >>> event.location
        u'Kitchen'

    We have succesfully removed the recurrence:

        >>> event.recurrence is None
        True

    Now lets add a new recurrence to the existing event:

        >>> request = TestRequest(form={'field.title': 'NonHacking',
        ...                             'field.start_date': '2004-09-19',
        ...                             'field.start_time': '15:35',
        ...                             'field.duration': '50',
        ...                             'field.location': 'Kitchen',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence': 'on',
        ...                             'field.recurrence_type' : 'daily',
        ...                             'field.range': 'count',
        ...                             'field.count': '23',
        ...                             'field.interval': '2',
        ...                             'UPDATE_SUBMIT': 'Edit'})

        >>> directlyProvides(event, IContainmentRoot)
        >>> view = CalendarEventEditTestView(event, request)

        >>> view.update()
        u'Updated on ${date_time}'

        >>> print view.errors
        ()
        >>> print view.error
        None

        >>> event.title
        u'NonHacking'
        >>> event.dtstart
        datetime.datetime(2004, 9, 19, 15, 35)
        >>> event.duration
        datetime.timedelta(0, 3000)
        >>> event.location
        u'Kitchen'
        >>> event.recurrence
        DailyRecurrenceRule(2, 23, None, ())

   """

def doctest_CalendarEventEditView_nextURL():
    r"""Tests nextURL of CalendarEventEditView.

    Let's create an event:

        >>> import datetime
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)

        >>> event = CalendarEvent(title="Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(minutes=60))
        >>> calendar.addEvent(event)

    Let's try to edit the event:

        >>> request = TestRequest(form={'date': '2004-08-13',
        ...                             'field.title': 'NonHacking',
        ...                             'field.start_date': '2004-09-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Edit'})

        >>> view = CalendarEventEditTestView(event, request)

        >>> view.update()
        u'Updated on ${date_time}'
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/calendar/2004-09-13'

    Let's try to cancel the editing event:

        >>> request = TestRequest(form={'date': '2004-08-13',
        ...                             'field.title': 'NonHacking',
        ...                             'field.start_date': '2004-09-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'CANCEL': 'Cancel'})

        >>> view = CalendarEventEditTestView(event, request)

        >>> view.update()
        ''
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/calendar/2004-08-13'

    If the date stays unchanged - we should be redirected to the date
    that was set in the request:

        >>> request = TestRequest(form={'date': '2004-08-13',
        ...                             'field.title': 'NonHacking',
        ...                             'field.start_date': '2004-09-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Edit'})
        >>> view = CalendarEventEditTestView(event, request)

        >>> view.update()
        u'Updated on ${date_time}'
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/calendar/2004-08-13'

    """

def doctest_CalendarEventEditView_updateForm():
    r"""Tests for CalendarEventEditView updateForm.

    Let's create an event:

        >>> import datetime
        >>> event = CalendarEvent(title=u"Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(minutes=60))

    Let's try to update the form after changing some values:

        >>> request = TestRequest(form={'field.title': 'NonHacking',
        ...                             'field.start_date': '2005-02-27',
        ...                             'field.start_time': '15:30',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE': 'Update'})

        >>> view = CalendarEventEditTestView(event, request)

        >>> view.update()
        ''
        >>> print view.errors
        ()
        >>> print view.error
        None

    Original event should stay unmodified:

        >>> event.title
        u'Hacking'
        >>> event.dtstart
        datetime.datetime(2004, 8, 13, 20, 0)
        >>> event.duration
        datetime.timedelta(0, 3600)
        >>> event.location is None
        True

    Yet the view should use the new start_date:

    2005-02-27 is a Sunday:

        >>> [day for day in range(7) if view.weekdayDisabled(str(day))]
        [6]

    If we submit an invalid form - errors should be generated:

        >>> request = TestRequest(form={'field.title': 'NonHacking',
        ...                             'field.start_date': '',
        ...                             'field.start_time': '',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE': 'Update'})

        >>> view = CalendarEventEditTestView(event, request)

        >>> view.update()
        u'An error occured.'
        >>> print view.errors
        WidgetInputError: ('start_date', 'Date', )
        WidgetInputError: ('start_time', 'Time', )
        >>> print view.error
        None

    """

def doctest_CalendarEventEditView_getInitialData():
    """Tests for CalendarEventEditView editing of new event.

    Let's create an event:

        >>> import datetime
        >>> event = CalendarEvent(title="Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(minutes=61),
        ...                       location="Kitchen")

    And a view for the event:

        >>> request = TestRequest()
        >>> view = CalendarEventEditTestView(event, request)

        >>> def normalize(s):
        ...   return '\\n  '.join(filter(None, s.split(' ')))

    Let's check whether the default values are set properly:

        >>> print normalize(view.title_widget())
        <input
          class="textType"
          id="field.title"
          name="field.title"
          size="20"
          type="text"
          value="Hacking"
          />

        >>> print normalize(view.start_date_widget())
        <input
          class="textType"
          id="field.start_date"
          name="field.start_date"
          size="20"
          type="text"
          value="2004-08-13"
          />

        >>> print normalize(view.start_time_widget())
        <input
          class="textType"
          id="field.start_time"
          name="field.start_time"
          size="20"
          type="text"
          value="20:00"
          />

        >>> print normalize(view.duration_widget())
        <input
          class="textType"
          id="field.duration"
          name="field.duration"
          size="10"
          type="text"
          value="61"
          />

        >>> print normalize(view.location_widget())
        <input
          class="textType"
          id="field.location"
          name="field.location"
          size="20"
          type="text"
          value="Kitchen"
          />

        >>> print normalize(view.recurrence_widget())
        <input
          class="hiddenType"
          id="field.recurrence.used"
          name="field.recurrence.used"
          type="hidden"
          value=""
          />
          <input
          class="checkboxType"
          id="field.recurrence"
          name="field.recurrence"
          type="checkbox"
          value="on"
          />

    Let's create a recurrent event:

        >>> from schoolbell.app.browser.cal import makeRecurrenceRule
        >>> rule = makeRecurrenceRule(recurrence_type='yearly', interval=2,
        ...                           range='until', until='2004-01-02')
        >>> event = CalendarEvent(title="Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(minutes=61),
        ...                       location="Kitchen", recurrence=rule)

    And a view for the event:

        >>> request = TestRequest()
        >>> view = CalendarEventEditTestView(event, request)

    Let's check whether the default values are set properly:

        >>> print normalize(view.recurrence_widget())
        <input
          class="hiddenType"
          id="field.recurrence.used"
          name="field.recurrence.used"
          type="hidden"
          value=""
          />
          <input
          class="checkboxType"
          checked="checked"
          id="field.recurrence"
          name="field.recurrence"
          type="checkbox"
          value="on"
          />

        >>> print normalize(view.interval_widget())
        <input
          class="textType"
          id="field.interval"
          name="field.interval"
          size="10"
          type="text"
          value="2"
          />

        >>> print view.recurrence_type_widget()
        <div>
        <div class="value">
        <select name="field.recurrence_type" size="1" >
        <option value="daily">Day</option>
        <option value="weekly">Week</option>
        <option value="monthly">Month</option>
        <option selected="selected" value="yearly">Year</option>
        </select>
        </div>
        <input name="field.recurrence_type-empty-marker" type="hidden" value="1" />
        </div>

        >>> print view.range_widget()
        <div>
        <div class="value">
        <select name="field.range" size="1" >
        <option value="">(no value)</option>
        <option value="count">Count</option>
        <option selected="selected" value="until">Until</option>
        <option value="forever">forever</option>
        </select>
        </div>
        <input name="field.range-empty-marker" type="hidden" value="1" />
        </div>

        >>> print normalize(view.until_widget())
        <input
          class="textType"
          id="field.until"
          name="field.until"
          size="20"
          type="text"
          value="2004-01-02"
          />

    Let's create a weekly recurrent event with exceptions:

        >>> from schoolbell.app.browser.cal import makeRecurrenceRule
        >>> exceptions = (date(2004, 8, 14), date(2004, 8, 15))
        >>> rule = makeRecurrenceRule(recurrence_type='weekly', interval=1,
        ...                           weekdays=[1, 2, 3, 4, 5, 6],
        ...                           exceptions=exceptions,
        ...                           range="count",
        ...                           count=20)
        >>> event = CalendarEvent(title="Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(minutes=61),
        ...                       location="Kitchen", recurrence=rule)

    And a view for the event:

        >>> request = TestRequest()
        >>> view = CalendarEventEditTestView(event, request)

    Let's check whether the default values are set properly:

        >>> print normalize(view.recurrence_widget())
        <input
          class="hiddenType"
          id="field.recurrence.used"
          name="field.recurrence.used"
          type="hidden"
          value=""
          />
          <input
          class="checkboxType"
          checked="checked"
          id="field.recurrence"
          name="field.recurrence"
          type="checkbox"
          value="on"
          />

        >>> print normalize(view.interval_widget())
        <input
          class="textType"
          id="field.interval"
          name="field.interval"
          size="10"
          type="text"
          value="1"
          />

        >>> print view.recurrence_type_widget()
        <div>
        <div class="value">
        <select name="field.recurrence_type" size="1" >
        <option value="daily">Day</option>
        <option selected="selected" value="weekly">Week</option>
        <option value="monthly">Month</option>
        <option value="yearly">Year</option>
        </select>
        </div>
        <input name="field.recurrence_type-empty-marker" type="hidden" value="1" />
        </div>

        >>> print view.range_widget()
        <div>
        <div class="value">
        <select name="field.range" size="1" >
        <option value="">(no value)</option>
        <option selected="selected" value="count">Count</option>
        <option value="until">Until</option>
        <option value="forever">forever</option>
        </select>
        </div>
        <input name="field.range-empty-marker" type="hidden" value="1" />
        </div>

        >>> print view.count_widget() # doctest: +ELLIPSIS
        <input...value="20"...

        >>> print view.exceptions_widget().replace("\\r\\n", "\\n")
        <textarea cols="60" id="field.exceptions" name="field.exceptions" rows="15" >2004-08-14
        2004-08-15</textarea>

        >>> print view.weekdays_widget() # doctest: +ELLIPSIS
        <script type="text/javascript">
        ...
              <select id="field.weekdays.to"
                      name="field.weekdays.to" size="5" multiple="">
              </select>
        ...


    Let's create another recurrent event:

        >>> from schoolbell.app.browser.cal import makeRecurrenceRule
        >>> rule = makeRecurrenceRule(recurrence_type='daily', interval=2,
        ...                           range="count",
        ...                           count=5)
        >>> event = CalendarEvent(title="Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(minutes=61),
        ...                       location="Kitchen", recurrence=rule)

    And a view for the event:

        >>> request = TestRequest()
        >>> view = CalendarEventEditTestView(event, request)


    The count should be set:

        >>> print view.count_widget() # doctest: +ELLIPSIS
        <input...value="5"...

    As well as the range:

        >>> print view.range_widget()
        <div>
        <div class="value">
        <select name="field.range" size="1" >
        <option value="">(no value)</option>
        <option selected="selected" value="count">Count</option>
        <option value="until">Until</option>
        <option value="forever">forever</option>
        </select>
        </div>
        <input name="field.range-empty-marker" type="hidden" value="1" />
        </div>

    Now one more event:

        >>> rule = makeRecurrenceRule(recurrence_type='monthly', interval=2,
        ...                           range="count", count=5, monthly="weekday")

        >>> event = CalendarEvent(title="Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(minutes=61),
        ...                       location="Kitchen", recurrence=rule)

    And a view for the event:

        >>> request = TestRequest()
        >>> view = CalendarEventEditTestView(event, request)

    """


def doctest_CalendarEventEditView_getStartDate():
    """Tests for CalendarEventEditView getStartDate().

    Let's create an event:

        >>> import datetime
        >>> event = CalendarEvent(title="Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(minutes=61),
        ...                       location="Kitchen")

    And a view for the event:

        >>> request = TestRequest()
        >>> view = CalendarEventEditTestView(event, request)

    If the date is not passed in the request we should get the date of the event:

        >>> view.getStartDate()
        datetime.date(2004, 8, 13)

    If the date is passed in request but has no sane value we should get None:

        >>> request.form = {'field.start_date': "200"}
        >>> view = CalendarEventEditTestView(event, request)
        >>> view.getStartDate() is None
        True

    If the field in the form is left blang we should return None too:

        >>> request.form = {'field.start_date': ""}
        >>> view = CalendarEventEditTestView(event, request)
        >>> view.getStartDate() is None
        True

    """

class TestGetRecurrenceRule(unittest.TestCase):

    def test_getRecurrenceRule(self):
        from schoolbell.calendar.recurrent import DailyRecurrenceRule
        from schoolbell.calendar.recurrent import WeeklyRecurrenceRule
        from schoolbell.calendar.recurrent import MonthlyRecurrenceRule
        from schoolbell.calendar.recurrent import YearlyRecurrenceRule
        from schoolbell.app.browser.cal import makeRecurrenceRule

        # Rule is not returned when the checkbox is unchecked

        rule = makeRecurrenceRule(recurrence_type='daily', interval=1)
        self.assertEquals(rule, DailyRecurrenceRule(interval=1))

        rule = makeRecurrenceRule(recurrence_type='daily', interval=2)
        self.assertEquals(rule, DailyRecurrenceRule(interval=2))

        rule = makeRecurrenceRule(recurrence_type='weekly', interval=3)
        self.assertEquals(rule, WeeklyRecurrenceRule(interval=3))

        rule = makeRecurrenceRule(recurrence_type='monthly', interval=1)
        self.assertEquals(rule, MonthlyRecurrenceRule(interval=1))

        rule = makeRecurrenceRule(recurrence_type='yearly')
        self.assertEquals(rule, YearlyRecurrenceRule(interval=1))

        rule = makeRecurrenceRule(recurrence_type='yearly', interval=1,
                                  until=date(2004, 01, 02), count=3,
                                  range="until")
        self.assertEquals(rule, YearlyRecurrenceRule(interval=1,
                                                     until=date(2004, 1, 2)))

        rule = makeRecurrenceRule(recurrence_type='yearly',
                                  interval=1, until='2004-01-02',
                                  count=3, range="count")
        self.assertEquals(rule, YearlyRecurrenceRule(interval=1, count=3),
                          rule.__dict__)

        rule = makeRecurrenceRule(recurrence_type='yearly', interval=1,
                                  until='2004-01-02', count=3, range="forever")
        self.assertEquals(rule, YearlyRecurrenceRule(interval=1))

        rule = makeRecurrenceRule(recurrence_type='yearly', interval=1,
                                  until='2004-01-02', count=3)
        self.assertEquals(rule, YearlyRecurrenceRule(interval=1))

        dates = (date(2004, 1, 1), date(2004, 1, 2))
        rule = makeRecurrenceRule(recurrence_type='daily', interval=1,
                                  exceptions=dates)
        self.assertEquals(rule, DailyRecurrenceRule(interval=1,
                                                    exceptions=dates))

        rule = makeRecurrenceRule(recurrence_type='weekly', interval=1,
                                  weekdays=(2,))
        self.assertEquals(rule, WeeklyRecurrenceRule(interval=1,
                                                     weekdays=(2, )))

        rule = makeRecurrenceRule(recurrence_type='weekly', interval=1,
                        weekdays=[1, 2])
        self.assertEquals(rule, WeeklyRecurrenceRule(interval=1,
                                                     weekdays=(1, 2)))

        rule = makeRecurrenceRule(recurrence_type='monthly', interval=1,
                                  monthly="monthday")
        self.assertEquals(rule, MonthlyRecurrenceRule(interval=1,
                                                      monthly="monthday"))

        rule = makeRecurrenceRule(recurrence_type='monthly', interval=1,
                                  monthly="weekday")
        self.assertEquals(rule, MonthlyRecurrenceRule(interval=1,
                                                      monthly="weekday"))

        rule = makeRecurrenceRule(recurrence_type='monthly', interval=1,
                                  monthly="lastweekday")
        self.assertEquals(rule, MonthlyRecurrenceRule(interval=1,
                                                      monthly="lastweekday"))


def doctest_TestCalendarEventBookingView():
    r"""A test for the resource booking view.

    We must have a schoolbell application with some resources, a
    person and his calendar with an event:

        >>> from schoolbell.app.browser.cal import CalendarEventBookingView
        >>> from schoolbell.app.security import setUpLocalAuth
        >>> from schoolbell.app.app import SchoolBellApplication
        >>> from schoolbell.app.app import Resource, Person
        >>> from schoolbell.app.cal import CalendarEvent
        >>> from zope.app.component.hooks import setSite

        >>> app = SchoolBellApplication()
        >>> directlyProvides(app, IContainmentRoot)
        >>> setUpLocalAuth(app)
        >>> setSite(app)

        >>> person = Person(u'ignas')
        >>> app['persons']['ignas'] = person

        >>> for i in range(10):
        ...     app['resources']['res' + str(i)] = Resource('res' + str(i))

        >>> event = CalendarEvent(datetime(2002, 2, 2, 2, 2),
        ...                       timedelta(hours=2), "Some event",
        ...                       unique_id="ev1")
        >>> person.calendar.addEvent(event)

    Now let's create a view for the event:


        >>> request = TestRequest()
        >>> view = CalendarEventBookingView(event, request)

        >>> view.update()
        ''

        >>> view.errors
        ()

    We should see all the resources in the form:

        >>> [resource.title for resource in view.availableResources]
        ['res0', 'res1', 'res2', 'res3', 'res4', 'res5', 'res6', 'res7', 'res8', 'res9']

    All the resources should be unbooked:

        >>> [resource.title for resource in view.availableResources
        ...                 if not view.hasBooked(resource)]
        ['res0', 'res1', 'res2', 'res3', 'res4', 'res5', 'res6', 'res7', 'res8', 'res9']

    """

class TestDailyCalendarView(unittest.TestCase):

    def test_title(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person

        view = DailyCalendarView(Person().calendar, TestRequest())
        view.update()
        self.assertEquals(view.cursor, date.today())

        view.request = TestRequest(form={'date': '2005-01-06'})
        view.update()
        self.assertEquals(view.title(), "Thursday, 2005-01-06")
        view.request = TestRequest(form={'date': '2005-01-07'})
        view.update()
        self.assertEquals(view.title(), "Friday, 2005-01-07")

    def test__setRange(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person

        person = Person("Da Boss")
        cal = person.calendar
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 16)

        def do_test(events, expected):
            view.starthour, view.endhour = 8, 19
            view._setRange(events)
            self.assertEquals((view.starthour, view.endhour), expected)

        do_test([], (8, 19))

        events = [createEvent('2004-08-16 7:00', '1min', 'workout')]
        do_test(events, (7, 19))

        events = [createEvent('2004-08-15 8:00', '1d', "long workout")]
        do_test(events, (0, 19))

        events = [createEvent('2004-08-16 20:00', '30min', "late workout")]
        do_test(events, (8, 21))

        events = [createEvent('2004-08-16 20:00', '5h', "long late workout")]
        do_test(events, (8, 24))

    def test_dayEvents(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person

        ev1 = createEvent('2004-08-12 12:00', '2h', "ev1")
        ev2 = createEvent('2004-08-12 13:00', '2h', "ev2")
        ev3 = createEvent('2004-08-12 14:00', '2h', "ev3")
        ev4 = createEvent('2004-08-11 14:00', '3d', "ev4")
        cal = Person().calendar
        for e in [ev1, ev2, ev3, ev4]:
            cal.addEvent(e)
        view = DailyCalendarView(cal, TestRequest())
        view.request = TestRequest()
        result = view.dayEvents(date(2004, 8, 12))
        expected = [ev4, ev1, ev2, ev3]
        fmt = lambda x: '[%s]' % ', '.join([e.title for e in x])
        self.assertEquals(result, expected,
                          '%s != %s' % (fmt(result), fmt(expected)))

    def test_getColumns(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person, Calendar

        person = Person(title="Da Boss")
        cal = person.calendar
        view = DailyCalendarView(cal, TestRequest())
        view.request = TestRequest()
        view.cursor = date(2004, 8, 12)

        self.assertEquals(view.getColumns(), 1)

        cal.addEvent(createEvent('2004-08-12 12:00', '2h', "Meeting"))
        self.assertEquals(view.getColumns(), 1)

        #
        #  Three events:
        #
        #  12 +--+
        #  13 |Me|+--+    <--- overlap
        #  14 +--+|Lu|+--+
        #  15     +--+|An|
        #  16         +--+
        #
        #  Expected result: 2

        cal.addEvent(createEvent('2004-08-12 13:00', '2h', "Lunch"))
        cal.addEvent(createEvent('2004-08-12 14:00', '2h', "Another meeting"))
        self.assertEquals(view.getColumns(), 2)

        #
        #  Four events:
        #
        #  12 +--+
        #  13 |Me|+--+    +--+ <--- overlap
        #  14 +--+|Lu|+--+|Ca|
        #  15     +--+|An|+--+
        #  16         +--+
        #
        #  Expected result: 3

        cal.addEvent(createEvent('2004-08-12 13:00', '2h',
                                 "Call Mark during lunch"))
        self.assertEquals(view.getColumns(), 3)

        #
        #  Events that do not overlap in real life, but overlap in our view
        #
        #    +-------------+-------------+-------------+
        #    | 12:00-12:30 | 12:30-13:00 | 12:00-12:00 |
        #    +-------------+-------------+-------------+
        #
        #  Expected result: 3

        cal.clear()
        cal.addEvent(createEvent('2004-08-12 12:00', '30min', "a"))
        cal.addEvent(createEvent('2004-08-12 12:30', '30min', "b"))
        cal.addEvent(createEvent('2004-08-12 12:00', '0min', "c"))
        self.assertEquals(view.getColumns(), 3)

    def test_getColumns_periods(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person, Calendar
        from schoolbell.calendar.utils import parse_datetime

        person = Person(title="Da Boss")
        cal = person.calendar
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)
        view.calendarRows = lambda: iter([
            ("B", parse_datetime('2004-08-12 10:00:00'), timedelta(hours=3)),
            ("C", parse_datetime('2004-08-12 13:00:00'), timedelta(hours=2)),
             ])
        cal.addEvent(createEvent('2004-08-12 09:00', '2h', "Whatever"))
        cal.addEvent(createEvent('2004-08-12 11:00', '2m', "Phone call"))
        cal.addEvent(createEvent('2004-08-12 11:10', '2m', "Phone call"))
        cal.addEvent(createEvent('2004-08-12 12:00', '2m', "Phone call"))
        cal.addEvent(createEvent('2004-08-12 12:30', '3h', "Nap"))
        self.assertEquals(view.getColumns(), 5)

    def test_getHours(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person

        person = Person(title="Da Boss")
        cal = person.calendar
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)
        view.starthour = 10
        view.endhour = 16
        result = list(view.getHours())
        self.assertEquals(result,
                          [{'duration': 60, 'time': '10:00',
                            'title': '10:00', 'cols': (None,)},
                           {'duration': 60, 'time': '11:00',
                            'title': '11:00', 'cols': (None,)},
                           {'duration': 60, 'time': '12:00',
                            'title': '12:00', 'cols': (None,)},
                           {'duration': 60, 'time': '13:00',
                            'title': '13:00', 'cols': (None,)},
                           {'duration': 60, 'time': '14:00',
                            'title': '14:00', 'cols': (None,)},
                           {'duration': 60, 'time': '15:00',
                            'title': '15:00', 'cols': (None,)},])

        ev1 = createEvent('2004-08-12 12:00', '2h', "Meeting")
        cal.addEvent(ev1)
        result = list(view.getHours())

        def clearTimeAndDuration(l):
            for d in l:
                del d['time']
                del d['duration']
            return l

        result = clearTimeAndDuration(result)
        self.assertEquals(result,
                          [{'title': '10:00', 'cols': (None,)},
                           {'title': '11:00', 'cols': (None,)},
                           {'title': '12:00', 'cols': (ev1,)},
                           {'title': '13:00', 'cols': ('',)},
                           {'title': '14:00', 'cols': (None,)},
                           {'title': '15:00', 'cols': (None,)}])

        #
        #  12 +--+
        #  13 |Me|+--+
        #  14 +--+|Lu|
        #  15 |An|+--+
        #  16 +--+
        #

        ev2 = createEvent('2004-08-12 13:00', '2h', "Lunch")
        ev3 = createEvent('2004-08-12 14:00', '2h', "Another meeting")
        cal.addEvent(ev2)
        cal.addEvent(ev3)

        result = list(view.getHours())
        self.assertEquals(clearTimeAndDuration(result),
                          [{'title': '10:00', 'cols': (None, None)},
                           {'title': '11:00', 'cols': (None, None)},
                           {'title': '12:00', 'cols': (ev1, None)},
                           {'title': '13:00', 'cols': ('', ev2)},
                           {'title': '14:00', 'cols': (ev3, '')},
                           {'title': '15:00', 'cols': ('', None)},])

        ev4 = createEvent('2004-08-11 14:00', '3d', "Visit")
        cal.addEvent(ev4)

        result = list(view.getHours())
        self.assertEquals(clearTimeAndDuration(result),
                          [{'title': '0:00', 'cols': (ev4, None, None)},
                           {'title': '1:00', 'cols': ('', None, None)},
                           {'title': '2:00', 'cols': ('', None, None)},
                           {'title': '3:00', 'cols': ('', None, None)},
                           {'title': '4:00', 'cols': ('', None, None)},
                           {'title': '5:00', 'cols': ('', None, None)},
                           {'title': '6:00', 'cols': ('', None, None)},
                           {'title': '7:00', 'cols': ('', None, None)},
                           {'title': '8:00', 'cols': ('', None, None)},
                           {'title': '9:00', 'cols': ('', None, None)},
                           {'title': '10:00', 'cols': ('', None, None)},
                           {'title': '11:00', 'cols': ('', None, None)},
                           {'title': '12:00', 'cols': ('', ev1, None)},
                           {'title': '13:00', 'cols': ('', '', ev2)},
                           {'title': '14:00', 'cols': ('', ev3, '')},
                           {'title': '15:00', 'cols': ('', '', None)},
                           {'title': '16:00', 'cols': ('', None, None)},
                           {'title': '17:00', 'cols': ('', None, None)},
                           {'title': '18:00', 'cols': ('', None, None)},
                           {'title': '19:00', 'cols': ('', None, None)},
                           {'title': '20:00', 'cols': ('', None, None)},
                           {'title': '21:00', 'cols': ('', None, None)},
                           {'title': '22:00', 'cols': ('', None, None)},
                           {'title': '23:00', 'cols': ('', None, None)}])

    def test_rowspan(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person
        view = DailyCalendarView(None, TestRequest())
        view.starthour = 10
        view.endhour = 18
        view.cursor = date(2004, 8, 12)
        view.request = TestRequest()

        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '1d', "Long")), 6)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-11 12:00', '3d', "Very")), 8)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '10min', "")), 1)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '1h+1sec', "")), 2)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 09:00', '3h', "")), 2)

    def test_rowspan_periods(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        from schoolbell.app.app import Person
        from schoolbell.calendar.utils import parse_datetime
        view = DailyCalendarView(None, TestRequest())
        view.calendarRows = lambda: iter([
            ("8", parse_datetime('2004-08-12 08:00:00'), timedelta(hours=1)),
            ("A", parse_datetime('2004-08-12 09:00:00'), timedelta(hours=1)),
            ("B", parse_datetime('2004-08-12 10:00:00'), timedelta(hours=3)),
            ("C", parse_datetime('2004-08-12 13:00:00'), timedelta(hours=2)),
            ("D", parse_datetime('2004-08-12 15:00:00'), timedelta(hours=1)),
            ("16", parse_datetime('2004-08-12 16:00:00'), timedelta(hours=1)),
            ("17", parse_datetime('2004-08-12 17:00:00'), timedelta(hours=1)),
             ])
        view.cursor = date(2004, 8, 12)
        view.starthour = 8
        view.endhour = 18

        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '1d', "Long")), 5)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-11 12:00', '3d', "Very")), 7)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '10min', "")), 1)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '1h+1sec', "")), 2)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 13:00', '2h', "")), 1)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 09:00', '3h', "")), 2)

    def doctest_snapToGrid(self):
        """Tests for DailyCalendarView.snapToGrid

        DailyCalendarView displays events in a grid.  The grid starts
        at view.starthour and ends at view.endhour, both on the same
        day (view.cursor).  Gridlines are spaced at 15 minute intervals.

            >>> from schoolbell.app.browser.cal import DailyCalendarView
            >>> view = DailyCalendarView(None, TestRequest())
            >>> view.starthour = 8
            >>> view.endhour = 18
            >>> view.cursor = date(2004, 8, 1)

        snapToGrid returns a (floating point) postition in the grid.  Topmost
        gridline is number 0 and it corresponds to starthour.

            >>> view.snapToGrid(datetime(2004, 8, 1, 8, 0))
            0.0

            >>> view.snapToGrid(datetime(2004, 8, 1, 8, 1))
            0.066...
            >>> view.snapToGrid(datetime(2004, 8, 1, 8, 7))
            0.466...
            >>> view.snapToGrid(datetime(2004, 8, 1, 8, 8))
            0.533...
            >>> view.snapToGrid(datetime(2004, 8, 1, 8, 15))
            1.0

        Timestamps before starthour are clipped to 0

            >>> view.snapToGrid(datetime(2004, 8, 1, 7, 30))
            0.0
            >>> view.snapToGrid(datetime(2004, 7, 30, 16, 30))
            0.0

        Timestamps after endhour are clipped to the bottom

            >>> view.snapToGrid(datetime(2004, 8, 1, 18, 0))
            40.0
            >>> view.snapToGrid(datetime(2004, 8, 1, 18, 20))
            40.0
            >>> view.snapToGrid(datetime(2004, 8, 2, 10, 40))
            40.0

        Corner case: starthour == 0, endhour == 24

            >>> view.starthour = 0
            >>> view.endhour = 24

            >>> view.snapToGrid(datetime(2004, 8, 1, 0, 0))
            0.0
            >>> view.snapToGrid(datetime(2004, 8, 1, 2, 0))
            8.0
            >>> view.snapToGrid(datetime(2004, 7, 30, 16, 30))
            0.0
            >>> view.snapToGrid(datetime(2004, 8, 1, 23, 55))
            95.666...
            >>> view.snapToGrid(datetime(2004, 8, 2, 10, 40))
            96.0

        """

    def test_eventTop(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        view = DailyCalendarView(None, TestRequest())
        view.starthour = 8
        view.endhour = 18
        view.cursor = date(2004, 8, 12)
        view.request = TestRequest()

        def check(dt, duration, expected):
            top = view.eventTop(createEvent(dt, duration, ""))
            self.assert_(abs(top - expected) < 0.001,
                         "%s != %s" % (top, expected))

        check('2004-08-12 08:00', '1h', 0)
        check('2004-08-12 09:00', '1h', 4)
        check('2004-08-12 10:00', '1h', 8)
        check('2004-08-12 10:15', '1h', 9)
        check('2004-08-12 10:30', '1h', 10)
        check('2004-08-12 10:45', '1h', 11)
        check('2004-08-12 10:46', '1h', 11+1/15.)
        check('2004-08-12 10:44', '1h', 11-1/15.)
        check('2004-08-11 10:00', '24h', 0)

    def test_eventHeight(self):
        from schoolbell.app.browser.cal import DailyCalendarView
        view = DailyCalendarView(None, TestRequest())
        view.starthour = 8
        view.endhour = 18
        view.cursor = date(2004, 8, 12)
        view.request = TestRequest()

        def check(dt, duration, expected):
            height = view.eventHeight(createEvent(dt, duration, ""),
                                      minheight=1)
            self.assert_(abs(height - expected) < 0.001,
                         "%s != %s" % (height, expected))

        check('2004-08-12 09:00', '0', 1)
        check('2004-08-12 09:00', '14m', 1)
        check('2004-08-12 09:00', '1h', 4)
        check('2004-08-12 10:00', '2h', 8)
        check('2004-08-12 10:00', '2h+15m', 9)
        check('2004-08-12 10:00', '2h+30m', 10)
        check('2004-08-12 10:00', '2h+45m', 11)
        check('2004-08-12 10:00', '2h+46m', 11 + 1/15.)
        check('2004-08-12 10:00', '2h+44m', 11 - 1/15.)
        check('2004-08-12 10:02', '2h+44m', 11 - 1/15.)
        check('2004-08-12 10:00', '24h+44m', 32)
        check('2004-08-11 10:00', '48h+44m', 40)
        check('2004-08-11 10:00', '24h', 8)


def doctest_CalendarViewBase():
    """Tests for CalendarViewBase.

        >>> from schoolbell.app.browser.cal import CalendarViewBase

        >>> from schoolbell.app.cal import Calendar
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)

    Set up the checkers for canEdit/canView on events:

        >>> from schoolbell.app.cal import CalendarEvent
        >>> from zope.security.checker import defineChecker, Checker
        >>> defineChecker(CalendarEvent,
        ...               Checker({'description': 'zope.Public'},
        ...                       {'description': 'zope.Public'}))

    CalendarViewBase has a method calURL used for forming links to other
    calendar views on other dates.

        >>> request = TestRequest()
        >>> view = CalendarViewBase(calendar, request)
        >>> view.cursor = date(2005, 2, 3)

        >>> view.calURL("daily")
        'http://127.0.0.1/calendar/2005-02-03'
        >>> view.calURL("monthly")
        'http://127.0.0.1/calendar/2005-02'
        >>> view.calURL("yearly")
        'http://127.0.0.1/calendar/2005'

        >>> view.calURL("daily", date(2005, 12, 13))
        'http://127.0.0.1/calendar/2005-12-13'
        >>> view.calURL("monthly", date(2005, 12, 13))
        'http://127.0.0.1/calendar/2005-12'
        >>> view.calURL("yearly", date(2007, 11, 13))
        'http://127.0.0.1/calendar/2007'

    The weekly links need some special attention:

        >>> view.calURL("weekly")
        'http://127.0.0.1/calendar/2005-w05'
        >>> view.calURL("weekly", date(2003, 12, 31))
        'http://127.0.0.1/calendar/2004-w01'
        >>> view.calURL("weekly", date(2005, 1, 1))
        'http://127.0.0.1/calendar/2004-w53'

        >>> view.calURL("quarterly")
        Traceback (most recent call last):
        ...
        ValueError: quarterly

    update() sets the cursor for the view.  If it does not find a date in
    request, it defaults to the current day:

        >>> view.update()
        >>> view.cursor == date.today()
        True

    The date can be provided in the request:

        >>> request.form['date'] = '2005-01-02'
        >>> view.update()

        >>> view.cursor
        datetime.date(2005, 1, 2)

    """


def doctest_DailyCalendarView():
    r"""Tests for DailyCalendarView.

        >>> from schoolbell.app.browser.cal import DailyCalendarView

        >>> from schoolbell.app.cal import Calendar
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = DailyCalendarView(calendar, TestRequest())

    prev(), current() and next() return links for adjacent days:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.prev()
        'http://127.0.0.1/calendar/2004-08-17'
        >>> view.next()
        'http://127.0.0.1/calendar/2004-08-19'
        >>> view.current() == 'http://127.0.0.1/calendar/%s' % date.today()
        True

    """


def doctest_WeeklyCalendarView():
    """Tests for WeeklyCalendarView.

        >>> from schoolbell.app.browser.cal import WeeklyCalendarView

        >>> from schoolbell.app.cal import Calendar
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = WeeklyCalendarView(calendar, TestRequest())

    title() forms a nice title for the calendar:

        >>> view.cursor = date(2005, 2, 3)
        >>> view.title()
        u'February, 2005 (week 5)'

    prev(), current() and next() return links for adjacent weeks:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.prev()
        'http://127.0.0.1/calendar/2004-w33'
        >>> view.next()
        'http://127.0.0.1/calendar/2004-w35'
        >>> fmt = 'http://127.0.0.1/calendar/%G-w%V'
        >>> view.current() == date.today().strftime(fmt)
        True

    getCurrentWeek is a shortcut for view.getWeek(view.cursor)

        >>> view.cursor = "works"
        >>> view.getWeek = lambda x: "really " + x
        >>> view.getCurrentWeek()
        'really works'

    """


def doctest_MonthlyCalendarView():
    """Tests for MonthlyCalendarView.

        >>> from schoolbell.app.browser.cal import MonthlyCalendarView

        >>> from schoolbell.app.cal import Calendar
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = MonthlyCalendarView(calendar, TestRequest())

    title() forms a nice title for the calendar:

        >>> view.cursor = date(2005, 2, 3)
        >>> view.title()
        u'February, 2005'

    Some helpers for are provided for use in the template:

        >>> view.dayOfWeek(date(2005, 5, 17))
        u'Tuesday'

        >>> view.weekTitle(date(2005, 5, 17))
        u'Week 20'

    prev(), current and next() return links for adjacent months:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.prev()
        'http://127.0.0.1/calendar/2004-07'
        >>> view.next()
        'http://127.0.0.1/calendar/2004-09'
        >>> dt = date.today().strftime("%Y-%m")
        >>> view.current() == 'http://127.0.0.1/calendar/%s' % dt
        True

    getCurrentWeek is a shortcut for view.getMonth(view.cursor)

        >>> view.cursor = "works"
        >>> view.getMonth = lambda x: "really " + x
        >>> view.getCurrentMonth()
        'really works'

    """


def doctest_YearlyCalendarView():
    r"""Tests for YearlyCalendarView.

        >>> from schoolbell.app.browser.cal import YearlyCalendarView

        >>> from schoolbell.app.cal import Calendar
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = YearlyCalendarView(calendar, TestRequest())

    title() forms a nice title for the calendar:

        >>> view.cursor = date(2005, 2, 3)
        >>> view.title()
        '2005'

    monthTitle() returns names of months:

        >>> view.monthTitle(date(2005, 2, 3))
        u'February'
        >>> view.monthTitle(date(2005, 8, 3))
        u'August'

    dayOfWeek() returns short names of weekdays:

        >>> view.shortDayOfWeek(date(2005, 2, 3))
        u'Thu'
        >>> view.shortDayOfWeek(date(2005, 8, 3))
        u'Wed'

    prev(), current() and next() return links for adjacent years:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.prev()
        'http://127.0.0.1/calendar/2003'
        >>> view.next()
        'http://127.0.0.1/calendar/2005'
        >>> expected = 'http://127.0.0.1/calendar/%d' % date.today().year
        >>> view.current() == expected
        True

    renderRow() renders HTML for one week of events.  It is implemented
    in python for performance reasons.

        >>> week = view.getWeek(date(2004, 2, 4))[2:4]
        >>> print view.renderRow(week, 2)
        <td class="cal_yearly_day">
        <a href="http://127.0.0.1/calendar/2004-02-04" class="cal_yearly_day">4</a>
        </td>
        <td class="cal_yearly_day">
        <a href="http://127.0.0.1/calendar/2004-02-05" class="cal_yearly_day">5</a>
        </td>

    """


def doctest_EventDeleteView():
    r"""Tests for EventDeleteView.

    We'll need a little context here:

        >>> from schoolbell.app.app import Person, PersonContainer
        >>> from schoolbell.app.cal import Calendar, CalendarEvent
        >>> from schoolbell.calendar.recurrent import DailyRecurrenceRule
        >>> container = PersonContainer()
        >>> directlyProvides(container, IContainmentRoot)
        >>> person = container['person'] = Person('person')
        >>> cal = Calendar(person)
        >>> dtstart = datetime(2005, 2, 3, 12, 15)
        >>> martyr = CalendarEvent(dtstart, timedelta(hours=3), "Martyr",
        ...                        unique_id="killme")
        >>> cal.addEvent(martyr)

        >>> innocent = CalendarEvent(dtstart, timedelta(hours=3), "Innocent",
        ...                          unique_id="leavemealone")
        >>> cal.addEvent(innocent)

    In order to deal with overlaid calendars, request.principal is adapted
    to IPerson.  To make the adaptation work, we will define a simple stub.

        >>> from schoolbell.app.interfaces import IPerson
        >>> class ConformantStub:
        ...     def __init__(self, obj):
        ...         self.obj = obj
        ...     def __conform__(self, interface):
        ...         if interface is IPerson:
        ...             return self.obj

    EventDeleteView can get rid of events for you.  Just ask:

        >>> from schoolbell.app.browser.cal import EventDeleteView
        >>> request = TestRequest(form={'event_id': 'killme',
        ...                             'date': '2005-02-03'})
        >>> view = EventDeleteView(cal, request)
        >>> view.handleEvent()

        >>> martyr in cal
        False
        >>> innocent in cal
        True

    As a side effect, you will be shown your way to the calendar view:

        >>> def redirected(request, day, person='person'):
        ...     if view.request.response.getStatus() != 302:
        ...         return False
        ...     location = view.request.response.getHeaders()['Location']
        ...     expected = ('http://127.0.0.1/%s/calendar/'
        ...                 '2005-02-%02d' % (person, day))
        ...     assert location == expected, location
        ...     return True
        >>> redirected(request, 3)
        True

    Invalid requests to delete events will be ignored, and you will be bounced
    back to where you came from:

        >>> request = TestRequest(form={'event_id': 'idontexist',
        ...                             'date': '2005-02-03'})
        >>> request.setPrincipal(ConformantStub(None))
        >>> view = EventDeleteView(cal, request)
        >>> view.handleEvent()

        >>> redirected(request, 3)
        True

    That was easy.  Now the hard part: recurrent events.  Let's create one.

        >>> dtstart = datetime(2005, 2, 3, 12, 15)
        >>> exceptions = [date(2005, 2, 4), date(2005, 2, 6)]
        >>> rrule = DailyRecurrenceRule(exceptions=exceptions)
        >>> recurrer = CalendarEvent(dtstart, timedelta(hours=3), "Recurrer",
        ...                          unique_id='rec', recurrence=rrule)
        >>> cal.addEvent(recurrer)

    Now, if we try to delete this event, the view will not know what to do,
    so it will return an event to be shown for the user.

        >>> request = TestRequest(form={'event_id': 'rec',
        ...                             'date': '2005-02-05'})
        >>> view = EventDeleteView(cal, request)
        >>> event = view.handleEvent()
        >>> event is recurrer
        True
        >>> redirected(request, 5)
        False

    The event has not been touched, because we did not issue a command.  We'll
    just check that no exceptions have been added:

        >>> cal.find('rec').recurrence.exceptions
        (datetime.date(2005, 2, 4), datetime.date(2005, 2, 6))

    We can easily return back to the daily view:

        >>> request.form['CANCEL'] = 'Cancel'
        >>> view.handleEvent()
        >>> redirected(request, 5)
        True
        >>> del request.form['CANCEL']

    OK.  First, let's try and delete only the current recurrence:

        >>> request.form['CURRENT'] = 'Current'
        >>> view.handleEvent()
        >>> redirected(request, 5)
        True

    As a result, a new exception date should have been added:

        >>> cal.find('rec').recurrence.exceptions[-1]
        datetime.date(2005, 2, 5)

    Now, if we decide to remove all exceptions in the future, the recurrence
    rule's until argument will be updated:

        >>> del request.form['CURRENT']
        >>> request.form['FUTURE'] = 'Future'
        >>> view.handleEvent()
        >>> redirected(request, 5)
        True

        >>> cal.find('rec').recurrence.until
        datetime.date(2005, 2, 4)

    Finally, let's remove the event altogether.

        >>> del request.form['FUTURE']
        >>> request.form['ALL'] = 'All'
        >>> view.handleEvent()

    The event has kicked the bucket:

        >>> cal.find('rec')
        Traceback (most recent call last):
        ...
        KeyError: 'rec'

    We will need one more short-lived event:

        >>> rrule = recurrer.recurrence
        >>> evt = CalendarEvent(dtstart, timedelta(hours=3), "Butterfly",
        ...                     unique_id='butterfly', recurrence=rrule)
        >>> cal.addEvent(evt)

    If we try to modify the event's recurrence rule and the event never
    occurs as a result, the event is removed from the calendar.  For example,
    as our event only occurs until Februrary 4th (which is an exception
    anyway), when we add an exception for the 3rd too, the event should be
    gone with the wind.

        >>> request.form = {'event_id': 'butterfly', 'date': '2005-02-03',
        ...                 'CURRENT': 'Current'}
        >>> view.handleEvent()
        >>> cal.find('butterfly')
        Traceback (most recent call last):
        ...
        KeyError: 'butterfly'

    There is also a catch with deleting future events -- both `count`
    and `until` can not be set.

        >>> rrule = DailyRecurrenceRule(count=5)
        >>> evt = CalendarEvent(dtstart, timedelta(hours=3), "Butterfly",
        ...                     unique_id='counted', recurrence=rrule)
        >>> cal.addEvent(evt)

        >>> request.form = {'event_id': 'counted', 'date': '2005-02-08',
        ...                 'FUTURE': 'Future'}
        >>> view.handleEvent()
        >>> cal.find('counted').recurrence
        DailyRecurrenceRule(1, None, datetime.date(2005, 2, 7), ())

    Overlaid events are also found and handled properly:

        >>> cal2 = Calendar() # a dummy calendar
        >>> owner = container['friend'] = Person('friend')
        >>> owner.overlaid_calendars.add(cal)
        >>> owner.overlaid_calendars.add(cal2)
        >>> request = TestRequest(form={'event_id': 'counted',
        ...                             'date': '2005-02-03'})
        >>> request.setPrincipal(ConformantStub(owner))

        >>> view = EventDeleteView(owner.calendar, request)
        >>> view.handleEvent() # doctest: +ELLIPSIS
        <schoolbell.app.cal.CalendarEvent object at 0x...>

    We have been presented with a form.  We say: nuke it.

        >>> request.form['ALL'] = 'All'
        >>> view.handleEvent()
        >>> cal.find('counted')
        Traceback (most recent call last):
        ...
        KeyError: 'counted'

    We have been redirected to the right calendar too:

        >>> redirected(request, 3, 'friend')
        True

    Note that if the context calendar's parent is different from the
    principal's calendar, overlaid events are not even scanned.

        >>> evt = CalendarEvent(dtstart, timedelta(hours=3), "Butterfly",
        ...                     unique_id='counted', recurrence=rrule)
        >>> cal.addEvent(evt)

        >>> foe = container['foe'] = Person('foe')
        >>> view.context.__parent__ = foe
        >>> del view.request.form['ALL']

        >>> print view.handleEvent()
        None

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCalendarViewBase))
    suite.addTest(unittest.makeSuite(TestDailyCalendarView))
    suite.addTest(unittest.makeSuite(TestGetRecurrenceRule))
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS))
    suite.addTest(doctest.DocTestSuite('schoolbell.app.browser.cal'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
