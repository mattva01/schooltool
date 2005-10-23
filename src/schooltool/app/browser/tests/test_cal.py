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
Tests for SchoolTool-specific calendar views.

$Id$
"""
import unittest
import calendar
from datetime import datetime, date, timedelta, time
from pytz import timezone, utc

from zope.i18n import translate
from zope.interface import directlyProvides, implements
from zope.interface.verify import verifyObject
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.tests import setup, ztapi
from zope.app.pagetemplate.simpleviewclass import SimpleViewClass
from zope.app.publisher.browser import BrowserView
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.session.interfaces import ISession

import schooltool.app
from schooltool.common import parse_datetime
from schooltool.timetable import SchooldayTemplate, SchooldaySlot
from schooltool.timetable import SequentialDaysTimetableModel
from schooltool.testing.util import NiceDiffsMixin

# Used in defining CalendarEventAddTestView
from schooltool.app.browser.cal import CalendarEventAddView
from schooltool.app.browser.cal import ICalendarEventAddForm
from schooltool.app.cal import CalendarEvent, Calendar
from schooltool.app.interfaces import ISchoolToolCalendar

# Used in defining CalendarEventEditTestView
from schooltool.app.browser.cal import CalendarEventEditView
from schooltool.app.browser.cal import ICalendarEventEditForm
from schooltool.app.browser.testing import setUp as browserSetUp, tearDown
from schooltool.testing import setup as sbsetup

# Used for the PrincipalStub
# XXX: Bad, it depends on the person package.
from schooltool.person.person import Person, PersonContainer
from schooltool.person.interfaces import IPerson
from schooltool.person.preference import getPersonPreferences
from schooltool.person.interfaces import IPersonPreferences


def dt(timestr):
    dt = parse_datetime('2004-11-05 %s:00' % timestr)
    return dt.replace(tzinfo=utc)


def setUp(test=None):
    browserSetUp(test)
    sbsetup.setupCalendaring()


def doctest_ToCalendarTraverser():
    """Tests for CalendarOwnerTraverser.

    CalendarOwnerTraverser allows you to traverse directly to the calendar
    of a calendar owner.

        >>> from schooltool.app.browser.cal import ToCalendarTraverser
        >>> person = Person()
        >>> request = TestRequest()
        >>> traverser = ToCalendarTraverser(person, request)
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

        >>> calendar = ISchoolToolCalendar(person)
        >>> traverser.publishTraverse(request, 'calendar') is calendar
        True

    We can also get the calendar as iCalendar:

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> ztapi.browserView(ISchoolToolCalendar, 'calendar.ics', BrowserView)
        >>> view = traverser.publishTraverse(request, 'calendar.ics')
        >>> view.context is ISchoolToolCalendar(traverser.context)
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

        >>> from schooltool.app.browser.cal import CalendarTraverser
        >>> from schooltool.app.cal import Calendar
        >>> cal = Calendar(None)
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

        >>> view = traverser.publishTraverse(request, '2004-05.pdf')
        monthly.pdf
        >>> request['date']
        '2004-05-01'

    The getViewByDate() method is responsible for recognizing dates.  It
    may return a view if it recognizes a date, or None.

    The yearly view is returned when only a year is provided:

        >>> traverser.getViewByDate(request, '2002', 'foo')
        'yearly.foo'
        >>> request['date']
        '2002-01-01'

    The monthly view is supported too:

        >>> traverser.getViewByDate(request, '2002-07', 'foo')
        'monthly.foo'
        >>> request['date']
        '2002-07-01'

    The weekly view can be accessed by adding 'w' in front of the week number:

        >>> traverser.getViewByDate(request, '2002-w11', 'foo')
        'weekly.foo'
        >>> request['date']
        '2002-03-11'

    The daily view is supported too:

        >>> traverser.getViewByDate(request, '2002-07-03', 'foo')
        'daily.foo'
        >>> request['date']
        '2002-07-03'

    Invalid dates are not touched:

        >>> for name in ['', 'abc', 'index.html', '', '200a', '2004-1a',
        ...              '2001-02-03-04', '2001/02/03', '2001-w3a', 'a-w2',
        ...              '1000', '3000']:
        ...     assert traverser.getHTMLViewByDate(request, name) is None
        ...     assert traverser.getViewByDate(request, name, '') is None

    getPDFViewByDate is similar to getHTMLViewByDate but returns PDF views
    for the dates.

        >>> traverser.getPDFViewByDate(request, '2002-07.pdf')
        'monthly.pdf'
        >>> request['date']
        '2002-07-01'

    We do not have a yearly PDF view (that could be huge!):

        >>> print traverser.getPDFViewByDate(request, '2002.pdf')
        None

    It only handles view names ending with '.pdf' and ignores invalid dates:

        >>> del request.form['date']
        >>> print traverser.getPDFViewByDate(request, '2002-07-03.quux')
        None
        >>> 'date' in request
        False
        >>> print traverser.getPDFViewByDate(request, '2002-1a-01.pdf')
        None
        >>> 'date' in request
        False

    If we try to look up a nonexistent view, we should get a NotFound error:

        >>> traverser.publishTraverse(request,
        ...                           'nonexistent.html') # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        NotFound: Object: <...Calendar object at ...>, name: 'nonexistent.html'

    You can traverse into calendar events by their unique id:

        >>> from schooltool.app.cal import CalendarEvent
        >>> event = CalendarEvent(datetime(2002, 2, 2, 2, 2),
        ...                       timedelta(hours=2), "Some event",
        ...                       unique_id="it's me!")
        >>> cal.addEvent(event)
        >>> traverser.publishTraverse(request, "it's me!") is event
        True

    """

def doctest_CalendarOwnerHttpTraverser():
    """Tests for CalendarOwnerHttpTraverser.

    CalendarOwnerHttpTraverser allows you to traverse directly to the calendar
    of a calendar owner.

        >>> from schooltool.app.browser.cal import CalendarOwnerHTTPTraverser
        >>> person = Person()
        >>> request = TestRequest()
        >>> traverser = CalendarOwnerHTTPTraverser(person, request)
        >>> traverser.context is person
        True
        >>> traverser.request is request
        True

    The traverser should implement IBrowserPublisher:

        >>> from zope.publisher.interfaces.browser import IBrowserPublisher
        >>> verifyObject(IBrowserPublisher, traverser)
        True

    The whole point of this class is that we can ask for the calendar:

        >>> calendar = ISchoolToolCalendar(person)
        >>> traverser.publishTraverse(request, 'calendar') is calendar
        True
        >>> traverser.publishTraverse(request, 'calendar.ics') is calendar
        True
        >>> traverser.publishTraverse(request, 'calendar.vfb') is calendar
        True

    """

def doctest_CalendarHttpTraverser():
    """Tests for CalendarHttpTraverser.

    CalendarHttpTraverser allows you to traverse directly to the calendar
    of a calendar .

        >>> from schooltool.app.browser.cal import CalendarHTTPTraverser
        >>> person = Person()
        >>> request = TestRequest()
        >>> calendar = ISchoolToolCalendar(person)
        >>> traverser = CalendarHTTPTraverser(calendar, request)
        >>> traverser.context is calendar
        True
        >>> traverser.request is request
        True

    The traverser should implement IBrowserPublisher:

        >>> from zope.publisher.interfaces.browser import IBrowserPublisher
        >>> verifyObject(IBrowserPublisher, traverser)
        True

    The whole point of this class is that we can ask for the calendar:

        >>> traverser.publishTraverse(request, 'calendar.ics') is calendar
        True
        >>> traverser.publishTraverse(request, 'calendar.vfb') is calendar
        True

    """

def doctest_EventForDisplay():
    """A wrapper for calendar events.

        >>> from schooltool.app.browser.cal import EventForDisplay
        >>> from schooltool.resource.resource import Resource
        >>> person = Person("p1")
        >>> calendar = ISchoolToolCalendar(person)
        >>> event = createEvent('2004-01-02 14:45:50', '5min', 'yawn')
        >>> calendar.addEvent(event)
        >>> request = TestRequest()
        >>> e1 = EventForDisplay(event, request, 'red', 'green', calendar, utc)

    EventForDisplay lets us access all the usual attributes

        >>> e1.dtstart.date()
        datetime.date(2004, 1, 2)
        >>> e1.dtstart.time()
        datetime.time(14, 45, 50)
        >>> e1.dtstart.tzname()
        'UTC'
        >>> e1.title
        'yawn'
        >>> e1.source_calendar is calendar
        True
        >>> e1.allday
        False

    If event is an allday event EventForDisplay has it's allday attribute set:

        >>> event.allday = True
        >>> allday_efd = EventForDisplay(event, request, 'red', 'green',
        ...                              calendar, utc)
        >>> allday_efd.allday
        True
        >>> event.allday = False

    It adds some additional attributes

        >>> e1.dtend.date()
        datetime.date(2004, 1, 2)
        >>> e1.dtend.time()
        datetime.time(14, 50, 50)
        >>> e1.dtend.tzname()
        'UTC'
        >>> e1.color1
        'red'
        >>> e1.color2
        'green'
        >>> e1.shortTitle
        'yawn'
        >>> e1.getBooker() is None
        True

    shortTitle is ellipsized if the title is long

        >>> e2 = createEvent('2004-01-02 12:00:00', '15min',
        ...                  'sleeping for a little while because I was tired')
        >>> e2 = EventForDisplay(e2, request, 'blue', 'yellow', calendar, utc)
        >>> e2.shortTitle
        'sleeping for a ...'

    Lists of EventForDisplay objects can be sorted by start time

        >>> e1 > e2
        True

    The `renderShort` method is used to render the event in the monthly
    calendar view.

        >>> print e2.renderShort().replace('&ndash;', '--')
        sleeping for a ... (12:00--12:15)

    The same CalendarEvent can be renderered for display in a particular
    timezone.

        >>> e2east = EventForDisplay(e2, request, 'blue', 'yellow', calendar,
        ...                          timezone=timezone('US/Eastern'))
        >>> print e2east.renderShort().replace('&ndash;', '--')
        sleeping for a ... (07:00--07:15)

    If the event is a booking event and the source calendar is a calendar of
    the resource we should get the booker of the event:

       >>> resource = Resource("r1")
       >>> e1.bookResource(resource)
       >>> e1.source_calendar = ISchoolToolCalendar(resource)
       >>> e1.getBooker() is person
       True

    If an event does not have a __parent__, getBooker() will return None:

        >>> e1.context.__parent__ is calendar
        True
        >>> e1.context.__parent__ = None
        >>> print e1.getBooker()
        None

    QED.  Now restore the fixture.

        >>> e1.context.__parent__ = calendar

    We should not see booked resources though:

       >>> e1.getBookedResources()
       ()

    But if we are looking at the persons calendar we should get the
    list of them:

       >>> e1.source_calendar = calendar
       >>> [resource.title for resource in  e1.getBookedResources()]
       ['r1']

    By default events display their time in UTC, the way it's stored.

        >>> e3 = createEvent('2004-01-02 12:00:00', '15min',
        ...                  'sleeping for a little while because I was tired')
        >>> e3utc = EventForDisplay(e3, request, 'blue', 'yellow', calendar,
        ...                         utc)
        >>> print e3utc.dtstarttz
        2004-01-02 12:00:00+00:00
        >>> print e3utc.dtendtz
        2004-01-02 12:15:00+00:00
        >>> e3cairo = EventForDisplay(e3, request, 'blue', 'yellow', calendar,
        ...                           timezone('Africa/Cairo'))
        >>> print e3cairo.dtstarttz
        2004-01-02 14:00:00+02:00
        >>> print e3cairo.dtendtz
        2004-01-02 14:15:00+02:00

    this is how we display it

        >>> print e3cairo.dtstarttz.strftime('%Y-%m-%d')
        2004-01-02

    """


def doctest_EventForDisplay_editLink():
    """Test for EventForDisplay.editLink.

        >>> from schooltool.app.browser.cal import EventForDisplay
        >>> from schooltool.app.cal import Calendar, CalendarEvent
        >>> event = CalendarEvent(datetime(2005, 9, 26, 21, 2),
        ...                       timedelta(hours=1), "Clickety-click",
        ...                       unique_id='xyzzy')
        >>> request = TestRequest()
        >>> color1 = color2 = None
        >>> calendar = Calendar(None)

    Some events are not editable.

        >>> e = EventForDisplay(event, request, color1, color2, calendar, utc)
        >>> print e.editLink()
        None

    Other events are

        >>> calendar.addEvent(event)
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> e = EventForDisplay(event, request, color1, color2, calendar, utc)
        >>> print e.editLink()
        http://127.0.0.1/calendar/xyzzy/edit.html?date=2005-09-26

    """


def doctest_EventForBookingDisplay():
    """A wrapper for calendar events.

        >>> from schooltool.app.browser.cal import EventForBookingDisplay
        >>> e1 = createEvent('2004-01-02 14:45:50', '5min', 'yawn')
        >>> e1 = EventForBookingDisplay(e1)

    EventForBookingDisplay lets us access all the usual attributes

        >>> e1.dtend.date()
        datetime.date(2004, 1, 2)
        >>> e1.dtend.time()
        datetime.time(14, 50, 50)
        >>> e1.dtend.tzname()
        'UTC'
        >>> e1.title
        'yawn'

    It adds some additional attributes

        >>> e1.dtend.date()
        datetime.date(2004, 1, 2)
        >>> e1.dtend.time()
        datetime.time(14, 50, 50)
        >>> e1.dtend.tzname()
        'UTC'
        >>> e1.shortTitle
        'yawn'

    shortTitle is ellipsized if the title is long

        >>> e2 = createEvent('2004-01-02 12:00:00', '15min',
        ...                  'sleeping for a little while because I was tired')
        >>> e2 = EventForBookingDisplay(e2)
        >>> e2.shortTitle
        'sleeping for a ...'

    """


def doctest_CalendarDay():
    """A calendar day is a set of events that took place on a particular day.

        >>> from schooltool.app.browser.cal import CalendarDay
        >>> day1 = CalendarDay(date(2004, 8, 5))
        >>> day1.date
        datetime.date(2004, 8, 5)
        >>> translate(day1.title)
        u'Thursday, 2004-08-05'
        >>> day1.events
        []

        >>> day2 = CalendarDay(date(2004, 7, 15), ["abc", "def"])
        >>> day2.date
        datetime.date(2004, 7, 15)
        >>> translate(day2.title)
        u'Thursday, 2004-07-15'
        >>> day2.events
        ['abc', 'def']

    You can sort a list of CalendarDay objects.

        >>> day1 > day2 and not day1 < day2
        True
        >>> day2 == CalendarDay(date(2004, 7, 15))
        True

    You can test a calendar day to see if its date is today

        >>> day = CalendarDay(date.today())
        >>> day.today()
        'today'

        >>> day = CalendarDay(date.today() - date.resolution)
        >>> day.today()
        ''

    """


def createEvent(dtstart, duration, title, **kw):
    """Create a CalendarEvent.

      >>> from schooltool.app.cal import CalendarEvent
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
    from schooltool.app.cal import CalendarEvent
    from schooltool.calendar.utils import parse_datetimetz
    if dtstart.count(':') == 0:         # YYYY-MM-DD
        dtstart = parse_datetimetz(dtstart+' 00:00:00') # add hh:mm:ss
    elif dtstart.count(':') == 1:       # YYYY-MM-DD HH:MM
        dtstart = parse_datetimetz(dtstart+':00') # add seconds
    else:                               # YYYY-MM-DD HH:MM:SS
        dtstart = parse_datetimetz(dtstart)
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


class PrincipalStub(object):

    _person = Person()

    def __conform__(self, interface):
        if interface is IPerson:
            return self._person


def registerCalendarHelperViews():
    """Register the real CalendarListView for use by other views."""
    from schooltool.app.browser.cal import CalendarListView
    from schooltool.app.browser.cal import DailyCalendarRowsView
    from schooltool.app.interfaces import ISchoolToolCalendar
    ztapi.browserView(ISchoolToolCalendar, 'calendar_list', CalendarListView)
    ztapi.browserView(ISchoolToolCalendar, 'daily_calendar_rows',
                      DailyCalendarRowsView)


def getDaysStub(start, end):
    """Stub for CalendarViewBase.getDays."""
    from schooltool.app.browser.cal import CalendarDay
    days = []
    day = start
    while day < end:
        days.append(CalendarDay(day))
        day += timedelta(1)
    return days


class TestCalendarViewBase(unittest.TestCase):
    # Legacy unit tests from SchoolTool.

    def setUp(self):
        setup.placefulSetUp()

        sbsetup.setupSessions()
        registerCalendarHelperViews()

        # Usually registered for IHavePreferences
        ztapi.provideAdapter(IPerson, IPersonPreferences,
                             getPersonPreferences)

    def tearDown(self):
        setup.placefulTearDown()

    def test_initDayCache(self):
        from schooltool.app.browser.cal import CalendarViewBase
        view = CalendarViewBase(None, TestRequest())

        view.cursor = date(2005, 6, 9)
        view.first_day_of_week = calendar.SUNDAY
        view._initDaysCache()
        self.assertEquals(view._days_cache.expensive_getDays, view._getDays)
        self.assertEquals(view._days_cache.cache_first, date(2005, 5, 1))
        self.assertEquals(view._days_cache.cache_last, date(2005, 8, 7))

        view.cursor = date(2005, 6, 9)
        view.first_day_of_week = calendar.MONDAY
        view._initDaysCache()
        self.assertEquals(view._days_cache.expensive_getDays, view._getDays)
        self.assertEquals(view._days_cache.cache_first, date(2005, 4, 25))
        self.assertEquals(view._days_cache.cache_last, date(2005, 8, 1))

    def test_update_today_by_default(self):
        from schooltool.app.browser.cal import CalendarViewBase
        request = TestRequest()
        view = CalendarViewBase(None, request)
        view.update()
        self.assertEquals(view.cursor, date.today())

    def test_update_explicit_date(self):
        from schooltool.app.browser.cal import CalendarViewBase
        request = TestRequest(form={'date': '2005-03-04'})
        view = CalendarViewBase(None, request)
        view.update()
        self.assertEquals(view.cursor, date(2005, 3, 4))

    def test_update_date_from_session(self):
        from schooltool.app.browser.cal import CalendarViewBase
        request = TestRequest()
        ISession(request)['calendar']['last_visited_day'] = date(2005, 1, 2)
        view = CalendarViewBase(None, request)
        view.inCurrentPeriod = lambda dt: False
        view.update()
        self.assertEquals(view.cursor, date(2005, 1, 2))

    # update is also tested in doctest_CalendarViewBase

    def test_update_initializes_days_cache(self):
        from schooltool.app.browser.cal import CalendarViewBase
        request = TestRequest(form={'date': '2005-03-04'})
        view = CalendarViewBase(None, request)
        view.update()
        self.assert_(view._days_cache is not None)
        first, last = view._days_cache.cache_first, view._days_cache.cache_last
        self.assert_(first <= view.cursor <= last)

    def test_dayTitle(self):
        from schooltool.app.browser.cal import CalendarViewBase

        # Usually registered for IHavePreferences
        ztapi.provideAdapter(IPerson, IPersonPreferences,
                             getPersonPreferences)

        request1 = TestRequest()
        request1.setPrincipal(PrincipalStub())
        view1 = CalendarViewBase(None, request1)
        dt = datetime(2004, 7, 1)
        self.assertEquals(view1.dayTitle(dt), "Thursday, 2004-07-01")

        request2 = TestRequest()
        request2.setPrincipal(PrincipalStub())
        self.assertEquals(view1.timezone.tzname(datetime.utcnow()), 'UTC')

        # set the dateformat preference to the long format and change the
        # timezone preference

        prefs = IPersonPreferences(request2.principal._person)
        prefs.dateformat = "%d %B, %Y"
        prefs.timezone = "US/Eastern"

        view2 = CalendarViewBase(None, request2)

        self.assertEquals(view2.dayTitle(dt), "Thursday, 01 July, 2004")
        self.assertEquals(view2.timezone.zone,
                          'US/Eastern')

    def test_prev_next(self):
        from schooltool.app.browser.cal import CalendarViewBase

        request = TestRequest()
        request.setPrincipal(PrincipalStub())
        view = CalendarViewBase(None, request)

        view.cursor = date(2004, 8, 18)
        self.assertEquals(view.prevMonth(), date(2004, 7, 1))
        self.assertEquals(view.nextMonth(), date(2004, 9, 1))
        self.assertEquals(view.prevDay(), date(2004, 8, 17))
        self.assertEquals(view.nextDay(), date(2004, 8, 19))

    def test_getWeek(self):
        import calendar as pycalendar
        from schooltool.app.browser.cal import CalendarViewBase, CalendarDay
        from schooltool.app.cal import Calendar

        request = TestRequest()
        request.setPrincipal(PrincipalStub())

        cal = Calendar(None)
        view = CalendarViewBase(cal, request)
        self.assertEquals(view.first_day_of_week, 0) # Monday by default
        self.assertEquals(view.time_fmt, '%H:%M')

        # change our preferences
        prefs = IPersonPreferences(request.principal._person)
        prefs.weekstart = pycalendar.SUNDAY
        prefs.timeformat = "%I:%M %p"

        view_sunday = CalendarViewBase(cal, request)
        self.assertEquals(view_sunday.first_day_of_week, 6)
        self.assertEquals(view_sunday.time_fmt, "%I:%M %p")

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
        from schooltool.app.browser.cal import CalendarViewBase, CalendarDay
        from schooltool.app.cal import Calendar

        request = TestRequest()
        request.setPrincipal(PrincipalStub())

        cal = Calendar(None)
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
        from schooltool.app.browser.cal import CalendarViewBase
        from schooltool.app.cal import Calendar
        cal = Calendar(None)
        request = TestRequest()
        view = CalendarViewBase(cal, request)
        view.getDays = getDaysStub
        self.do_test_getMonth(view)

    def test_getMonth_with_caching(self):
        from schooltool.app.browser.cal import CalendarViewBase
        cal = Calendar(None)
        request = TestRequest()
        view = CalendarViewBase(cal, request)

        # We can pass a list of CalendarDays to getMonth to speed it up.
        # This list must contain consecutive days only!
        days = getDaysStub(date(2004, 1, 1), date(2004, 12, 31))

        # The view now never needs to call self.getDays, so we might
        # just as well get rid of it
        def dontCallUsWellCallYou(*args):
            raise NotImplementedError, "don't call us, we'll call you"
        view.getDays = dontCallUsWellCallYou

        self.do_test_getMonth(view, days)

    def test_getMonth_caching_corner_cases(self):
        from schooltool.app.browser.cal import CalendarViewBase
        view = CalendarViewBase(None, TestRequest())
        days = getDaysStub(date(2004, 7, 27), date(2004, 12, 31))
        self.assertRaises(AssertionError,
                          view.getMonth, date(2004, 8, 11), days=days)
        days = getDaysStub(date(2004, 1, 1), date(2004, 9, 5))
        self.assertRaises(AssertionError,
                          view.getMonth, date(2004, 8, 11), days=days)
        days = getDaysStub(date(2004, 7, 26), date(2004, 9, 6))
        view.getMonth(date(2004, 8, 11), days=days)

    def do_test_getMonth(self, view, days=None):
        """Test basic functionality of getMonth.

        We want to test getMonth with the same data set irrespective
        of whether caching is used or not.
        """
        weeks = view.getMonth(date(2004, 8, 11), days=days)
        self.assertEquals(len(weeks), 6)
        bounds = [(week[0].date, week[-1].date) for week in weeks]
        self.assertEquals(bounds,
                          [(date(2004, 7, 26), date(2004, 8, 1)),
                           (date(2004, 8, 2), date(2004, 8, 8)),
                           (date(2004, 8, 9), date(2004, 8, 15)),
                           (date(2004, 8, 16), date(2004, 8, 22)),
                           (date(2004, 8, 23), date(2004, 8, 29)),
                           (date(2004, 8, 30), date(2004, 9, 5))])

        # October 2004 ends with a Sunday, so we use it to check that
        # no days from the next month are included.
        weeks = view.getMonth(date(2004, 10, 1), days=days)
        bounds = [(week[0].date, week[-1].date) for week in weeks]
        self.assertEquals(bounds[4],
                          (date(2004, 10, 25), date(2004, 10, 31)))

        # Same here, just check the previous month.
        weeks = view.getMonth(date(2004, 11, 1), days=days)
        bounds = [(week[0].date, week[-1].date) for week in weeks]
        self.assertEquals(bounds[0],
                          (date(2004, 11, 1), date(2004, 11, 7)))

    def test_getYear(self):
        from schooltool.app.browser.cal import CalendarViewBase

        request = TestRequest()
        request.setPrincipal(PrincipalStub())

        view = CalendarViewBase(None, request)
        view.getDays = getDaysStub

        def getMonthStub(dt, days=None):
            # Check that boundaries of `days` are ones that we expect
            self.assertEquals(days[0].date, date(2003, 12, 29))
            self.assertEquals(days[-1].date, date(2005, 1, 2))
            return dt
        view.getMonth = getMonthStub

        year = view.getYear(date(2004, 3, 4))
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

    def doctest_pigeonhole(self):
        r"""Test for CalendarViewBase.pigeonhole().

        Our pigeonholer operates on date intervals and CalendarDays:

            >>> from schooltool.app.browser.cal import CalendarViewBase
            >>> from schooltool.app.cal import Calendar

            >>> setup.placefulSetUp()
            >>> app = sbsetup.setupSchoolToolSite()
            >>> setup.setUpAnnotations()
            >>> registerCalendarHelperViews()
            >>> sbsetup.setupTimetabling()

            >>> calendar = Calendar(Person())
            >>> vb = CalendarViewBase(calendar, TestRequest())

        Pigeonholer returns an empty list if the interval list is empty:

            >>> vb.pigeonhole([], [])
            []

        It returns a list of (empty) lists if we will pass it a
        non-empty list of intervals and an empty list of CalendarDays:

        An interval is a tuple of 2 dates (start and end; the former
        is inclusive while the latter is exclusive):

            >>> intervals = [(date(2005, 1, 1),
            ...               date(2005, 1, 8)),
            ...              (date(2005, 1, 8),
            ...               date(2005, 1, 15))]
            >>> vb.pigeonhole(intervals, [])
            [[], []]

        Let's pigeonhole a couple of days' worth of events into
        intervals:

            >>> days = vb._getDays(date(2005, 1, 7),
            ...                    date(2005, 1, 9))

            >>> weeks = vb.pigeonhole(intervals, days)
            >>> [day.date for day in weeks[0]]
            [datetime.date(2005, 1, 7)]
            >>> [day.date for day in weeks[1]]
            [datetime.date(2005, 1, 8)]

        If intervals overlap, then common days should be included in
        all of them:

            >>> intervals = [(date(2005, 1, 1),
            ...               date(2005, 1, 9)),
            ...              (date(2005, 1, 7),
            ...               date(2005, 1, 15))]

            >>> weeks = vb.pigeonhole(intervals, days)
            >>> [day.date for day in weeks[0]]
            [datetime.date(2005, 1, 7), datetime.date(2005, 1, 8)]
            >>> [day.date for day in weeks[1]]
            [datetime.date(2005, 1, 7), datetime.date(2005, 1, 8)]

        """

    def doctest_getCalendars(self):
        """Test for CalendarViewBase.getCalendars().

            >>> setup.placelessSetUp()

        getCalendars() only delegates the task to a calendar list view.  We
        will provide a stub view to test the method.

            >>> class CalendarListViewStub(BrowserView):
            ...     def getCalendars(self):
            ...         return ['some calendar', 'another calendar']
            >>> from schooltool.app.interfaces import ISchoolToolCalendar
            >>> ztapi.browserView(ISchoolToolCalendar, 'calendar_list',
            ...                   CalendarListViewStub)

            >>> from schooltool.app.cal import Calendar
            >>> from schooltool.app.browser.cal import CalendarViewBase
            >>> view = CalendarViewBase(Calendar(None), TestRequest())

        Now, if we call the method, the output of our stub will be returned:

            >>> view.getCalendars()
            ['some calendar', 'another calendar']

        We're done:

            >>> setup.placelessTearDown()

        """

    def doctest_getCalendars_cache(self):
        """Test for CalendarViewBase.getCalendars() caching.

        Let's set up needed stubs:

            >>> class CalendarListViewStub(BrowserView):
            ...     def getCalendars(self):
            ...         return ['some calendar', 'another calendar']
            >>> from schooltool.app.interfaces import ISchoolToolCalendar
            >>> ztapi.browserView(ISchoolToolCalendar, 'calendar_list',
            ...                   CalendarListViewStub)

        The cache for calendar list is None by default:

            >>> from schooltool.app.cal import Calendar
            >>> from schooltool.app.browser.cal import CalendarViewBase
            >>> from schooltool.person.person import Person
            >>> view = CalendarViewBase(Calendar(Person()), TestRequest())

            >>> view._calendars is None
            True

        When we get the list of calendars for the first time it gets
        set:

            >>> view.getCalendars()
            ['some calendar', 'another calendar']
            >>> view._calendars
            ['some calendar', 'another calendar']

        Next call of getCalendars will return the cached value:

            >>> view._calendars.append('random calendar')
            >>> view.getCalendars()
            ['some calendar', 'another calendar', 'random calendar']

        """

    def doctest_getEvents(self):
        """Test for CalendarViewBase.getEvents

            >>> setup.placefulSetUp()
            >>> app = sbsetup.setupSchoolToolSite()
            >>> setup.setUpAnnotations()
            >>> registerCalendarHelperViews()
            >>> sbsetup.setupSessions()
            >>> sbsetup.setupTimetabling()

        CalendarViewBase.getEvents returns a list of wrapped calendar
        events.

            >>> from schooltool.app.browser.cal import CalendarViewBase
            >>> from schooltool.app.cal import Calendar
            >>> cal1 = Calendar(Person())
            >>> cal1.addEvent(createEvent('2005-02-26 19:39', '1h', 'code'))
            >>> cal1.addEvent(createEvent('2005-02-20 16:00', '1h', 'walk'))
            >>> view = CalendarViewBase(cal1, TestRequest())
            >>> view.inCurrentPeriod = lambda dt: False
            >>> for e in view.getEvents(datetime(2005, 2, 21),
            ...                         datetime(2005, 3, 1)):
            ...     print e.title
            ...     print e.dtstarttz
            code
            2005-02-26 19:39:00+00:00

        Changes in the view's timezone are reflected in the events dtstarttz

            >>> view.timezone = timezone('US/Eastern')
            >>> view.update()
            >>> for e in view.getEvents(datetime(2005, 2, 21),
            ...                         datetime(2005, 3, 1)):
            ...     print e.title
            ...     print e.dtstarttz
            code
            2005-02-26 14:39:00-05:00

            >>> view.timezone = timezone('UTC')
            >>> view.update()

        We will stub view.getCalendars to simulate overlayed calendars

            >>> cal2 = Calendar(None)
            >>> cal2.addEvent(createEvent('2005-02-27 12:00', '1h', 'rest'))
            >>> view.getCalendars = lambda:[(cal1, 'r', 'g'), (cal2, 'b', 'y')]
            >>> for e in view.getEvents(datetime(2005, 2, 21),
            ...                         datetime(2005, 3, 1)):
            ...     print e.title, '(%s)' % e.color1
            code (r)
            rest (b)

            >>> view.timezone.tzname(datetime.now())
            'UTC'

            >>> from schooltool.app.cal import CalendarEvent
            >>> for i in range(0, 24):
            ...     cal1.addEvent(CalendarEvent(datetime(2002, 2, 1, i),
            ...                       timedelta(minutes=59), "day1-" + str(i)))
            ...     cal1.addEvent(CalendarEvent(datetime(2002, 2, 2, i),
            ...                       timedelta(minutes=59), "day2-" + str(i)))
            ...     cal1.addEvent(CalendarEvent(datetime(2002, 2, 3, i),
            ...                       timedelta(minutes=59), "day3-" + str(i)))

        The default timezone for a CalendarView is UTC.

            >>> titles = []
            >>> for e in view.getEvents(datetime(2002, 2, 2),
            ...                         datetime(2002, 2, 3)):
            ...     titles.append(e.title)
            >>> titles.sort()
            >>> for title in  titles:
            ...     print title
            day2-0
            day2-1
            day2-10
            day2-11
            day2-12
            day2-13
            day2-14
            day2-15
            day2-16
            day2-17
            day2-18
            day2-19
            day2-2
            day2-20
            day2-21
            day2-22
            day2-23
            day2-3
            day2-4
            day2-5
            day2-6
            day2-7
            day2-8
            day2-9

        Now lets change the timezone to something with a negative utcoffset.

            >>> view.timezone = timezone('US/Eastern')
            >>> view.update()
            >>> view.timezone.tzname(datetime.utcnow())
            'EST'

            >>> titles = []
            >>> for e in view.getEvents(datetime(2002, 2, 2, tzinfo=utc),
            ...                         datetime(2002, 2, 3, tzinfo=utc)):
            ...     titles.append(e.title)
            >>> titles.sort()
            >>> for title in  titles:
            ...     print title
            day2-10
            day2-11
            day2-12
            day2-13
            day2-14
            day2-15
            day2-16
            day2-17
            day2-18
            day2-19
            day2-20
            day2-21
            day2-22
            day2-23
            day2-5
            day2-6
            day2-7
            day2-8
            day2-9
            day3-0
            day3-1
            day3-2
            day3-3
            day3-4

        And something with a positive offset

            >>> view.timezone = timezone('Africa/Cairo')
            >>> view.update()
            >>> view.timezone.tzname(datetime.utcnow())
            'EET'

            >>> titles = []
            >>> for e in view.getEvents(datetime(2002, 2, 2),
            ...                         datetime(2002, 2, 3)):
            ...     titles.append(e.title)
            >>> titles.sort()
            >>> for title in  titles:
            ...     print title
            day1-22
            day1-23
            day2-0
            day2-1
            day2-10
            day2-11
            day2-12
            day2-13
            day2-14
            day2-15
            day2-16
            day2-17
            day2-18
            day2-19
            day2-2
            day2-20
            day2-21
            day2-3
            day2-4
            day2-5
            day2-6
            day2-7
            day2-8
            day2-9

        We're done:

            >>> setup.placefulSetUp()

        """

    def test_getDays_cache(self):
        from schooltool.app.browser.cal import CalendarViewBase
        view = CalendarViewBase(None, TestRequest())
        view._getDays = lambda *args: ['got some computed days']

        start = date(2004, 8, 10)
        end = date(2004, 8, 16)

        assert view._days_cache is None
        days = view.getDays(start, end)
        self.assertEquals(days, ['got some computed days'])

        class DaysCacheStub:
            def getDays(self, start, end):
                return ['got some cached days here']
        view._days_cache = DaysCacheStub()

        days = view.getDays(start, end)
        self.assertEquals(days, ['got some cached days here'])

    def test_getDays(self):
        from schooltool.app.browser.cal import CalendarViewBase
        from schooltool.app.cal import Calendar
        app = sbsetup.setupSchoolToolSite()
        sbsetup.setupTimetabling()

        e0 = createEvent('2004-08-10 11:00', '1h', "e0")
        e2 = createEvent('2004-08-11 11:00', '1h', "e2")
        e3 = createEvent('2004-08-12 23:00', '4h', "e3")
        e4 = createEvent('2004-08-15 11:00', '1h', "e4")
        e5 = createEvent('2004-08-10 09:00', '3d', "e5")
        e6 = createEvent('2004-08-13 00:00', '1d', "e6")
        e7 = createEvent('2004-08-12 00:00', '1d+1sec', "e7")
        e8 = createEvent('2004-08-15 00:00', '0sec', "e8")

        cal = Calendar(Person())
        for e in [e0, e2, e3, e4, e5, e6, e7, e8]:
            cal.addEvent(e)

        request = TestRequest()
        view = CalendarViewBase(cal, request)

        start = date(2004, 8, 10)
        days = view._getDays(start, start)
        self.assertEquals(len(days), 0)

        start = date(2004, 8, 10)
        end = date(2004, 8, 16)
        days = view._getDays(start, end)

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
        days = view._getDays(start, end)
        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, start)
        self.assertEqualEventLists(days[0].events, [e5, e2])

    def test_getDays_in_timezones(self):
        from schooltool.app.browser.cal import CalendarViewBase
        from schooltool.app.cal import Calendar
        app = sbsetup.setupSchoolToolSite()
        sbsetup.setupTimetabling()

        e0 = createEvent('2004-08-10 22:00', '1h', "e0")
        e1 = createEvent('2004-08-11 02:00', '1h', "e1")
        e2 = createEvent('2004-08-11 12:00', '1h', "e2")
        e3 = createEvent('2004-08-11 22:00', '1h', "e3")
        e4 = createEvent('2004-08-12 02:00', '1h', "e4")

        cal = Calendar(Person())
        for e in [e0, e1, e2, e3, e4]:
            cal.addEvent(e)

        request = TestRequest()
        view = CalendarViewBase(cal, request)

        start = date(2004, 8, 11)
        days = view._getDays(start, start)
        self.assertEquals(len(days), 0)

        start = date(2004, 8, 11)
        end = date(2004, 8, 12)
        days = view._getDays(start, end)

        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, date(2004, 8, 11))

        self.assertEqualEventLists(days[0].events, [e1, e2, e3])

        view.timezone = timezone('US/Eastern')
        days = view._getDays(start, end)

        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, date(2004, 8, 11))

        self.assertEqualEventLists(days[0].events, [e2, e3, e4])

        view.timezone = timezone('Europe/Vilnius')
        days = view._getDays(start, end)

        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, date(2004, 8, 11))

        self.assertEqualEventLists(days[0].events, [e0, e1, e2])

        start = date(2004, 8, 12)
        end = date(2004, 8, 13)
        days = view._getDays(start, end)

        view.timezone = timezone('US/Eastern')
        days = view._getDays(start, end)

        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, date(2004, 8, 12))

        self.assertEqualEventLists(days[0].events, [])

        view.timezone = timezone('Europe/Vilnius')
        days = view._getDays(start, end)

        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, date(2004, 8, 12))

        self.assertEqualEventLists(days[0].events, [e3, e4])





    def test_getJumpToYears(self):
        from schooltool.app.cal import Calendar
        from schooltool.app.browser.cal import CalendarViewBase
        cal = Calendar(Person())
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
        from schooltool.app.cal import Calendar
        from schooltool.app.browser.cal import CalendarViewBase
        cal = Calendar(Person())
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

def doctest_CalendarEventView():
    r"""Tests for CalendarEventView.

    We'll create a simple event view.

        >>> from schooltool.app.cal import CalendarEvent
        >>> from schooltool.app.cal import Calendar
        >>> from schooltool.app.browser.cal import CalendarEventView
        >>> from schooltool.app.browser.cal import makeRecurrenceRule
        >>> cal = Calendar(Person())
        >>> event = CalendarEvent(datetime(2002, 2, 3, 12, 30),
        ...                       timedelta(minutes=59), "Event")
        >>> cal.addEvent(event)
        >>> request = TestRequest()
        >>> view = CalendarEventView(event, request)

        >>> view.start
        '12:30'
        >>> view.end
        '13:29'

    Our view has a display attribute with an EventForDisplay object of this
    event.

        >>> type(view.display)
        <class 'schooltool.app.browser.cal.EventForDisplay'>

    The display's dtstarttz and dtendtz should be datetime representations of
    view.start and view.end.

        >>> view.display.dtstarttz.time()
        datetime.time(12, 30)
        >>> view.display.dtendtz.time()
        datetime.time(13, 29)

    The display has knows about booked resources, currently there are none.

        >>> view.display.getBookedResources()
        ()

        >>> from schooltool.resource.resource import Resource
        >>> resource = Resource("r1")
        >>> event.bookResource(resource)
        >>> [r.title for r in view.display.getBookedResources()]
        ['r1']

    The view has a day attribute the provides the date and day of week:

        >>> view.day
        u'Sunday, 2002-02-03'

        >>> event2 = CalendarEvent(datetime(2004, 2, 3, 12, 30),
        ...                       timedelta(minutes=59), "Event")
        >>> cal.addEvent(event2)
        >>> request = TestRequest()
        >>> view = CalendarEventView(event2, request)
        >>> view.day
        u'Tuesday, 2004-02-03'

    """


def doctest_CalendarEventAddView_add():
    r"""Tests for CalendarEventAddView adding of new event.

    First, let's simply render the CalendarEventAddTestView.

        >>> view = CalendarEventAddTestView(Calendar(Person()), TestRequest())
        >>> view.update()

    Let's try to add an event:

        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Add'})

        >>> calendar = Calendar(Person())
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
        >>> event.dtstart.date()
        datetime.date(2004, 8, 13)
        >>> event.dtstart.time()
        datetime.time(15, 30)
        >>> event.duration
        datetime.timedelta(0, 3000)
        >>> event.location is None
        True

    We should have been redirected to the calendar view:

        >>> view.request.response.getStatus()
        302
        >>> view.request.response.getHeader('Location')
        'http://127.0.0.1/calendar'

    We can cowardly run away if we decide so, i.e., cancel our request.
    In that case we are redirected to today's calendar.

        >>> request = TestRequest(form={'CANCEL': 'Cancel'})
        >>> calendar = Calendar(Person())
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        ''
        >>> view.request.response.getStatus()
        302
        >>> location = view.request.response.getHeader('Location')
        >>> expected = 'http://127.0.0.1/calendar'
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

        >>> calendar = Calendar(Person())
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

   Lets change our timezone to US/Eastern.

        >>> request = TestRequest(form={'field.title': 'East Coast',
        ...                             'field.start_date': '2004-08-13',
        ...                             'field.start_time': '15:30',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'field.location': 'East Coast',
        ...                             'field.weekdays-empty-marker': '1',
        ...                             'UPDATE_SUBMIT': 'Add'})

        >>> calendar = Calendar(Person())
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> eastern = timezone('US/Eastern')
        >>> view.timezone = eastern
        >>> view.update()
        ''

   We handle this by taking the date and time the user enters,

        >>> request.form['field.start_date']
        '2004-08-13'
        >>> request.form['field.start_time']
        '15:30'

   We use parse_time to create a naive time object.

        >>> from schooltool.calendar.utils import parse_time
        >>> st = parse_time(request.form['field.start_time'])
        >>> sdt = datetime.combine(date(2004, 2, 13), st)
        >>> sdt = eastern.localize(sdt)
        >>> sdt.tzname()
        'EST'
        >>> sdt.time()
        datetime.time(15, 30)

    then we replace the start time with the same time in UTC, and create the
    event with the UTC version of the start time.

        >>> sdt = sdt.astimezone(utc)
        >>> sdt.tzname()
        'UTC'

    EST is -05:00 so our time stored is 5 hours greater.

        >>> sdt.time()
        datetime.time(20, 30)

    If we set the event during DST, the offset is -04:00

        >>> sdt = datetime.combine(date(2004, 5, 31), st)
        >>> sdt = eastern.localize(sdt)
        >>> sdt.tzname()
        'EDT'
        >>> sdt.time()
        datetime.time(15, 30)

        >>> sdt = sdt.astimezone(utc)
        >>> sdt.tzname()
        'UTC'

        >>> sdt.time()
        datetime.time(19, 30)

    """


def doctest_CalendarEventAddView_add_validation():
    r"""Tests for CalendarEventAddView form validation.

    Let's try to add an event without a required field:

        >>> request = TestRequest(form={'field.title': 'Hacking',
        ...                             'field.duration': '50',
        ...                             'field.recurrence.used': '',
        ...                             'field.recurrence_type': 'daily',
        ...                             'UPDATE_SUBMIT': 'Add'})

        >>> calendar = Calendar(Person())
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
        ConversionError: (u'Invalid datetime data', <...>)
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
        ConversionError: (u'Invalid integer data', <...>)
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

        >>> calendar = Calendar(Person())
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
        >>> calendar = Calendar(Person())
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
        >>> event.dtstart.date()
        datetime.date(2004, 8, 13)
        >>> event.dtstart.time()
        datetime.time(15, 30)
        >>> event.dtstart.tzname()
        'UTC'
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


        >>> calendar = Calendar(Person())
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
        >>> event.dtstart.date()
        datetime.date(2004, 8, 13)
        >>> event.dtstart.time()
        datetime.time(15, 30)
        >>> event.dtstart.tzname()
        'UTC'
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


        >>> calendar = Calendar(Person())
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
        >>> calendar = Calendar(Person())
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
        >>> calendar = Calendar(Person())
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

        >>> calendar = Calendar(Person())
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

        >>> calendar = Calendar(Person())
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

        >>> calendar = Calendar(Person())
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
        >>> calendar = Calendar(Person())
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
        >>> calendar = Calendar(Person())

        >>> request.form['field.start_date'] = ""
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> translate(view.getLastWeekDay())
        'last weekday'

        >>> request.form['field.start_date'] = "2004-10-24"
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.getLastWeekDay() is None
        True

        >>> request.form['field.start_date'] = "2004-10-25"
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> translate(view.getLastWeekDay())
        u'Last Monday'

        >>> request.form['field.start_date'] = "2004-10-31"
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> translate(view.getLastWeekDay())
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
        >>> calendar = Calendar(Person())
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occured.'
        >>> view.errors
        WidgetInputError: ('interval', 'Repeat every', )
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
        >>> calendar = Calendar(Person())
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
        >>> calendar = Calendar(Person())
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occured.'
        >>> view.errors
        MissingInputError: ('field.interval', 'Repeat every', None)
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
        >>> event.dtstart.date()
        datetime.date(2004, 9, 13)
        >>> event.dtstart.time()
        datetime.time(15, 30)
        >>> event.dtstart.tzname()
        'UTC'
        >>> event.duration
        datetime.timedelta(0, 3000)
        >>> event.location is None
        True

     Now a recurring event:

        >>> from schooltool.app.browser.cal import makeRecurrenceRule
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
        >>> event.dtstart.date()
        datetime.date(2004, 9, 19)
        >>> event.dtstart.time()
        datetime.time(15, 35)
        >>> event.dtstart.tzname()
        'UTC'
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
        >>> event.dtstart.date()
        datetime.date(2004, 9, 19)
        >>> event.dtstart.time()
        datetime.time(15, 35)
        >>> event.dtstart.tzname()
        'UTC'
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
        >>> calendar = Calendar(Person())
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
        'http://127.0.0.1/calendar'

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
        'http://127.0.0.1/calendar'

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
        'http://127.0.0.1/calendar'

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
        >>> event.dtstart.date()
        datetime.date(2004, 8, 13)
        >>> event.dtstart.time()
        datetime.time(20, 0)
        >>> event.dtstart.tzname()
        'UTC'
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
    r"""Tests for CalendarEventEditView editing of new event.

    Let's create an event:

        >>> import datetime
        >>> event = CalendarEvent(title="Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(minutes=61),
        ...                       location="Kitchen")

    And a view for the event:

        >>> request = TestRequest()
        >>> view = CalendarEventEditTestView(event, request)

    Let's check whether the default values are set properly:

        >>> view.title_widget._getFormValue()
        'Hacking'

        >>> view.start_date_widget._getFormValue()
        datetime.date(2004, 8, 13)

        >>> view.start_time_widget._getFormValue()
        '20:00'

        >>> view.duration_widget._getFormValue()
        61

        >>> view.location_widget._getFormValue()
        'Kitchen'

        >>> view.recurrence_widget._getFormValue()
        ''

    Let's create a recurrent event:

        >>> from schooltool.app.browser.cal import makeRecurrenceRule
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

        >>> view.recurrence_widget._getFormValue()
        'on'

        >>> view.interval_widget._getFormValue()
        2

        >>> view.recurrence_type_widget._getFormValue()
        'yearly'

        >>> view.range_widget._getFormValue()
        'until'

        >>> view.until_widget._getFormValue()
        '2004-01-02'

    Let's create a weekly recurrent event with exceptions:

        >>> from schooltool.app.browser.cal import makeRecurrenceRule
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

        >>> view.recurrence_widget._getFormValue()
        'on'

        >>> view.interval_widget._getFormValue()
        1

        >>> view.recurrence_type_widget._getFormValue()
        'weekly'

        >>> view.range_widget._getFormValue()
        'count'

        >>> view.count_widget._getFormValue()
        20

        >>> view.exceptions_widget._getFormValue()
        '2004-08-14\r\n2004-08-15'

        >>> view.weekdays_widget._getFormValue()
        [1, 2, 3, 4, 5, 6]


    Let's create another recurrent event:

        >>> from schooltool.app.browser.cal import makeRecurrenceRule
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

        >>> view.count_widget._getFormValue()
        5

    As well as the range:

        >>> view.range_widget._getFormValue()
        'count'

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
        from schooltool.calendar.recurrent import DailyRecurrenceRule
        from schooltool.calendar.recurrent import WeeklyRecurrenceRule
        from schooltool.calendar.recurrent import MonthlyRecurrenceRule
        from schooltool.calendar.recurrent import YearlyRecurrenceRule
        from schooltool.app.browser.cal import makeRecurrenceRule

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

    We must have a schooltool application with some resources, a
    person and his calendar with an event:

        >>> from schooltool.app.browser.cal import CalendarEventBookingView
        >>> from schooltool.resource.resource import Resource
        >>> from schooltool.app.cal import CalendarEvent

        >>> app = sbsetup.setupSchoolToolSite()

        >>> from zope.security.checker import defineChecker, Checker
        >>> defineChecker(Calendar,
        ...               Checker({'addEvent': 'zope.Public'},
        ...                       {'addEvent': 'zope.Public'}))


        >>> person = Person(u'ignas')
        >>> app['persons']['ignas'] = person

        >>> for i in range(10):
        ...     app['resources']['res' + str(i)] = Resource('res' + str(i))

        >>> event = CalendarEvent(datetime(2002, 2, 2, 2, 2),
        ...                       timedelta(hours=2), "Some event",
        ...                       unique_id="ev1")
        >>> ISchoolToolCalendar(person).addEvent(event)

    Now let's create a view for the event:

        >>> request = TestRequest()
        >>> view = CalendarEventBookingView(event, request)

        >>> view.update()
        >>> view.errors
        ()

    We should see all the resources in the form:

        >>> [resource.title for resource in view.availableResources]
        ['res0', 'res1', 'res2', 'res3', 'res4', 'res5', 'res6', 'res7', 'res8', 'res9']

    But if event belongs to a resource it should not see its owner in the list:

        >>> r_event = CalendarEvent(datetime(2002, 2, 2, 2, 2),
        ...                       timedelta(hours=2), "Some event",
        ...                       unique_id="rev")
        >>> ISchoolToolCalendar(app['resources']['res3']).addEvent(r_event)
        >>> view.context = r_event

        >>> [resource.title for resource in view.availableResources]
        ['res0', 'res1', 'res2', 'res4', 'res5', 'res6', 'res7', 'res8', 'res9']

        >>> view.context = event

    All the resources should be unbooked:

        >>> [resource.title for resource in view.availableResources
        ...                 if not view.hasBooked(resource)]
        ['res0', 'res1', 'res2', 'res3', 'res4', 'res5', 'res6', 'res7', 'res8', 'res9']

    Now let's book some resources for our event:

        >>> request = TestRequest(form={'marker-res0': '1',
        ...                             'marker-res1': '1',
        ...                             'res2': 'booked',
        ...                             'marker-res2': '1',
        ...                             'marker-res3': '1',
        ...                             'res4': 'booked',
        ...                             'marker-res4': '1',
        ...                             'marker-res5': '1',
        ...                             'marker-res6': '1',
        ...                             'marker-res7': '1',
        ...                             'marker-res8': '1',
        ...                             'marker-res9': '1',
        ...                             'UPDATE_SUBMIT': 'Set'})

        >>> view = CalendarEventBookingView(event, request)

        >>> view.update()
        ''

    A couple of resources should be booked now:

        >>> [resource.title for resource in view.availableResources
        ...                 if view.hasBooked(resource)]
        ['res2', 'res4']


    Now let's unbook a resource and book a new one:

        >>> request = TestRequest(form={'marker-res0': '1',
        ...                             'marker-res1': '1',
        ...                             'marker-res2': '1',
        ...                             'res3': 'booked',
        ...                             'marker-res3': '1',
        ...                             'res4': 'booked',
        ...                             'marker-res4': '1',
        ...                             'marker-res5': '1',
        ...                             'marker-res6': '1',
        ...                             'marker-res7': '1',
        ...                             'marker-res8': '1',
        ...                             'marker-res9': '1',
        ...                             'UPDATE_SUBMIT': 'Set'})

        >>> view = CalendarEventBookingView(event, request)

        >>> view.update()
        ''

    We should see resource 3 in the list now:

        >>> [resource.title for resource in view.availableResources
        ...                 if view.hasBooked(resource)]
        ['res3', 'res4']

    If you don't feel very brave, use the Cancel button:

        >>> request = TestRequest(form={'marker-res0': '1',
        ...                             'marker-res1': '1',
        ...                             'marker-res2': '1',
        ...                             'marker-res3': '1',
        ...                             'marker-res4': '1',
        ...                             'marker-res5': '1',
        ...                             'res5': 'booked',
        ...                             'marker-res6': '1',
        ...                             'marker-res7': '1',
        ...                             'marker-res8': '1',
        ...                             'marker-res9': '1',
        ...                             'CANCEL': 'Cancel'})

        >>> view = CalendarEventBookingView(event, request)
        >>> view.update()
        ''

    Nothing has changed, see?

        >>> [resource.title for resource in view.availableResources
        ...                 if view.hasBooked(resource)]
        ['res3', 'res4']

    And you have been redirected back to the calendar:

        >>> request.response.getHeader('Location')
        'http://127.0.0.1/persons/ignas/calendar/ev1/@@edit.html'

    The view also follows PersonPreferences timeformat and dateformat settings.
    To demonstrate these we need to setup PersonPreferences:

        >>> setup.setUpAnnotations()

        # Usually registered for IHavePreferences
        >>> ztapi.provideAdapter(IPerson, IPersonPreferences,
        ...                      getPersonPreferences)
        >>> request.setPrincipal(person)
        >>> view = CalendarEventBookingView(event, request)
        >>> view.update()
        ''

    Without the preferences set, we get the default start and end time
    formatting:

        >>> view.start
        u'2002-02-02 - 02:02'
        >>> view.end
        u'2002-02-02 - 04:02'

    We'll change the date and time formatting in the preferences and create a
    new view.  Note that we need to create a new view because 'start' and 'end'
    are set in __init__:

        >>> prefs = IPersonPreferences(person)
        >>> prefs.timeformat = '%I:%M %p'
        >>> prefs.dateformat = '%d %B, %Y'
        >>> view = CalendarEventBookingView(event, request)

    Now we can see the changes:

        >>> view.start
        u'02 February, 2002 - 02:02 AM'
        >>> view.end
        u'02 February, 2002 - 04:02 AM'

    """

def doctest_getEvents_booking():
    """Test for CalendarViewBase.getEvents when booking is involved

    CalendarViewBase.getEvents returns a list of wrapped calendar
    events.

        >>> from schooltool.app.browser.cal import CalendarViewBase
        >>> from schooltool.app.cal import Calendar
        >>> from schooltool.resource.resource import Resource

        >>> person = Person(u"frog")
        >>> calendar = ISchoolToolCalendar(person)
        >>> resource = Resource(u"mud")

        >>> event = createEvent('2005-02-26 19:39', '1h', 'code')
        >>> calendar.addEvent(event)
        >>> event.bookResource(resource)

    We will stub view.getCalendars to simulate overlayed calendars

    We can see only one instance of the event:

        >>> view = CalendarViewBase(calendar, TestRequest())
        >>> view.getCalendars = lambda: [
        ...     (calendar, 'r', 'g'),
        ...     (ISchoolToolCalendar(resource), 'b', 'y')]
        >>> for e in view.getEvents(datetime(2005, 2, 21),
        ...                         datetime(2005, 3, 1)):
        ...     print e.title, '(%s)' % e.color1
        code (r)

    Let toad book the same resource:

        >>> toad = Person(u"toad")
        >>> event = createEvent('2005-02-26 9:39', '1h', 'swim')
        >>> ISchoolToolCalendar(toad).addEvent(event)
        >>> event.bookResource(resource)

    We should see only one box for code, yet we should see swim twice:

        >>> view.getCalendars = lambda:[
        ...     (calendar, 'r', 'g'),
        ...     (ISchoolToolCalendar(resource), 'b', 'y'),
        ...     (ISchoolToolCalendar(toad), 'm', 'c')]
        >>> for e in view.getEvents(datetime(2005, 2, 21),
        ...                         datetime(2005, 3, 1)):
        ...     print e.title, '(%s)' % e.color1
        code (r)
        swim (b)
        swim (m)

    """

class TestDailyCalendarView(unittest.TestCase):

    def setUp(self):
        setup.placefulSetUp()
        self.app = sbsetup.setupSchoolToolSite()
        registerCalendarHelperViews()
        sbsetup.setupSessions()
        sbsetup.setupTimetabling()
        sbsetup.setupCalendaring()

    def tearDown(self):
        setup.placefulTearDown()

    def test_title(self):
        from schooltool.app.browser.cal import DailyCalendarView

        view = DailyCalendarView(ISchoolToolCalendar(Person()), TestRequest())
        view.update()
        self.assertEquals(view.cursor, date.today())

        view.request = TestRequest(form={'date': '2005-01-06'})
        view.update()
        self.assertEquals(view.title(), "Thursday, 2005-01-06")
        view.request = TestRequest(form={'date': '2005-01-07'})
        view.update()
        self.assertEquals(view.title(), "Friday, 2005-01-07")

    def test__setRange(self):
        from schooltool.app.browser.cal import DailyCalendarView

        person = Person("Da Boss")
        cal = ISchoolToolCalendar(person)
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

    def test__setRange_timezones(self):
        from schooltool.app.browser.cal import DailyCalendarView

        london = timezone('Europe/London')
        vilnius = timezone('Europe/Vilnius')
        eastern = timezone('US/Eastern')

        person = Person("Da Boss")
        cal = ISchoolToolCalendar(person)
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 16)

        def do_test(events, expected):
            view.starthour, view.endhour = 8, 19
            view._setRange(events)
            self.assertEquals((view.starthour, view.endhour), expected)

        for tz in (utc, london, vilnius, eastern):
            view.timezone = tz
            do_test([], (8, 19))

        view.timezone = vilnius
        events = [createEvent('2004-08-16 5:00', '60min', 'First Class')]
        do_test(events, (8, 19))

        events = [createEvent('2004-08-16 4:00', '60min', 'Before School')]
        do_test(events, (7, 19))

        view.timezone = eastern
        do_test(events, (0, 19))

        view.timezone = london
        do_test(events, (5, 19))

        view.timezone = utc
        do_test(events, (4, 19))

        events = [createEvent('2004-08-16 4:00', '60min', 'Before School'),
                    createEvent('2004-08-16 18:00', '60min', 'Last Class')]
        do_test(events, (4, 19))

        view.timezone = vilnius
        do_test(events, (7, 22))

        view.timezone = eastern
        do_test(events, (0, 19))

        view.timezone = london
        do_test(events, (5, 20))

        view.timezone = vilnius
        events = [createEvent('2004-08-16 4:00', '60min', 'Before School'),
                    createEvent('2004-08-16 18:00', '61min', 'Running Late')]
        do_test(events, (7, 23))

        view.timezone = eastern
        do_test(events, (0, 19))

        view.timezone = london
        do_test(events, (5, 21))

        events = []
        for tz in (utc, london, vilnius, eastern):
            view.timezone = tz
            do_test([], (8, 19))

        view.timezone = utc
        events = [createEvent('2004-08-16 22:00', '30min', "late workout")]
        do_test(events, (8, 23))

        # after midnight
        view.timezone = vilnius
        do_test(events, (8, 19))

        # before 19:00
        view.timezone = eastern
        do_test(events, (8, 19))

        # between 19:00 and Midnight
        view.timezone = london
        do_test(events, (8, 24))

        view.timezone = utc
        events = [createEvent('2004-08-16 22:00', '180min', "long workout")]
        do_test(events, (8, 24))

        # start after midnight
        view.timezone = vilnius
        do_test(events, (8, 19))

        # end between 19:00 and midnight
        view.timezone = eastern
        do_test(events, (8, 21))

        # end after Midnight
        view.timezone = london
        do_test(events, (8, 24))

    def test_dayEvents(self):
        from schooltool.app.browser.cal import DailyCalendarView

        ev1 = createEvent('2004-08-12 12:00', '2h', "ev1")
        ev2 = createEvent('2004-08-12 13:00', '2h', "ev2")
        ev3 = createEvent('2004-08-12 14:00', '2h', "ev3")
        ev4 = createEvent('2004-08-11 14:00', '3d', "ev4")
        cal = ISchoolToolCalendar(Person())
        for e in [ev1, ev2, ev3, ev4]:
            cal.addEvent(e)
        view = DailyCalendarView(cal, TestRequest())
        view.request = TestRequest()
        result = view.dayEvents(date(2004, 8, 12))
        expected = [ev4, ev1, ev2, ev3]
        fmt = lambda x: '[%s]' % ', '.join([e.title for e in x])
        self.assertEquals(result, expected,
                          '%s != %s' % (fmt(result), fmt(expected)))

    def test_dayEvents_cache(self):
        from schooltool.app.browser.cal import DailyCalendarView
        from schooltool.app.interfaces import ISchoolToolCalendar
        from schooltool.person.person import Person

        ev1 = createEvent('2004-08-12 12:00', '2h', "ev1")
        ev2 = createEvent('2004-08-12 13:00', '2h', "ev2")
        ev3 = createEvent('2004-08-12 14:00', '2h', "ev3")
        ev4 = createEvent('2004-08-11 14:00', '3d', "ev4")
        cal = ISchoolToolCalendar(Person())
        for e in [ev1, ev2, ev3, ev4]:
            cal.addEvent(e)
        view = DailyCalendarView(cal, TestRequest())
        view.request = TestRequest()
        # Cache is set to None when view is created
        self.assertEquals(view._day_events, None)
        result = view.dayEvents(date(2004, 8, 12))
        # Each day you look at is added to the cache
        self.assertEquals(len(view._day_events), 1)
        cached_result = view._day_events[date(2004, 8, 12)].events

        fmt = lambda x: '[%s]' % ', '.join([e.title for e in x])
        self.assertEquals(result, cached_result,
                          '%s != %s' % (fmt(result), fmt(cached_result)))

        result = view.dayEvents(date(2004, 8, 11))
        cached_result = view._day_events[
            date(2004, 8, 11)].events
        self.assertEquals(len(view._day_events), 2)
        self.assertEquals(result, cached_result,
                          '%s != %s' % (fmt(result), fmt(cached_result)))

        # If we call the function with the same arguments - we should
        # get the list that was stored in the cache
        view._day_events[date(2004, 8, 11)].events.append(ev1)
        result = view.dayEvents(date(2004, 8, 11))
        expected = [ev4, ev1]
        self.assertEquals(result, expected,
                          '%s != %s' % (fmt(result), fmt(expected)))

    def test_getColumns(self):
        from schooltool.app.browser.cal import DailyCalendarView

        person = Person(title="Da Boss")
        cal = ISchoolToolCalendar(person)
        view = DailyCalendarView(cal, TestRequest())
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

        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)
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

        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)
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

        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)
        cal.clear()
        cal.addEvent(createEvent('2004-08-12 12:00', '30min', "a"))
        cal.addEvent(createEvent('2004-08-12 12:30', '30min', "b"))
        cal.addEvent(createEvent('2004-08-12 12:00', '0min', "c"))
        self.assertEquals(view.getColumns(), 3)

    def test_getColumns_periods(self):
        from schooltool.app.browser.cal import DailyCalendarView
        from schooltool.calendar.utils import parse_datetimetz

        person = Person(title="Da Boss")
        cal = ISchoolToolCalendar(person)
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)
        view.calendarRows = lambda: iter([
            ("B", parse_datetimetz('2004-08-12 10:00:00'), timedelta(hours=3)),
            ("C", parse_datetimetz('2004-08-12 13:00:00'), timedelta(hours=2)),
             ])
        cal.addEvent(createEvent('2004-08-12 09:00', '2h', "Whatever"))
        cal.addEvent(createEvent('2004-08-12 11:00', '2m', "Phone call"))
        cal.addEvent(createEvent('2004-08-12 11:10', '2m', "Phone call"))
        cal.addEvent(createEvent('2004-08-12 12:00', '2m', "Phone call"))
        cal.addEvent(createEvent('2004-08-12 12:30', '3h', "Nap"))
        self.assertEquals(view.getColumns(), 5)

    def test_calendarRows(self):
        from schooltool.app.browser.cal import DailyCalendarView

        person = Person(title="Da Boss")
        cal = ISchoolToolCalendar(person)
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)
        view.starthour = 10
        view.endhour = 16
        result = list(view.calendarRows())
        expected = [('%d:00' % hr, datetime(2004, 8, 12, hr, tzinfo=utc),
                     timedelta(0, 3600)) for hr in range(10, 16)]
        self.assertEquals(result, expected)

    def test_getHours(self):
        from schooltool.app.browser.cal import DailyCalendarView

        person = Person(title="Da Boss")
        cal = ISchoolToolCalendar(person)
        def createView():
            view = DailyCalendarView(cal, TestRequest())
            view.cursor = date(2004, 8, 12)
            view.starthour = 10
            view.endhour = 16
            return view
        view = createView()
        result = list(view.getHours())
        self.assertEquals(result,
                          [{'duration': 60, 'time': '10:00',
                            'title': '10:00', 'cols': (None,),
                            'top': 0.0, 'height': 4.0},
                           {'duration': 60, 'time': '11:00',
                            'title': '11:00', 'cols': (None,),
                            'top': 4.0, 'height': 4.0},
                           {'duration': 60, 'time': '12:00',
                            'title': '12:00', 'cols': (None,),
                            'top': 8.0, 'height': 4.0},
                           {'duration': 60, 'time': '13:00',
                            'title': '13:00', 'cols': (None,),
                            'top': 12.0, 'height': 4.0},
                           {'duration': 60, 'time': '14:00',
                            'title': '14:00', 'cols': (None,),
                            'top': 16.0, 'height': 4.0},
                           {'duration': 60, 'time': '15:00',
                            'title': '15:00', 'cols': (None,),
                            'top': 20.0, 'height': 4.0},
                            ])

        ev1 = createEvent('2004-08-12 12:00', '2h', "Meeting")
        cal.addEvent(ev1)
        view = createView()
        result = list(view.getHours())

        def clearMisc(l):
            for d in l:
                del d['time']
                del d['duration']
                del d['top']
                del d['height']
            return l

        result = clearMisc(result)
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

        view = createView()
        result = list(view.getHours())
        self.assertEquals(clearMisc(result),
                          [{'title': '10:00', 'cols': (None, None)},
                           {'title': '11:00', 'cols': (None, None)},
                           {'title': '12:00', 'cols': (ev1, None)},
                           {'title': '13:00', 'cols': ('', ev2)},
                           {'title': '14:00', 'cols': (ev3, '')},
                           {'title': '15:00', 'cols': ('', None)},])

        ev4 = createEvent('2004-08-11 14:00', '3d', "Visit")
        cal.addEvent(ev4)

        view = createView()
        result = list(view.getHours())
        self.assertEquals(clearMisc(result),
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

    def test_getHours_allday_events(self):
        from schooltool.app.interfaces import ISchoolToolCalendar
        from schooltool.app.browser.cal import DailyCalendarView
        from schooltool.person.person import Person

        person = Person(title="Da Boss")
        cal = ISchoolToolCalendar(person)
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)
        view.starthour = 0
        view.endhour = 23
        no_allday_events = list(view.getHours())

        ev1 = createEvent('2004-08-12 14:00', '5min', "My Birthday")
        ev1.allday = True
        cal.addEvent(ev1)
        result = list(view.getHours())

        self.assertEquals(result, no_allday_events)

    def test_getHours_short_periods(self):
        from schooltool.app.browser.cal import DailyCalendarView

        # Some setup.
        person = Person(title="Da Boss")
        cal = ISchoolToolCalendar(person)
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)

        # Patch in a custom simpleCalendarRows method to test short periods.

        from schooltool.app.browser.cal import DailyCalendarRowsView
        rows_view = DailyCalendarRowsView(view.context, view.request)

        def simpleCalendarRows():
            today = datetime.combine(view.cursor, time(13, tzinfo=utc))
            durations = [0, 1800, 1351, 1349, 600, 7200]
            row_ends = [today + timedelta(seconds=sum(durations[:i+1]))
                        for i in range(1, len(durations))]

            start = today + timedelta(hours=view.starthour)
            for end in row_ends:
                duration = end - start
                yield (rows_view.rowTitle(start.hour, start.minute),
                       start, duration)
                start = end

        view.calendarRows = simpleCalendarRows

        result = list(view.getHours())
        # clean up the result
        for rowinfo in result:
            for key in rowinfo.keys():
                if key not in ('height', 'title'):
                    del rowinfo[key]
                rowinfo['height'] = round(rowinfo['height'], 4)

        expected = [{'title': '21:00', 'height': 66.0},
                    {'title': '13:30', 'height': 1.5011},
                    {'title': '', 'height': 1.4989},
                    {'title': '', 'height': 0.6667},
                    {'title': '14:25', 'height': 8.0}]
        self.assertEquals(result, expected)

    def doctest_snapToGrid(self):
        """Tests for DailyCalendarView.snapToGrid

        DailyCalendarView displays events in a grid.  The grid starts
        at view.starthour and ends at view.endhour, both on the same
        day (view.cursor).  Gridlines are spaced at 15 minute intervals.

            >>> from schooltool.app.browser.cal import DailyCalendarView
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
        from schooltool.app.browser.cal import DailyCalendarView
        from pytz import timezone
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
        check('2004-08-12 14:30', '1h', 26)
        check('2004-08-12 16:30', '1h', 34)

        #If we change the view timezone, we shif the event's on the page.
        view.timezone = timezone('US/Eastern')
        check('2004-08-12 14:30', '1h', 10)
        check('2004-08-12 16:30', '1h', 18)

    def test_eventHeight(self):
        from schooltool.app.browser.cal import DailyCalendarView
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

    def test_getAllDayEvents(self):
        """Test for DailyCalendarView.getAllDayEvents

            >>> setup.placefulSetUp()
            >>> app = sbsetup.setupSchoolToolSite()
            >>> setup.setUpAnnotations()
            >>> registerCalendarHelperViews()
            >>> sbsetup.setupSessions()
            >>> sbsetup.setupTimetabling()

        DailyCalendarView.getAllDayEvents returns a list of wrapped
        all-day calendar events for the date of the view cursor.

            >>> from schooltool.app.browser.cal import DailyCalendarView
            >>> from schooltool.app.cal import Calendar
            >>> from schooltool.person.person import Person
            >>> cal = Calendar(Person())
            >>> cal.addEvent(createEvent('2005-02-20 16:00', '1h',
            ...      'A Birthday', allday=True))
            >>> cal.addEvent(createEvent('2005-02-20 16:00', '1h', 'walk'))
            >>> view = DailyCalendarView(cal, TestRequest())

        Only all-day events are returned

            >>> view.cursor = date(2005, 2, 20)
            >>> for e in view.getAllDayEvents():
            ...     print e.title
            ...     print e.dtstarttz
            A Birthday
            2005-02-20 16:00:00+00:00

        Only events that happen on the day specified by the cursor are
        displayed:

            >>> view.cursor = date(2005, 2, 22)
            >>> [e for e in view.getAllDayEvents()]
            []

        We're done:

            >>> setup.placelessTearDown()

        """


def doctest_CalendarViewBase():
    """Tests for CalendarViewBase.

        >>> sbsetup.setupSessions()

        >>> from schooltool.app.browser.cal import CalendarViewBase
        >>> from schooltool.app.cal import Calendar
        >>> calendar = Calendar(Person())
        >>> directlyProvides(calendar, IContainmentRoot)

    Set up the checkers for canEdit/canView on events:

        >>> from schooltool.app.cal import CalendarEvent
        >>> from zope.security.checker import defineChecker, Checker
        >>> defineChecker(CalendarEvent,
        ...               Checker({'description': 'zope.Public'},
        ...                       {'description': 'zope.Public'}))

    CalendarViewBase has a method calURL used for forming links to other
    calendar views on other dates.

        >>> request = TestRequest()
        >>> view = CalendarViewBase(calendar, request)
        >>> view.inCurrentPeriod = lambda dt: False
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

    pdfURL generates links to PDFs.  It only works when calendar generation
    is enabled:

        >>> from schooltool.app.browser import pdfcal
        >>> real_pdfcal_disabled = pdfcal.disabled

        >>> pdfcal.disabled = True
        >>> print view.pdfURL()
        None

        >>> pdfcal.disabled = False

    It should only be called on subclasses which have cal_type set, so we
    will temporarily do that.

        >>> view.cal_type = 'weekly'
        >>> view.pdfURL()
        'http://127.0.0.1/calendar/2005-w05.pdf'
        >>> del view.cal_type

        >>> pdfcal.disabled = real_pdfcal_disabled 

    update() sets the cursor for the view.  If it does not find a date in
    request or the session, it defaults to the current day:

        >>> view.update()
        >>> view.cursor == date.today()
        True

    The date can be provided in the request:

        >>> request.form['date'] = '2005-01-02'
        >>> view.update()
        >>> view.cursor
        datetime.date(2005, 1, 2)

    update() stores the last visited day in the session:

        >>> from zope.app.session.interfaces import ISession
        >>> ISession(view.request)['calendar']['last_visited_day']
        datetime.date(2005, 1, 2)

    If not given a date, update() will try the last visited one from the
    session:

        >>> view.cursor = None
        >>> del request.form['date']
        >>> view.update()
        >>> view.cursor
        datetime.date(2005, 1, 2)

    It will not update the session data if inCurrentPeriod() returns True:

        >>> view.inCurrentPeriod = lambda dt: True
        >>> request.form['date'] = '2005-01-01'
        >>> view.update()
        >>> ISession(view.request)['calendar']['last_visited_day']
        datetime.date(2005, 1, 2)

    canAddEvents checks to see if the current user has addEvent permission on
    the context:

        >>> defineChecker(Calendar,
        ...               Checker({'addEvent': 'zope.Public'},
        ...                       {'addEvent': 'zope.Public'}))
        >>> view.canAddEvents()
        True

    """


def doctest_DailyCalendarView():
    r"""Tests for DailyCalendarView.

        >>> from schooltool.app.browser.cal import DailyCalendarView

        >>> from schooltool.app.cal import Calendar
        >>> calendar = Calendar(Person())
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

    inCurrentPeriod returns True for the same day only:

        >>> view.inCurrentPeriod(date(2004, 8, 18))
        True
        >>> view.inCurrentPeriod(date(2004, 8, 19))
        False
        >>> view.inCurrentPeriod(date(2004, 8, 17))
        False

    """


def doctest_WeeklyCalendarView():
    """Tests for WeeklyCalendarView.

        >>> from schooltool.app.browser.cal import WeeklyCalendarView

        >>> from schooltool.app.cal import Calendar
        >>> calendar = Calendar(Person())
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = WeeklyCalendarView(calendar, TestRequest())

    title() forms a nice title for the calendar:

        >>> view.cursor = date(2005, 2, 3)
        >>> translate(view.title())
        u'February, 2005 (week 5)'

    prev(), current() and next() return links for adjacent weeks:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.prev()
        'http://127.0.0.1/calendar/2004-w33'
        >>> view.next()
        'http://127.0.0.1/calendar/2004-w35'
        >>> fmt = 'http://127.0.0.1/calendar/%04d-w%02d'
        >>> view.current() == fmt % date.today().isocalendar()[:2]
        True

    getCurrentWeek is a shortcut for view.getWeek(view.cursor)

        >>> view.cursor = "works"
        >>> view.getWeek = lambda x: "really " + x
        >>> view.getCurrentWeek()
        'really works'

    inCurrentPeriod returns True for the same week only:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.inCurrentPeriod(date(2004, 8, 16))
        True
        >>> view.inCurrentPeriod(date(2004, 8, 22))
        True
        >>> view.inCurrentPeriod(date(2004, 8, 23))
        False
        >>> view.inCurrentPeriod(date(2004, 8, 15))
        False

    """


def doctest_MonthlyCalendarView():
    """Tests for MonthlyCalendarView.

        >>> from schooltool.app.browser.cal import MonthlyCalendarView

        >>> from schooltool.app.cal import Calendar
        >>> calendar = Calendar(Person())
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = MonthlyCalendarView(calendar, TestRequest())

    title() forms a nice title for the calendar:

        >>> view.cursor = date(2005, 2, 3)
        >>> translate(view.title())
        u'February, 2005'

    Some helpers for are provided for use in the template:

        >>> view.dayOfWeek(date(2005, 5, 17))
        u'Tuesday'

        >>> translate(view.weekTitle(date(2005, 5, 17)))
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

    inCurrentPeriod returns True for the same month only:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.inCurrentPeriod(date(2004, 8, 18))
        True
        >>> view.inCurrentPeriod(date(2004, 8, 1))
        True
        >>> view.inCurrentPeriod(date(2004, 7, 31))
        False
        >>> view.inCurrentPeriod(date(2003, 8, 18))
        False

    """


def doctest_YearlyCalendarView():
    r"""Tests for YearlyCalendarView.

        >>> from schooltool.app.browser.cal import YearlyCalendarView

        >>> from schooltool.app.cal import Calendar
        >>> calendar = Calendar(Person())
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = YearlyCalendarView(calendar, TestRequest())

    Stub out view.getCalendars so that we do not need to worry about view
    registration:

        >>> view.getCalendars = lambda: []

    title() forms a nice title for the calendar:

        >>> view.cursor = date(2005, 2, 3)
        >>> view.title()
        u'2005'

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

    If the week includes today, that is indicated in a class attribute:

        >>> week = view.getWeek(date.today())
        >>> print view.renderRow(week, date.today().month)
        <td...class="cal_yearly_day today">...

    inCurrentPeriod returns True for the same year only:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.inCurrentPeriod(date(2004, 8, 18))
        True
        >>> view.inCurrentPeriod(date(2004, 1, 1))
        True
        >>> view.inCurrentPeriod(date(2003, 12, 31))
        False
        >>> view.inCurrentPeriod(date(2005, 1, 1))
        False

    pdfURL always returns None because yearly PDF calendars are not available.

        >>> print view.pdfURL()
        None

    """


def doctest_YearlyCalendarView_initDaysCache():
    r"""Tests for YearlyCalendarView._initDaysCache.

        >>> from schooltool.app.browser.cal import YearlyCalendarView
        >>> view = YearlyCalendarView(None, TestRequest())

    _initDaysCache designates the year of self.cursor (padded to week
    boundaries) as the time for caching

        >>> view.cursor = date(2005, 6, 12)
        >>> view.first_day_of_week = calendar.SUNDAY
        >>> view._initDaysCache()
        >>> view._days_cache.expensive_getDays == view._getDays
        True
        >>> print view._days_cache.cache_first, view._days_cache.cache_last
        2004-12-26 2006-01-01

        >>> view.first_day_of_week = calendar.MONDAY
        >>> view._initDaysCache()
        >>> print view._days_cache.cache_first, view._days_cache.cache_last
        2004-12-27 2006-01-02

    When the cursor is close to the beginning/end of the year, we also have
    to include the surrounding three months (for the calendar portlet)

        >>> view.cursor = date(2005, 1, 1)
        >>> view.first_day_of_week = calendar.SUNDAY
        >>> view._initDaysCache()
        >>> print view._days_cache.cache_first, view._days_cache.cache_last
        2004-11-28 2006-01-01

    """


def doctest_AtomCalendarView():
    r"""Tests for AtomCalendarView.

    Some setup:

        >>> setup.placefulSetUp()
        >>> app = sbsetup.setupSchoolToolSite()
        >>> sbsetup.setupTimetabling()
        >>> registerCalendarHelperViews()

        >>> from schooltool.app.browser.cal import AtomCalendarView

        >>> from schooltool.app.cal import Calendar
        >>> from schooltool.app.browser.cal import CalendarDay
        >>> person = Person()
        >>> calendar = Calendar(person)
        >>> directlyProvides(person, IContainmentRoot)

    Populate the calendar:

        >>> lastweek = CalendarEvent(datetime.now().replace(hour=12) -
        ...                          timedelta(8),
        ...                          timedelta(hours=3), "Last Week")
        >>> monday_date = (datetime.now().replace(hour=12) -
        ...                timedelta(datetime.now().weekday()))
        >>> tuesday_date = monday_date + timedelta(1)
        >>> monday = CalendarEvent(monday_date,
        ...                        timedelta(hours=3), "Today")
        >>> tuesday = CalendarEvent(tuesday_date,
        ...                         timedelta(hours=3), "Tomorrow")
        >>> calendar.addEvent(lastweek)
        >>> calendar.addEvent(monday)
        >>> calendar.addEvent(tuesday)

        >>> view = AtomCalendarView(calendar, TestRequest())
        >>> events = []
        >>> for day in view.getCurrentWeek():
        ...     for event in day.events:
        ...         events.append(event)

    getCurrentWeek() returns the current week as CalendarDays.  The even
    lastweek should not show up here.

        >>> isinstance(view.getCurrentWeek()[0], CalendarDay)
        True
        >>> len(events)
        2

    create ISO8601 date format for Atom spec
    TODO: this should probably go in schooltool.calendar.utils

        >>> dt = datetime(2005, 03, 29, 15, 33, 22)
        >>> view.w3cdtf_datetime(dt)
        '2005-03-29T15:33:22Z'

    this is a tricky thing to test, it should return datetime.now() in ISO8601

        >>> len(view.w3cdtf_datetime_now())
        20

    for now, we know its always UTC so it should end with Z

        >>> view.w3cdtf_datetime_now()[-1]
        'Z'

        >>> setup.placelessTearDown()

    """


def doctest_EventDeleteView():
    r"""Tests for EventDeleteView.

    We'll need a little context here:

        >>> from schooltool.app.cal import Calendar, CalendarEvent
        >>> from schooltool.calendar.recurrent import DailyRecurrenceRule
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

        >>> class ConformantStub:
        ...     def __init__(self, obj):
        ...         self.obj = obj
        ...     def __conform__(self, interface):
        ...         if interface is IPerson:
        ...             return self.obj

    EventDeleteView can get rid of events for you.  Just ask:

        >>> from schooltool.app.browser.cal import EventDeleteView
        >>> request = TestRequest(form={'event_id': 'killme',
        ...                             'date': '2005-02-03'})
        >>> view = EventDeleteView(cal, request)
        >>> view.handleEvent()

        >>> martyr in cal
        False
        >>> innocent in cal
        True

    As a side effect, you will be shown your way to the calendar view:

        >>> def redirected(request, person='person'):
        ...     if view.request.response.getStatus() != 302:
        ...         return False
        ...     location = view.request.response.getHeader('Location')
        ...     expected = 'http://127.0.0.1/%s/calendar' % (person, )
        ...     assert location == expected, location
        ...     return True
        >>> redirected(request)
        True

    Invalid requests to delete events will be ignored, and you will be bounced
    back to where you came from:

        >>> request = TestRequest(form={'event_id': 'idontexist',
        ...                             'date': '2005-02-03'})
        >>> request.setPrincipal(ConformantStub(None))
        >>> view = EventDeleteView(cal, request)
        >>> view.handleEvent()

        >>> redirected(request)
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
        >>> redirected(request)
        False

    The event has not been touched, because we did not issue a command.  We'll
    just check that no exceptions have been added:

        >>> cal.find('rec').recurrence.exceptions
        (datetime.date(2005, 2, 4), datetime.date(2005, 2, 6))

    We can easily return back to the daily view:

        >>> request.form['CANCEL'] = 'Cancel'
        >>> view.handleEvent()
        >>> redirected(request)
        True
        >>> del request.form['CANCEL']

    OK.  First, let's try and delete only the current recurrence:

        >>> request.form['CURRENT'] = 'Current'
        >>> view.handleEvent()
        >>> redirected(request)
        True

    As a result, a new exception date should have been added:

        >>> cal.find('rec').recurrence.exceptions[-1]
        datetime.date(2005, 2, 5)

    Now, if we decide to remove all exceptions in the future, the recurrence
    rule's until argument will be updated:

        >>> del request.form['CURRENT']
        >>> request.form['FUTURE'] = 'Future'
        >>> view.handleEvent()
        >>> redirected(request)
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

    Overlaid events should have their removal links pointing to their
    source calendars so they are not handled:

        >>> cal2 = Calendar(Person()) # a dummy calendar
        >>> owner = container['friend'] = Person('friend')
        >>> info = owner.overlaid_calendars.add(cal)
        >>> info = owner.overlaid_calendars.add(cal2)
        >>> request = TestRequest(form={'event_id': 'counted',
        ...                             'date': '2005-02-03'})
        >>> request.setPrincipal(ConformantStub(owner))

        >>> view = EventDeleteView(ISchoolToolCalendar(owner), request)
        >>> print view.handleEvent()
        None


    Note that if the context calendar's parent is different from the
    principal's calendar, overlaid events are not even scanned.

        >>> foe = container['foe'] = Person('foe')
        >>> view.context.__parent__ = foe

        >>> print view.handleEvent()
        None

    """


class TestDailyCalendarRowsView(NiceDiffsMixin, unittest.TestCase):

    def setUp(self):
        setUp()
        sbsetup.setupCalendaring()

        # set up adaptation (the view checks user preferences)
        from schooltool.person.preference import getPersonPreferences
        from schooltool.person.interfaces import IPersonPreferences
        from schooltool.person.interfaces import IHavePreferences
        from schooltool.person.person import Person
        ztapi.provideAdapter(Person, IPersonPreferences, getPersonPreferences)

        # set up the site
        app = sbsetup.setupSchoolToolSite()

        self.person = app['persons']['person'] = Person('person')

        # set up the timetable schema
        days = ['A', 'B', 'C']
        schema = self.createSchema(days,
                                   ['1', '2', '3', '4'],
                                   ['1', '2', '3', '4'],
                                   ['1', '2', '3', '4'])
        template = SchooldayTemplate()
        template.add(SchooldaySlot(time(8, 0), timedelta(hours=1)))
        template.add(SchooldaySlot(time(10, 15), timedelta(hours=1)))
        template.add(SchooldaySlot(time(11, 30), timedelta(hours=1)))
        template.add(SchooldaySlot(time(12, 30), timedelta(hours=2)))
        schema.model = SequentialDaysTimetableModel(days, {None: template})

        app['ttschemas']['default'] = schema

        # set up terms
        from schooltool.timetable.term import Term
        app['terms']['term'] = term = Term("Some term", date(2004, 9, 1),
                                           date(2004, 12, 31))
        term.add(date(2004, 11, 5))

    def tearDown(self):
        tearDown()

    def createSchema(self, days, *periods_for_each_day):
        """Create a timetable schema."""
        from schooltool.timetable.schema import TimetableSchema
        from schooltool.timetable.schema import TimetableSchemaDay
        schema = TimetableSchema(days, title="A Schema")
        for day, periods in zip(days, periods_for_each_day):
            schema[day] = TimetableSchemaDay(list(periods))
        return schema

    def test_calendarRows(self):
        from schooltool.app.browser.cal import DailyCalendarRowsView
        from schooltool.app.security import Principal

        request = TestRequest()
        principal = Principal('person', 'Some person', person=self.person)
        request.setPrincipal(principal)
        view = DailyCalendarRowsView(ISchoolToolCalendar(self.person), request)
        result = list(view.calendarRows(date(2004, 11, 5), 8, 19))

        expected = [("1", dt('08:00'), timedelta(hours=1)),
                    ("9:00", dt('09:00'), timedelta(hours=1)),
                    ("10:00", dt('10:00'), timedelta(minutes=15)),
                    ("2", dt('10:15'), timedelta(hours=1)),
                    ("11:15", dt('11:15'), timedelta(minutes=15)),
                    ("3", dt('11:30'), timedelta(hours=1)),
                    ("4", dt('12:30'), timedelta(hours=2)),
                    ("14:30", dt('14:30'), timedelta(minutes=30)),
                    ("15:00", dt('15:00'), timedelta(hours=1)),
                    ("16:00", dt('16:00'), timedelta(hours=1)),
                    ("17:00", dt('17:00'), timedelta(hours=1)),
                    ("18:00", dt('18:00'), timedelta(hours=1))]

        self.assertEquals(result, expected)

    def test_calendarRows_no_periods(self):
        from schooltool.app.browser.cal import DailyCalendarRowsView
        from schooltool.person.preference import getPersonPreferences
        from schooltool.app.security import Principal

        prefs = getPersonPreferences(self.person)
        prefs.cal_periods = False # do not show periods
        request = TestRequest()
        principal = Principal('person', 'Some person', person=self.person)
        request.setPrincipal(principal)
        view = DailyCalendarRowsView(ISchoolToolCalendar(self.person), request)

        result = list(view.calendarRows(date(2004, 11, 5), 8, 19))

        expected = [("%d:00" % i, dt('%d:00' % i), timedelta(hours=1))
                    for i in range(8, 19)]
        self.assertEquals(result, expected)

    def test_calendarRows_default(self):
        from schooltool.app.browser.cal import DailyCalendarRowsView

        request = TestRequest()
        # do not set the principal
        view = DailyCalendarRowsView(ISchoolToolCalendar(self.person), request)
        result = list(view.calendarRows(date(2004, 11, 5), 8, 19))

        # the default is not to show periods
        expected = [("%d:00" % i, dt('%d:00' % i), timedelta(hours=1))
                    for i in range(8, 19)]
        self.assertEquals(result, expected)


def doctest_CalendarSTOverlayView():
    r"""Tests for CalendarSTOverlayView

     Some setup:

        >>> sbsetup.setupCalendaring()

        >>> from zope.component import provideAdapter
        >>> from schooltool.app.app import ShowTimetables
        >>> provideAdapter(ShowTimetables)

        >>> from zope.interface import classImplements
        >>> from zope.app.annotation.interfaces import IAttributeAnnotatable
        >>> from schooltool.app.overlay import CalendarOverlayInfo
        >>> classImplements(CalendarOverlayInfo, IAttributeAnnotatable)

        >>> from schooltool.app.browser.cal import CalendarSTOverlayView
        >>> View = SimpleViewClass('../templates/calendar_overlay.pt',
        ...                        bases=(CalendarSTOverlayView,))

    CalendarOverlayView is a view on anything.

        >>> context = object()
        >>> request = TestRequest()
        >>> view = View(context, request)

    It renders to an empty string unless its context is the calendar of the
    authenticated user

        >>> view()
        u'\n'

    If you are an authenticated user looking at your own calendar, this view
    renders a calendar selection portlet.

        >>> from schooltool.group.group import Group
        >>> from schooltool.person.person import Person
        >>> from schooltool.course.course import Course
        >>> from schooltool.course.section import Section
        >>> from schooltool.app.security import Principal
        >>> app = sbsetup.setupSchoolToolSite()
        >>> person = app['persons']['whatever'] = Person('fred')
        >>> group1 = app['groups']['g1'] = Group(title="Group 1")
        >>> group2 = app['groups']['g2'] = Group(title="Group 2")
        >>> history = app['courses']['c1'] = Course(title="History")
        >>> section = app['sections']['s1'] = Section()
        >>> history.sections.add(section)

        >>> from schooltool.app.interfaces import IShowTimetables
        >>> info = person.overlaid_calendars.add(
        ...     ISchoolToolCalendar(group1), show=True)
        >>> IShowTimetables(info).showTimetables = False
        >>> info = person.overlaid_calendars.add(
        ...     ISchoolToolCalendar(group2), show=False)
        >>> info = person.overlaid_calendars.add(
        ...     ISchoolToolCalendar(section), show=False)

        >>> request = TestRequest()
        >>> request.setPrincipal(Principal('id', 'title', person))
        >>> view = View(ISchoolToolCalendar(person), request)

        >>> print view()
        <div id="portlet-calendar-overlay" class="portlet">
        ...
        ...<input type="checkbox" checked="checked" disabled="disabled" />...
        ...<input type="checkbox" name="my_timetable"
                  checked="checked" />...
        ...My Calendar...
        ...
        ...<input type="checkbox" name="overlay:list"
                  checked="checked" value="/groups/g1" />...
        ...<input type="checkbox"
                  name="overlay_timetables:list"
                  value="/groups/g1" />...
        ...
        ...<input type="checkbox" name="overlay:list"
                  value="/groups/g2" />...
        ...<input type="checkbox" name="overlay_timetables:list"
                  checked="checked" value="/groups/g2" />...
        ...<td style="width: 100%">Group 2</td>...
        ...
        ...<input type="checkbox" name="overlay:list"
                  value="/sections/s1" />...
        ...<input type="checkbox" name="overlay_timetables:list"
                  checked="checked" value="/sections/s1" />...
        ...<td style="width: 100%"> -- History</td>...
        ...
        </div>

    If the request has 'OVERLAY_APPLY', CalendarOverlayView applies your
    changes

        >>> request.form['overlay'] = [u'/groups/g2']
        >>> request.form['overlay_timetables'] = [u'/groups/g1']
        >>> request.form['OVERLAY_APPLY'] = u"Apply"
        >>> print view()
        <div id="portlet-calendar-overlay" class="portlet">
        ...
        ...<input type="checkbox" checked="checked" disabled="disabled" />...
        ...<input type="checkbox" name="my_timetable" />...
        ...My Calendar...
        ...
        ...<input type="checkbox" name="overlay:list"
                  value="/groups/g1" />...
        ...<input type="checkbox"
                  name="overlay_timetables:list"
                  checked="checked" value="/groups/g1" />...
        ...
        ...<input type="checkbox" name="overlay:list"
                  checked="checked" value="/groups/g2" />...
        ...<input type="checkbox" name="overlay_timetables:list"
                  value="/groups/g2" />...
        ...
        </div>

    It also redirects you to request.URL:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    There are two reasons for the redirect: first, part of the page template
    just rendered might have become invalid when calendar overlay selection
    changed, second, this lets the user refresh the page without having to
    experience confirmation dialogs that say "Do you want to POST this form
    again?".

    If the request has 'OVERLAY_MORE', CalendarOverlayView redirects to
    calendar_selection.html

        >>> request = TestRequest()
        >>> request.setPrincipal(Principal('id', 'title', person))
        >>> request.form['OVERLAY_MORE'] = u"More..."
        >>> view = View(ISchoolToolCalendar(person), request)
        >>> content = view()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/persons/fred/calendar_selection.html?nexturl=http%3A//127.0.0.1'

    """


def doctest_CalendarListView(self):
    """Tests for CalendarListView.

    This view only has the getCalendars() method.

    The difference between this view and the one in SchoolBell is that this
    view knows about timetables and may return timetable calendars as well.
    The color of each timetable calendar is the same as of the corresponding
    personal calendar.

    CalendarListView.getCalendars returns a list of calendars that
    should be displayed.  This list always includes the context of
    the view, but it may also include other calendars as well.

    Som initial setup:

        >>> sbsetup.setupCalendaring()

    A handful of useful stubs:

        >>> class CalendarStub:
        ...     def __init__(self, title):
        ...         self.title = title
        ...     def _getParent(self):
        ...         return PersonStub(self.title, self)
        ...     __parent__ = property(_getParent)

        >>> from zope.interface import implements
        >>> from schooltool.app.interfaces import IShowTimetables
        >>> class OverlayInfoStub:
        ...     implements(IShowTimetables)
        ...
        ...     def __init__(self, title, color1, color2,
        ...                  show=True, showTimetables=True):
        ...         self.calendar = CalendarStub(title)
        ...         self.color1 = color1
        ...         self.color2 = color2
        ...         self.show = show
        ...         self.showTimetables = showTimetables

        >>> from schooltool.person.interfaces import IPersonPreferences
        >>> from schooltool.app.interfaces import IHaveCalendar
        >>> from schooltool.app.cal import CALENDAR_KEY
        >>> from zope.interface import implements
        >>> from zope.app.annotation.interfaces import IAttributeAnnotatable
        >>> from schooltool.timetable.interfaces import ITimetables
        >>> class PersonStub:
        ...     implements(IAttributeAnnotatable, IHaveCalendar, ITimetables)
        ...     def __init__(self, title, calendar=None):
        ...         self.title = title
        ...         self.__annotations__= {CALENDAR_KEY: calendar}
        ...     def makeTimetableCalendar(self):
        ...         return CalendarStub(self.title + ' (timetable)')
        ...     def __conform__(self, interface):
        ...         if interface is IPersonPreferences:
        ...             return PreferenceStub()
        ...     overlaid_calendars = [
        ...         OverlayInfoStub('Other Calendar', 'red', 'blue',
        ...                         True, False),
        ...         OverlayInfoStub('Another Calendar', 'green', 'red',
        ...                         False, True),
        ...         OverlayInfoStub('Interesting Calendar', 'yellow', 'white',
        ...                         True, True),
        ...         OverlayInfoStub('Boring Calendar', 'brown', 'magenta',
        ...                         False, False)]

        >>> class PreferenceStub:
        ...     def __init__(self):
        ...         self.weekstart = pycalendar.MONDAY
        ...         self.timeformat = "%H:%M"
        ...         self.dateformat = "YYYY-MM-DD"
        ...         self.timezone = 'UTC'

    A simple check:

        >>> from schooltool.app.browser.cal import CalendarListView
        >>> import calendar as pycalendar
        >>> calendar = CalendarStub('My Calendar')
        >>> request = TestRequest()
        >>> view = CalendarListView(calendar, request)
        >>> for c, col1, col2 in view.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        My Calendar (#9db8d2, #7590ae)
        My Calendar (timetable) (#9db8d2, #7590ae)

    If the authenticated user is looking at his own calendar, then
    a list of overlaid calendars is taken into consideration

        >>> from schooltool.person.interfaces import IPerson
        >>> class PrincipalStub:
        ...     def __init__(self):
        ...         self.person = PersonStub('x', calendar=calendar)
        ...     def __conform__(self, interface):
        ...         if interface is IPerson:
        ...             return self.person
        >>> principal = PrincipalStub()
        >>> request.setPrincipal(principal)

        >>> for c, col1, col2 in view.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        My Calendar (#9db8d2, #7590ae)
        My Calendar (timetable) (#9db8d2, #7590ae)
        Other Calendar (red, blue)
        Another Calendar (timetable) (green, red)
        Interesting Calendar (yellow, white)
        Interesting Calendar (timetable) (yellow, white)

    If the person has the current timetable display unchecked, the composite
    timetable calendar is not included in the list:

        >>> from zope.app.annotation.interfaces import IAnnotations
        >>> annotations = IAnnotations(principal.person)
        >>> from schooltool.app.browser.cal import CalendarSTOverlayView
        >>> annotations[CalendarSTOverlayView.SHOW_TIMETABLE_KEY] = False

        >>> for c, col1, col2 in view.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        My Calendar (#9db8d2, #7590ae)
        Other Calendar (red, blue)
        Another Calendar (timetable) (green, red)
        Interesting Calendar (yellow, white)
        Interesting Calendar (timetable) (yellow, white)

        >>> annotations[CalendarSTOverlayView.SHOW_TIMETABLE_KEY] = True

    Only the timetable is overlaid if the user is looking at someone else's
    calendar:

        >>> view = CalendarListView(CalendarStub('Some Calendar'), request)
        >>> for c, col1, col2 in view.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        Some Calendar (#9db8d2, #7590ae)
        Some Calendar (timetable) (#9db8d2, #7590ae)

    """


def doctest_DaysCache():
    """Unit tests for DaysCache.

    We will need a pretend expensive computation function that returns
    a list of dates.  Since it is expensive, we want to see when exactly
    it gets called.

        >>> from schooltool.app.browser.cal import CalendarDay
        >>> def expensive_getDays(first, last):
        ...     print "Computing days from %s to %s" % (first, last)
        ...     return getDaysStub(first, last)

    Let's create a DaysCache and specify an initial date range for caching.

        >>> from schooltool.app.browser.cal import DaysCache
        >>> cache = DaysCache(expensive_getDays, date(2005, 6, 7),
        ...                   date(2005, 7, 9))

        >>> print cache.cache_first, cache.cache_last
        2005-06-07 2005-07-09

    Extending by the same interval changes nothing

        >>> cache.extend(date(2005, 6, 7), date(2005, 7, 9))
        >>> print cache.cache_first, cache.cache_last
        2005-06-07 2005-07-09

    We can extend it by a few days on both ends

        >>> cache.extend(date(2005, 6, 3), date(2005, 7, 4))
        >>> print cache.cache_first, cache.cache_last
        2005-06-03 2005-07-09

        >>> cache.extend(date(2005, 6, 11), date(2005, 7, 12))
        >>> print cache.cache_first, cache.cache_last
        2005-06-03 2005-07-12

    If we call getDays for a range outside the caching range, the expensive
    function gets called and its result is returned.

        >>> days = cache.getDays(date(2005, 6, 1), date(2005, 6, 3))
        Computing days from 2005-06-01 to 2005-06-03
        >>> [str(day.date) for day in days]
        ['2005-06-01', '2005-06-02']

    If we do call getDays for a subset of the caching range, the expensive
    function gets called (once) for the whole range, and subsequent calls
    do not invoke any expensive computations.

        >>> days = cache.getDays(date(2005, 6, 7), date(2005, 6, 9))
        Computing days from 2005-06-03 to 2005-07-12
        >>> [str(day.date) for day in days]
        ['2005-06-07', '2005-06-08']

        >>> days = cache.getDays(date(2005, 7, 7), date(2005, 7, 9))
        >>> [str(day.date) for day in days]
        ['2005-07-07', '2005-07-08']

    Corner case: the whole range

        >>> days = cache.getDays(date(2005, 6, 3), date(2005, 7, 12))
        >>> [str(day.date) for day in days[:2] + days[-2:]]
        ['2005-06-03', '2005-06-04', '2005-07-10', '2005-07-11']

    We can we call getDays for a range outside the caching range, if we
    need to.

        >>> days = cache.getDays(date(2005, 7, 12), date(2005, 7, 14))
        Computing days from 2005-07-12 to 2005-07-14
        >>> [str(day.date) for day in days]
        ['2005-07-12', '2005-07-13']

    You can also call getDays with date ranges overlapping the caching
    interval, but you'll get no benefit from that.

        >>> days = cache.getDays(date(2005, 6, 1), date(2005, 6, 4))
        Computing days from 2005-06-01 to 2005-06-04
        >>> [str(day.date) for day in days]
        ['2005-06-01', '2005-06-02', '2005-06-03']

        >>> days = cache.getDays(date(2005, 7, 11), date(2005, 7, 14))
        Computing days from 2005-07-11 to 2005-07-14
        >>> [str(day.date) for day in days]
        ['2005-07-11', '2005-07-12', '2005-07-13']

    You will get an assertion error if you try to pass in an invalid date range

        >>> cache.getDays(date(2005, 7, 12), date(2005, 7, 11))
        Traceback (most recent call last):
          ...
        AssertionError: invalid date range: 2005-07-12..2005-07-11

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCalendarViewBase))
    suite.addTest(unittest.makeSuite(TestDailyCalendarView))
    suite.addTest(unittest.makeSuite(TestGetRecurrenceRule))
    suite.addTest(unittest.makeSuite(TestDailyCalendarRowsView))
    suite.addTest(doctest.DocTestSuite(
        setUp=setUp, tearDown=tearDown,
        optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF|
                    doctest.NORMALIZE_WHITESPACE|
                    doctest.REPORT_ONLY_FIRST_FAILURE))
    suite.addTest(doctest.DocTestSuite('schooltool.app.browser.cal'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
