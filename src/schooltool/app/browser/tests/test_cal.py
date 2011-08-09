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
"""
import unittest
import doctest
import calendar
from datetime import datetime, date, timedelta, time
from pytz import timezone, utc

from zope.i18n import translate
from zope.interface import Interface
from zope.interface import directlyProvides, implements
from zope.component import provideAdapter, provideSubscriptionAdapter
from zope.interface.verify import verifyObject
from zope.publisher.browser import TestRequest
from zope.app.testing import setup
from zope.publisher.browser import BrowserView
from zope.traversing.interfaces import IContainmentRoot
from zope.session.interfaces import ISession
from zope.publisher.interfaces.http import IHTTPRequest
from zope.annotation.interfaces import IAttributeAnnotatable

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common import parse_datetime
from schooltool.term.interfaces import ITermContainer
from schooltool.term.tests import setUpDateManagerStub
from schooltool.testing.util import NiceDiffsMixin
from schooltool.app.interfaces import ISchoolToolCalendarEvent
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.app import getApplicationPreferences

# Used in defining CalendarEventAddTestView
from schooltool.app.browser.cal import CalendarEventAddView
from schooltool.app.browser.cal import ICalendarEventAddForm
from schooltool.app.cal import CalendarEvent, Calendar
from schooltool.app.interfaces import ISchoolToolCalendar

# Used in defining CalendarEventEditTestView
from schooltool.app.browser.cal import CalendarEventEditView
from schooltool.app.browser.cal import ICalendarEventEditForm
from schooltool.app.browser.testing import layeredTestTearDown
from schooltool.app.browser.testing import layeredTestSetup, makeLayeredSuite
from schooltool.app.browser.testing import setUp as browserSetUp, tearDown
from schooltool.app.testing import app_functional_layer
from schooltool.testing import setup as sbsetup

# Used for the PrincipalStub
# XXX: Bad, it depends on the person package.
from schooltool.person.person import Person, PersonContainer
from schooltool.person.interfaces import IPerson

# Used when registering CalendarProvider subscribers/stubs
from schooltool.app.browser.cal import CalendarListSubscriber
from schooltool.app.browser.interfaces import ICalendarProvider

# Used in tests
from schooltool.app.browser.cal import EventForDisplay
from schooltool.app.browser.cal import CalendarDay

try:
    from schooltool.timetable import SchooldayTemplate, SchooldaySlot
    from schooltool.timetable.interfaces import ITimetableSchemaContainer
    from schooltool.timetable.model import SequentialDaysTimetableModel
except:
    pass # XXX: tests not refactored yet


class PrincipalStub:

    _person = Person()

    def __conform__(self, interface):
        if interface is IPerson:
            return self._person


def dt(timestr):
    dt = parse_datetime('2004-11-05 %s:00' % timestr)
    return dt.replace(tzinfo=utc)


class ApplicationStub(object):
    implements(ISchoolToolApplication, IAttributeAnnotatable, IContainmentRoot)
    def __init__(self):
        pass


test_today = date(2005, 3, 13)
def setUp(test=None):
    browserSetUp(test)
    sbsetup.setUpCalendaring()
    sbsetup.setUpSessions()
    setUpDateManagerStub(test_today)
    app = ApplicationStub()
    provideAdapter(lambda x: app, (None,), ISchoolToolApplication)


def setUpTimetabling():
    from schooltool.timetable.app import getTimetableContainer
    from schooltool.timetable.app import getScheduleContainer

    provideAdapter(getTimetableContainer)
    provideAdapter(getScheduleContainer)

    from schooltool.testing import registry
    registry.setupTimetablesComponents()


class EventStub(object):

    implements(ISchoolToolCalendarEvent)

    dtstart = datetime(2006, 4, 20, 20, 7, tzinfo=utc)
    duration = timedelta(1)
    title = "Ordinary event"

    def __init__(self, unique_id='uid', owner=None, resources=()):
        self.__parent__ = ISchoolToolCalendar(Person())
        self.owner = owner
        self.resources = resources
        self.unique_id = unique_id
        self.__name__ = unique_id[::-1]


def createEvent(dtstart, duration, title, **kw):
    """Create a CalendarEvent.

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


def doctest_CalendarTraverser():
    """Tests for CalendarTraverser.

    CalendarTraverser allows you to traverse directly various calendar views:

        >>> from schooltool.calendar.browser.calendar import CalendarTraverser
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

        >>> event = CalendarEvent(datetime(2002, 2, 2, 2, 2),
        ...                       timedelta(hours=2), "Some event",
        ...                       unique_id="it's me!")
        >>> cal.addEvent(event)
        >>> event.__name__
        'aXQncyBtZSE='
        >>> traverser.publishTraverse(request, 'aXQncyBtZSE=') is event
        True

    """


def doctest_EventForDisplay():
    """A wrapper for calendar events.

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

    If event is an allday event EventForDisplay has its allday attribute set:

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

    shortTitle is ellipsized if the title is long

        >>> e2 = createEvent('2004-01-02 12:00:00', '15min',
        ...                  'sleeping for a little while because I was tired')
        >>> e2 = EventForDisplay(e2, request, 'blue', 'yellow', calendar, utc)
        >>> e2.shortTitle
        'sleeping for a ...'

    Lists of EventForDisplay objects can be sorted by start time

        >>> e1 > e2
        True

    You can specify the timezone you want the events to appear in

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

    Europe/Vilnius is a good test case, since the definiton of the zone has
    changed over the years, and if you use the wrong datetime API, you'll
    get a wrong UTC offset.

        >>> e3vilnius = EventForDisplay(e3, request, 'blue', 'yellow',
        ...                             calendar, timezone('Europe/Vilnius'))
        >>> print e3vilnius.dtstarttz
        2004-01-02 14:00:00+02:00
        >>> print e3vilnius.dtendtz
        2004-01-02 14:15:00+02:00

    """


def doctest_EventForDisplay_getBooker_getBookedResources():
    """Test for EventForDisplay.getBooker and getBookedResources.

        >>> from schooltool.app.browser.cal import EventForDisplay
        >>> class EFD(EventForDisplay):
        ...     def __init__(self):
        ...         self.context = EventStub(resources=['res1', 'res2'],
        ...                                  owner='Jonas')

    getBookedResources plainly returns the list of resources of the
    event:

        >>> efd = EFD()
        >>> sorted(efd.getBookedResources())
        ['res1', 'res2']

    getBooker returns the owner of the event:

        >>> print efd.getBooker()
        Jonas

    """


def doctest_EventForDisplay_renderShort():
    """Test for EventForDisplay.renderShort.

        >>> from schooltool.app.browser.cal import EventForDisplay
        >>> e = createEvent('2004-01-02 14:00:00', '90min',
        ...                 'sleeping for a little while because I was tired')
        >>> request = None
        >>> calendar = Calendar(None)
        >>> efd = EventForDisplay(e, request, 'blue', 'yellow', calendar, utc)

    The `renderShort` method is used to render the event in the monthly
    calendar view.

        >>> print efd.renderShort().replace('&ndash;', '--')
        sleeping for a ... (14:00--15:30)

    The same CalendarEvent can be renderered for display in a particular
    timezone.

        >>> efd = EventForDisplay(e, request, 'blue', 'yellow', calendar,
        ...                       timezone=timezone('US/Eastern'))
        >>> print efd.renderShort().replace('&ndash;', '--')
        sleeping for a ... (09:00--10:30)

    If the event crosses a day boundary, both dates are shown explicitly

        >>> efd = EventForDisplay(e, request, 'blue', 'yellow', calendar,
        ...                       timezone=timezone('Asia/Tokyo'))
        >>> print efd.renderShort().replace('&ndash;', '--').replace('&nbsp;', ' ')
        sleeping for a ... (Jan 02--Jan 03)

    """


def doctest_EventForDisplay_viewLink():
    """Test for EventForDisplay.viewLink.

        >>> from schooltool.app.browser.cal import EventForDisplay
        >>> event = createEvent('2005-12-12 22:50:00', '20min', 'drive home',
        ...                     unique_id='xyzzy')
        >>> request = TestRequest()
        >>> color1 = color2 = None
        >>> calendar = Calendar(None)
        >>> directlyProvides(calendar, IContainmentRoot)

    Some events are not viewable (dynamically created events, such as timetable
    events, that have no URLs):

        >>> e = EventForDisplay(event, request, color1, color2, calendar, utc)
        >>> print e.viewLink()
        None

    Other events are

        >>> calendar.addEvent(event)
        >>> e = EventForDisplay(event, request, color1, color2, calendar, utc)
        >>> print e.viewLink()
        http://127.0.0.1/calendar/eHl6enk%3D

    """


def doctest_EventForDisplay_editLink():
    """Test for EventForDisplay.editLink.

        >>> from schooltool.app.browser.cal import EventForDisplay
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
        http://127.0.0.1/calendar/eHl6enk%3D/edit.html?date=2005-09-26

    Note that if you're in a different time zone, the date may be different

        >>> e = EventForDisplay(event, request, color1, color2, calendar,
        ...                     timezone('Asia/Tokyo'))
        >>> print e.editLink()
        http://127.0.0.1/calendar/eHl6enk%3D/edit.html?date=2005-09-27

    A back-link may be specified.

        >>> e = EventForDisplay(event, request, color1, color2, calendar,
        ...                     timezone('Asia/Tokyo'),
        ...                     parent_view_link='http://foo/bar.html')
        >>> print e.editLink()
        http://127.0.0.1/calendar/eHl6enk%3D/edit.html?date=2005-09-27&back_url=http%3A//foo/bar.html&cancel_url=http%3A//foo/bar.html

    """


def doctest_EventForDisplay_deleteLink():
    """Test for EventForDisplay.deleteLink.

        >>> from schooltool.app.browser.cal import EventForDisplay
        >>> event = createEvent('2005-12-12 22:50:00', '20min', 'drive home',
        ...                     unique_id='xyzzy')
        >>> request = TestRequest()
        >>> color1 = color2 = None
        >>> calendar = Calendar(None)
        >>> directlyProvides(calendar, IContainmentRoot)

    Some events are not deletable.

        >>> e = EventForDisplay(event, request, color1, color2, calendar, utc)
        >>> print e.deleteLink()
        None

    Other events are

        >>> calendar.addEvent(event)
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> e = EventForDisplay(event, request, color1, color2, calendar, utc)
        >>> print e.deleteLink()
        http://127.0.0.1/calendar/delete.html?event_id=xyzzy&date=2005-12-12

    Note that if you're in a different time zone, the date may be different

        >>> e = EventForDisplay(event, request, color1, color2, calendar,
        ...                     timezone('Asia/Tokyo'))
        >>> print e.deleteLink()
        http://127.0.0.1/calendar/delete.html?event_id=xyzzy&date=2005-12-13

    A back-link may be specified.

        >>> e = EventForDisplay(event, request, color1, color2, calendar,
        ...                     timezone('Asia/Tokyo'),
        ...                     parent_view_link='http://foo/bar.html')
        >>> print e.deleteLink()
        http://127.0.0.1/calendar/delete.html?event_id=xyzzy&date=2005-12-13&back_url=http%3A//foo/bar.html

    """


def doctest_EventForDisplay_bookingLink():
    """Test for EventForDisplay.bookingLink.

        >>> from schooltool.app.browser.cal import EventForDisplay
        >>> event = createEvent('2005-12-12 22:50:00', '20min', 'drive home',
        ...                     unique_id='xyzzy')
        >>> request = TestRequest()
        >>> color1 = color2 = None
        >>> calendar = Calendar(None)
        >>> directlyProvides(calendar, IContainmentRoot)

    Some events are not bookable.

        >>> e = EventForDisplay(event, request, color1, color2, calendar, utc)
        >>> print e.bookingLink()
        None

    Other events are

        >>> calendar.addEvent(event)
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> e = EventForDisplay(event, request, color1, color2, calendar, utc)
        >>> print e.bookingLink()
        http://127.0.0.1/calendar/eHl6enk%3D/booking.html?date=2005-12-12

    Note that if you're in a different time zone, the date may be different

        >>> e = EventForDisplay(event, request, color1, color2, calendar,
        ...                     timezone('Asia/Tokyo'))
        >>> print e.bookingLink()
        http://127.0.0.1/calendar/eHl6enk%3D/booking.html?date=2005-12-13

    """


def doctest_EventForBookingDisplay():
    """A wrapper for calendar events.

        >>> from schooltool.app.browser.cal import EventForBookingDisplay
        >>> e1 = createEvent('2004-01-02 14:45:50', '5min', 'yawn',
        ...                  unique_id='uid0')
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
        >>> e1.unique_id
        'uid0'

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

        >>> day1 = CalendarDay(date(2004, 8, 5))
        >>> day1.date
        datetime.date(2004, 8, 5)
        >>> day1.events
        []

        >>> day2 = CalendarDay(date(2004, 7, 15), ["abc", "def"])
        >>> day2.date
        datetime.date(2004, 7, 15)
        >>> day2.events
        ['abc', 'def']

    You can sort a list of CalendarDay objects.

        >>> day1 > day2 and not day1 < day2
        True
        >>> day2 == CalendarDay(date(2004, 7, 15))
        True

    You can test a calendar day to see if its date is today

        >>> day = CalendarDay(test_today)
        >>> day.today()
        'today'

        >>> day = CalendarDay(test_today - date.resolution)
        >>> day.today()
        ''

    """


def registerCalendarSubscribers():
    """Register subscription adapter for listing calendars to display."""
    provideSubscriptionAdapter(CalendarListSubscriber,
                               (ISchoolToolCalendar, IHTTPRequest),
                               ICalendarProvider)


def registerCalendarHelperViews():
    """Register the real DailyCalendarRowsView for use by other views."""
    from schooltool.app.browser.cal import DailyCalendarRowsView
    from schooltool.app.interfaces import ISchoolToolCalendar
    from zope.publisher.interfaces.browser import IDefaultBrowserLayer
    provideAdapter(DailyCalendarRowsView,
                   (ISchoolToolCalendar, IDefaultBrowserLayer), Interface,
                   'daily_calendar_rows')


def getDaysStub(start, end):
    """Stub for CalendarViewBase.getDays."""
    days = []
    day = start
    while day < end:
        days.append(CalendarDay(day))
        day += timedelta(1)
    return days


class TestCalendarViewBase(unittest.TestCase):
    # Legacy unit tests from SchoolTool.

    today = date(2005, 6, 9)

    def setUp(self):
        setup.placefulSetUp()

        sbsetup.setUpSessions()
        registerCalendarHelperViews()
        registerCalendarSubscribers()

        provideAdapter(getApplicationPreferences,
                       (ISchoolToolApplication,), IApplicationPreferences)
        app = ApplicationStub()
        provideAdapter(lambda x: app, (None,), ISchoolToolApplication)

        setUpDateManagerStub(self.today)

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
        self.assertEquals(view.cursor, self.today)

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

        provideAdapter(getApplicationPreferences,
                       (ISchoolToolApplication,), IApplicationPreferences)

        from zope.publisher.interfaces import IRequest
        from zope.interface import Interface
        class TestDateFormatterFullView( BrowserView ):
            """
            A Stub view for formating the date
            """
            def __call__(self):
                return unicode(self.context.strftime("%A, %B%e, %Y"))

        provideAdapter(TestDateFormatterFullView,
                       [date, IRequest], Interface, name='fullDate')

        request1 = TestRequest()
        request1.setPrincipal(PrincipalStub())
        view1 = CalendarViewBase(None, request1)
        dt = datetime(2004, 7, 1)
        self.assertEquals(view1.dayTitle(dt), u'Thursday, July 1, 2004')

        request2 = TestRequest()
        request2.setPrincipal(PrincipalStub())
        self.assertEquals(view1.timezone.tzname(datetime.utcnow()), 'UTC')

    def test_prev_next(self):
        from schooltool.app.browser.cal import CalendarViewBase

        request = TestRequest()
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

        cal = Calendar(None)
        view = CalendarViewBase(cal, request)
        self.assertEquals(view.first_day_of_week, 0) # Monday by default
        self.assertEquals(view.time_fmt, '%H:%M')

        # change our preferences
        prefs = IApplicationPreferences(ISchoolToolApplication(None))
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

    def test_getYear_when_sunday(self):
        # Regression test for http://issues.schooltool.org/issue449
        from schooltool.app.browser.cal import CalendarViewBase
        view = CalendarViewBase(None, TestRequest())
        view.getDays = getDaysStub
        view.first_day_of_week = calendar.SUNDAY
        def getMonthStub(dt, days=None):
            # Check that boundaries of `days` are ones that we expect
            self.assertEquals(days[0].date, date(2003, 12, 28))
            self.assertEquals(days[-1].date, date(2005, 1, 1))
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

    def doctest_eventAddLink(self):
        """Tests for CalendarViewBase.eventAddLink.

            >>> from schooltool.app.browser.cal import CalendarViewBase
            >>> from schooltool.app.cal import Calendar

            >>> setup.placefulSetUp()
            >>> app = sbsetup.setUpSchoolToolSite()
            >>> directlyProvides(app, IContainmentRoot)
            >>> provideAdapter(lambda x: app, (None,), ISchoolToolApplication)
            >>> from schooltool.resource.interfaces import IBookingCalendar
            >>> from schooltool.resource.interfaces import IResourceContainer
            >>> from schooltool.resource.booking import ResourceBookingCalendar
            >>> provideAdapter(ResourceBookingCalendar,
            ...                (IResourceContainer,), IBookingCalendar)
            >>> setUpDateManagerStub(date(2005, 5, 13))

            >>> app['persons']['john'] = person = Person("john")
            >>> calendar = Calendar(person)
            >>> vb = CalendarViewBase(calendar, TestRequest())

        For persons or groups the link points to the add event view of
        the calendar you are looking at:

            >>> vb.cursor = date(2005, 1, 1)
            >>> vb.eventAddLink({'time': '5:00', 'duration': 45})
            'http://127.0.0.1/persons/john/calendar/add.html?field.start_date=2005-01-01&field.start_time=5:00&field.duration=45'

        The link should be quite different if this calendar belongs to
        a resource rather than a person. The link points to the
        resource booking calendar:

            >>> from schooltool.resource.resource import Resource
            >>> app['resources']['chair'] = resource = Resource("chair")
            >>> calendar = Calendar(resource)
            >>> vb = CalendarViewBase(calendar, TestRequest())

            >>> vb.cursor = date(2005, 1, 1)
            >>> vb.eventAddLink({'time': '5:00', 'duration': 45})
            u'http://127.0.0.1/resources/booking/book_one_resource.html?resource_id=chair&start_date=2005-01-01&start_time=5:00:00&title=Unnamed Event&duration=2700'

        """

    def doctest_pigeonhole(self):
        r"""Test for CalendarViewBase.pigeonhole().

        Our pigeonholer operates on date intervals and CalendarDays:

            >>> from schooltool.app.browser.cal import CalendarViewBase
            >>> from schooltool.app.cal import Calendar

            >>> app = sbsetup.setUpSchoolToolSite()
            >>> setUpTimetabling()
            >>> setUpDateManagerStub(date(2005, 5, 13))

            >>> person = app['persons']['ignas'] = Person(u'Ignas')
            >>> calendar = Calendar(person)
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
            >>> setUpDateManagerStub(date(2005, 5, 13))

        getCalendars() only delegates the task to a ICalendarProvider
        subscriber.  We will provide a stub subscriber to test the
        method.

            >>> class CalendarListSubscriberStub(object):
            ...     def __init__(self, context, request):
            ...         pass
            ...     def getCalendars(self):
            ...         return ['some calendar', 'another calendar']
            >>> provideSubscriptionAdapter(CalendarListSubscriberStub,
            ...                            (ISchoolToolCalendar, IHTTPRequest),
            ...                            ICalendarProvider)

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

            >>> class CalendarListSubscriberStub(object):
            ...     def __init__(self, context, request):
            ...         pass
            ...     def getCalendars(self):
            ...         return ['some calendar', 'another calendar']
            >>> provideSubscriptionAdapter(CalendarListSubscriberStub,
            ...                            (ISchoolToolCalendar, IHTTPRequest),
            ...                            ICalendarProvider)

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
            >>> app = sbsetup.setUpSchoolToolSite()
            >>> setup.setUpAnnotations()
            >>> registerCalendarHelperViews()
            >>> registerCalendarSubscribers()
            >>> sbsetup.setUpSessions()
            >>> setUpTimetabling()
            >>> setUpDateManagerStub(date(2005, 5, 13))

        CalendarViewBase.getEvents returns a list of wrapped calendar
        events.

            >>> from schooltool.app.browser.cal import CalendarViewBase
            >>> from schooltool.app.cal import Calendar
            >>> person = app['persons']['ignas'] = Person(u'Ignas')
            >>> cal1 = Calendar(person)
            >>> cal1.addEvent(createEvent('2005-02-26 19:39', '1h', 'code'))
            >>> cal1.addEvent(createEvent('2005-02-20 16:00', '1h', 'walk'))
            >>> view = CalendarViewBase(cal1, TestRequest())
            >>> view.inCurrentPeriod = lambda dt: False
            >>> for e in view.getEvents(datetime(2005, 2, 21, tzinfo=utc),
            ...                         datetime(2005, 3, 1, tzinfo=utc)):
            ...     print e.title
            ...     print e.dtstarttz
            code
            2005-02-26 19:39:00+00:00

        We will stub view.getCalendars to simulate overlayed calendars

            >>> cal2 = Calendar(None)
            >>> cal2.addEvent(createEvent('2005-02-27 12:00', '1h', 'rest'))
            >>> view.getCalendars = lambda:[(cal1, 'r', 'g'), (cal2, 'b', 'y')]
            >>> for e in view.getEvents(datetime(2005, 2, 21, tzinfo=utc),
            ...                         datetime(2005, 3, 1, tzinfo=utc)):
            ...     print e.title, '(%s)' % e.color1
            code (r)
            rest (b)

            >>> view.timezone.tzname(datetime.now())
            'UTC'

            >>> for i in range(0, 24):
            ...     cal1.addEvent(CalendarEvent(datetime(2002, 2, 1, i),
            ...                       timedelta(minutes=59), "day1-" + str(i)))
            ...     cal1.addEvent(CalendarEvent(datetime(2002, 2, 2, i),
            ...                       timedelta(minutes=59), "day2-" + str(i)))
            ...     cal1.addEvent(CalendarEvent(datetime(2002, 2, 3, i),
            ...                       timedelta(minutes=59), "day3-" + str(i)))

        Let's get some events in the interval between two dates:

            >>> titles = []
            >>> for e in view.getEvents(datetime(2002, 2, 2, tzinfo=utc),
            ...                         datetime(2002, 2, 3, tzinfo=utc)):
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
        app = sbsetup.setUpSchoolToolSite()
        setUpTimetabling()

        e0 = createEvent('2004-08-10 11:00', '1h', "e0")
        e2 = createEvent('2004-08-11 11:00', '1h', "e2")
        e3 = createEvent('2004-08-12 23:00', '4h', "e3")
        e4 = createEvent('2004-08-15 11:00', '1h', "e4")
        e5 = createEvent('2004-08-10 09:00', '3d', "e5")
        e6 = createEvent('2004-08-13 00:00', '1d', "e6")
        e7 = createEvent('2004-08-12 00:00', '1d+1sec', "e7")
        e8 = createEvent('2004-08-15 00:00', '0sec', "e8")

        cal = Calendar(Person())
        directlyProvides(cal, IContainmentRoot)
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
        app = sbsetup.setUpSchoolToolSite()
        setUpTimetabling()

        e0 = createEvent('2004-08-10 22:00', '30m', "e0")
        e1 = createEvent('2004-08-11 02:00', '1h', "e1")
        e2 = createEvent('2004-08-11 12:00', '1h', "e2")
        e3 = createEvent('2004-08-11 22:00', '1h', "e3")
        e4 = createEvent('2004-08-12 02:00', '1h', "e4")

        cal = Calendar(Person())
        directlyProvides(cal, IContainmentRoot)
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
        days = view._getDays(date(2004, 8, 11), date(2004, 8, 12))

        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, date(2004, 8, 11))

        self.assertEqualEventLists(days[0].events, [e0, e1, e2])

        days = view._getDays(date(2004, 8, 12), date(2004, 8, 13))
        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, date(2004, 8, 12))

        self.assertEqualEventLists(days[0].events, [e3, e4])

        view.timezone = timezone('US/Eastern')
        start = date(2004, 8, 12)
        end = date(2004, 8, 13)
        days = view._getDays(start, end)

        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, date(2004, 8, 12))

        self.assertEqualEventLists(days[0].events, [])

        view.timezone = timezone('Europe/Vilnius')
        days = view._getDays(start, end)

        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, date(2004, 8, 12))

        self.assertEqualEventLists(days[0].events, [e3, e4])

    def test_getDays_allday(self):
        from schooltool.app.browser.cal import CalendarViewBase
        from schooltool.app.cal import Calendar
        app = sbsetup.setUpSchoolToolSite()
        setUpTimetabling()

        event = createEvent('2004-08-10', "1d", "e0", allday=True)

        cal = Calendar(Person())
        directlyProvides(cal, IContainmentRoot)
        cal.addEvent(event)

        request = TestRequest()
        view = CalendarViewBase(cal, request)

        days = view._getDays(date(2004, 8, 9), date(2004, 8, 10))
        self.assertEquals(len(days[0].events), 0)

        days = view._getDays(date(2004, 8, 10), date(2004, 8, 11))
        self.assertEquals(len(days[0].events), 1)

        days = view._getDays(date(2004, 8, 11), date(2004, 8, 12))
        self.assertEquals(len(days[0].events), 0)

        view.timezone = timezone('Europe/Vilnius')

        days = view._getDays(date(2004, 8, 9), date(2004, 8, 10))
        self.assertEquals(len(days[0].events), 0)

        days = view._getDays(date(2004, 8, 10), date(2004, 8, 11))
        self.assertEquals(len(days[0].events), 1)

        days = view._getDays(date(2004, 8, 11), date(2004, 8, 12))
        self.assertEquals(len(days[0].events), 0)

    def test_getJumpToYears(self):
        from schooltool.app.cal import Calendar
        from schooltool.app.browser.cal import CalendarViewBase
        cal = Calendar(Person())
        directlyProvides(cal, IContainmentRoot)

        first_year = self.today.year - 2
        last_year = self.today.year + 2

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
                          'interval', 'range', 'until', 'count', 'exceptions',
                          'allday']
    _set_before_add = []
    _set_after_add = []

def doctest_CalendarEventView():
    r"""Tests for CalendarEventView.

    We'll create a simple event view.

        >>> from schooltool.app.browser.cal import CalendarEventView
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

    The display knows about booked resources, currently there are none.

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


def doctest_CalendarEventAddView_add_allday():
    r"""Adding an allday event with a duration.

    When creating an allday event we were not using the duration
    field, now that should be fixed:

        >>> request = TestRequest(
        ...     form={'field.title': 'NonHacking',
        ...           'field.start_date': '2005-02-27',
        ...           'field.allday': 'on',
        ...           'field.duration': '15',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Add'})

        >>> calendar = Calendar(Person())
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        ''

        >>> print view.errors
        ()
        >>> print view.error
        None

        >>> event = list(calendar)[0]
        >>> event.allday
        True
        >>> event.duration.days
        15

    And even if the user will manage to set some other duration units
    (not days), that input will be ignored:

        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2005-02-27',
        ...           'field.allday': 'on',
        ...           'field.duration': '13',
        ...           'field.duration_type': 'minutes',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Add'})

        >>> calendar = Calendar(Person())
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        ''

        >>> event = list(calendar)[0]
        >>> event.allday
        True
        >>> event.duration.days
        13

    """


def doctest_CalendarEventAddView_add_mark_for_booking():
    r"""Tests for CalendarEventAddView.add.

        >>> class CalendarStub(object):
        ...     def addEvent(self, e):
        ...         pass
        >>> request = TestRequest()
        >>> view = CalendarEventAddTestView(CalendarStub(), request)

    Let's add an event:

        >>> evt = view.add(EventStub('uid1'))

    Its id should have landed in the session:

        >>> session_data = ISession(request)['schooltool.calendar']
        >>> sorted(session_data['added_event_uids'])
        ['uid1']

    Let's try another one:

        >>> evt2 = view.add(EventStub('uid2'))
        >>> sorted(session_data['added_event_uids'])
        ['uid1', 'uid2']

    """


def doctest_CalendarEventAddView_add():
    r"""Tests for CalendarEventAddView adding of new event.

    First, let's simply render the CalendarEventAddTestView.

        >>> view = CalendarEventAddTestView(Calendar(Person()), TestRequest())
        >>> view.update()

    Let's try to add an event:

        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '15:30',
        ...           'field.duration': '50',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Add'})

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

        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '15:30',
        ...           'field.duration': '50',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'field.location': 'Moon',
        ...           'field.weekdays-empty-marker': '1',
        ...           'UPDATE_SUBMIT': 'Add'})

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


        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '15:30',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '50',
        ...           'field.recurrence_type': 'daily',})
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

        >>> request = TestRequest(
        ...     form={'field.title': 'East Coast',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '15:30',
        ...           'field.duration': '50',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'field.location': 'East Coast',
        ...           'field.weekdays-empty-marker': '1',
        ...           'UPDATE_SUBMIT': 'Add'})

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

        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.duration': '50',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Add'})

        >>> calendar = Calendar(Person())
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occurred.'

        >>> print view.errors
        MissingInputError: ('field.start_time', u'Time', None)
        >>> print view.error
        None
        >>> len(calendar)
        0

        >>> request = TestRequest(
        ...     form={'field.title': '',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '15:30',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '50',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Add'})
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occurred.'
        >>> view.errors
        WidgetInputError: ('title', u'Title', RequiredMissing())
        >>> view.error is None
        True


        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2004-31-13',
        ...           'field.start_time': '15:30',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '50',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Add'})
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occurred.'
        >>> view.errors
        ConversionError: (u'Invalid datetime data', ...)
        >>> view.error is None
        True


        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '15:30',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '100h',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Add'})
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occurred.'
        >>> view.errors
        ConversionError: (u'Invalid integer data', ...)
        >>> view.error is None
        True

        >>> request = TestRequest(
        ...     form={'field.title': '',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '1530',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '60',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Add'})
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occurred.'
        >>> view.errors
        WidgetInputError: ('title', u'Title', RequiredMissing())
        ConversionError: (u'Invalid time', None)
        >>> view.error is None
        True

        >>> request = TestRequest(
        ...     form={'field.title': '',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '1530',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '60',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE': 'update'})
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occurred.'
        >>> view.errors
        WidgetInputError: ('title', u'Title', RequiredMissing())
        ConversionError: (u'Invalid time', None)
        >>> view.error is None
        True

    """


def doctest_CalendarEventAddView_add_recurrence():
    r"""Tests for CalendarEventAddView adding of recurring event.

    Let's try to add a recurring event:

        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '15:30',
        ...           'field.duration': '50',
        ...           'field.location': 'Moon',
        ...           'field.recurrence': 'on',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'field.interval': '1',
        ...           'field.range': 'forever',
        ...           'UPDATE_SUBMIT': 'Add'})

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

        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '15:30',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '50',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Add'})
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

        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '15:30',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '50',
        ...           'field.recurrence': 'on',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'field.interval': '2',
        ...           'field.range': 'forever',
        ...           'UPDATE_SUBMIT': 'Add'})


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

        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '15:30',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '50',
        ...           'field.recurrence': 'on',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'field.interval': '1',
        ...           'field.range': 'forever',
        ...           'field.exceptions': '2004-08-14\n2004-08-19\n2004-08-20',
        ...           'UPDATE_SUBMIT': 'Add'})


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
        u'An error occurred.'

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

        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2004-10-01',
        ...           'field.start_time': '15:30',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '50',
        ...           'field.recurrence': 'on',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'field.interval': '2',
        ...           'UPDATE_SUBMIT': 'Add'})
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

        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2004-10-01',
        ...           'field.start_time': '15:30',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '50',
        ...           'field.recurrence': 'on',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'field.interval': '2',
        ...           'UPDATE_SUBMIT': 'Add'})
        >>> calendar = Calendar(Person())

        >>> request.form['field.start_date'] = ""
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> translate(view.getLastWeekDay())
        u'last weekday'

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

        >>> request = TestRequest(
        ...     form={'field.title': 'Foo',
        ...     'field.start_date': '2003-12-01',
        ...     'field.start_time': '15:30',
        ...     'field.location': 'Kitchen',
        ...     'field.duration': '59',
        ...     'field.recurrence': 'on',
        ...     'field.recurrence_type': 'daily',
        ...     'field.interval': '',
        ...     'field.range': 'count',
        ...     'field.count': '6',
        ...     'field.until': '2004-01-01',
        ...     'UPDATE_SUBMIT': 'Add'})
        >>> calendar = Calendar(Person())
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occurred.'
        >>> view.errors
        WidgetInputError: ('interval', u'Repeat every', RequiredMissing())
        >>> view.error is None
        True

        >>> request = TestRequest(
        ...     form={'field.title': 'Foo',
        ...           'field.start_date': '2003-12-01',
        ...           'field.start_time': '15:30',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '59',
        ...           'field.recurrence': 'on',
        ...           'field.recurrence_type' : 'daily',
        ...           'field.interval': '1',
        ...           'field.range': 'until',
        ...           'field.until': '2002-01-01',
        ...           'UPDATE_SUBMIT': 'Add'})
        >>> calendar = Calendar(Person())
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occurred.'
        >>> view.errors
        WidgetInputError: ('until', u'Repeat until',
            ConstraintNotSatisfied(u'End date is earlier than start date'))
        >>> view.error is None
        True

        >>> request = TestRequest(
        ...     form={'field.title': 'Hacking',
        ...           'field.start_date': '2004-08-13',
        ...           'field.start_time': '15:30',
        ...           'field.location': 'Kitchen',
        ...           'field.duration': '100',
        ...           'field.recurrence': 'on',
        ...           'field.recurrence_type' : 'daily',
        ...           'field.range': 'until',
        ...           'field.count': '23',
        ...           'UPDATE_SUBMIT': 'Add'})
        >>> calendar = Calendar(Person())
        >>> view = CalendarEventAddTestView(calendar, request)
        >>> view.update()
        u'An error occurred.'
        >>> view.errors
        MissingInputError: ('field.interval', u'Repeat every', None)
        MissingInputError: ('field.until', u'Repeat until', None)
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
                          'interval', 'range', 'until', 'count', 'exceptions',
                          'allday']
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

        >>> request = TestRequest(
        ...     form={'field.title': 'NonHacking',
        ...           'field.start_date': '2004-09-13',
        ...           'field.start_time': '15:30',
        ...           'field.duration': '50',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Edit'})

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
        >>> request = TestRequest(
        ...     form={'field.title': 'NonHacking',
        ...           'field.start_date': '2004-09-19',
        ...           'field.start_time': '15:35',
        ...           'field.duration': '50',
        ...           'field.location': 'Kitchen',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Edit'})

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

        >>> request = TestRequest(
        ...     form={'field.title': 'NonHacking',
        ...           'field.start_date': '2004-09-19',
        ...           'field.start_time': '15:35',
        ...           'field.duration': '50',
        ...           'field.location': 'Kitchen',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence': 'on',
        ...           'field.recurrence_type' : 'daily',
        ...           'field.range': 'count',
        ...           'field.count': '23',
        ...           'field.interval': '2',
        ...           'UPDATE_SUBMIT': 'Edit'})

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

        >>> request = TestRequest(
        ...     form={'date': '2004-08-13',
        ...           'field.title': 'NonHacking',
        ...           'field.start_date': '2004-09-13',
        ...           'field.start_time': '15:30',
        ...           'field.duration': '50',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Edit'})

        >>> view = CalendarEventEditTestView(event, request)

        >>> view.update()
        u'Updated on ${date_time}'
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/calendar'

    Let's try to cancel the editing event:

        >>> request = TestRequest(
        ...     form={'date': '2004-08-13',
        ...           'field.title': 'NonHacking',
        ...           'field.start_date': '2004-09-13',
        ...           'field.start_time': '15:30',
        ...           'field.duration': '50',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'CANCEL': 'Cancel'})

        >>> view = CalendarEventEditTestView(event, request)

        >>> view.update()
        ''
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/calendar'

    If the date stays unchanged - we should be redirected to the date
    that was set in the request:

        >>> request = TestRequest(
        ...     form={'date': '2004-08-13',
        ...           'field.title': 'NonHacking',
        ...           'field.start_date': '2004-09-13',
        ...           'field.start_time': '15:30',
        ...           'field.duration': '50',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE_SUBMIT': 'Edit'})
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

        >>> request = TestRequest(
        ...     form={'field.title': 'NonHacking',
        ...           'field.start_date': '2005-02-27',
        ...           'field.start_time': '15:30',
        ...           'field.duration': '50',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE': 'Update'})

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

        >>> request = TestRequest(
        ...     form={'field.title': 'NonHacking',
        ...           'field.start_date': '',
        ...           'field.start_time': '',
        ...           'field.duration': '50',
        ...           'field.recurrence.used': '',
        ...           'field.recurrence_type': 'daily',
        ...           'UPDATE': 'Update'})

        >>> view = CalendarEventEditTestView(event, request)

        >>> view.update()
        u'An error occurred.'
        >>> print view.errors
        WidgetInputError: ('start_date', u'Date', RequiredMissing())
        WidgetInputError: ('start_time', u'Time', RequiredMissing())
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

    Regression test for events with duration longer than 24 hours:

        >>> event = CalendarEvent(title="Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(days=2),
        ...                       location="Kitchen")

        >>> view = CalendarEventEditTestView(event, request)
        >>> view.duration_widget._getFormValue()
        2

        >>> view.duration_type_widget._getFormValue()
        'days'

    As users don't really measure all the times in minutes it would be
    kind of nice to show units in hours if minutes divide up by 60:

        >>> event = CalendarEvent(title="Hacking",
        ...                       dtstart=datetime.datetime(2004, 8, 13, 20, 0),
        ...                       duration=datetime.timedelta(hours=2),
        ...                       location="Kitchen")

        >>> view = CalendarEventEditTestView(event, request)

        >>> view.duration_widget._getFormValue()
        2

        >>> view.duration_type_widget._getFormValue()
        'hours'

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

    The days should have shifted to a later date:

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

    If the timezone of the view shifts the event into the different
    day, the date changes:

        >>> view.timezone = timezone('Australia/Canberra')
        >>> view.getStartDate()
        datetime.date(2004, 8, 14)

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


def doctest_convertWeekdaysList():
    """A test for convertWeekdaysList

       >>> from schooltool.app.browser.cal import convertWeekdaysList

    When it's 1:00 AM in Vilnius, it's still yesterday in London:

       >>> vilnius = timezone('Europe/Vilnius')
       >>> london = timezone('Europe/London')
       >>> dt = vilnius.localize(datetime(2006, 5, 5, 1, 0))
       >>> convertWeekdaysList(dt, vilnius, london, (0, ))
       [6]
       >>> convertWeekdaysList(dt, vilnius, london, (5, 6))
       [4, 5]

    And vice versa:

       >>> convertWeekdaysList(dt, london, vilnius, (0, ))
       [1]
       >>> convertWeekdaysList(dt, london, vilnius, (5, 6))
       [6, 0]

    Let's look at the time that is the same day in Vilnius and London:

       >>> dt = vilnius.localize(datetime(2006, 5, 5, 23, 0))
       >>> convertWeekdaysList(dt, london, vilnius, (0, ))
       [0]
       >>> convertWeekdaysList(dt, london, vilnius, (5, 6))
       [5, 6]

    """

def doctest_TestCalendarEventBookingView():
    r"""A test for the resource booking view.

    We must have a schooltool application with some resources, a
    person and his calendar with an event:

        >>> from schooltool.app.browser.cal import CalendarEventBookingView
        >>> from schooltool.resource.resource import Resource
        >>> from schooltool.app.cal import CalendarEvent

        >>> app = sbsetup.setUpSchoolToolSite()

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
        >>> class StubResourceContainer(object):
        ...     def filter(self, list):
        ...         return list
        ...     def values(self):
        ...         return []
        >>> def stubItemsContainer():
        ...     return StubResourceContainer()
        >>> view.getAvailableItemsContainer = stubItemsContainer
        >>> view.filter = lambda list: list
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

        >>> request = TestRequest(form={'add_item.res2': '1',
        ...                             'add_item.res4': '1',
        ...                             'BOOK': 'Set'})
        >>> view = CalendarEventBookingView(event, request)
        >>> view.getAvailableItemsContainer = stubItemsContainer
        >>> view.filter = lambda list: list
        >>> view.update()
        ''

    A couple of resources should be booked now:

        >>> sorted([resource.title for resource in view.getBookedItems()])
        ['res2', 'res4']


    Now let's unbook a resource and book a new one:

        >>> request = TestRequest(form={'add_item.res3': '1',
        ...                             'add_item.res4': '1',
        ...                             'BOOK': 'Set'})

        >>> view = CalendarEventBookingView(event, request)
        >>> view.getAvailableItemsContainer = stubItemsContainer
        >>> view.filter = lambda list: list
        >>> view.update()
        ''
        >>> sorted([resource.title for resource in view.getBookedItems()])
        ['res2', 'res3', 'res4']

        >>> request = TestRequest(form={'remove_item.res2':'1',
        ...                            'UNBOOK': 'Set'})
        >>> view = CalendarEventBookingView(event, request)
        >>> view.getAvailableItemsContainer = stubItemsContainer
        >>> view.filter = lambda list: list
        >>> view.update()
        ''

    We should see resource 3 in the list now:

        >>> sorted([resource.title for resource in view.getBookedItems()])
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
        >>> view.getAvailableItemsContainer = stubItemsContainer
        >>> view.filter = lambda list: list
        >>> view.update()

    Nothing has changed, see?

        >>> sorted([resource.title for resource in view.getBookedItems()])
        ['res3', 'res4']

    And you have been redirected back to the calendar:

        >>> request.response.getHeader('Location')
        'http://127.0.0.1/persons/ignas/calendar'

    The view also follows PersonPreferences timeformat and dateformat settings.
    To demonstrate these we need to setup PersonPreferences:

        >>> setup.setUpAnnotations()

        >>> provideAdapter(getApplicationPreferences,
        ...                (ISchoolToolApplication,), IApplicationPreferences)
        >>> view = CalendarEventBookingView(event, request)
        >>> view.getAvailableItemsContainer = stubItemsContainer
        >>> view.filter = lambda list: list
        >>> view.update()

    Without the preferences set, we get the default start and end time
    formatting:

        >>> view.start
        u'2002-02-02 - 02:02'
        >>> view.end
        u'2002-02-02 - 04:02'

    We'll change the date and time formatting in the preferences and create a
    new view.  Note that we need to create a new view because 'start' and 'end'
    are set in __init__:

        >>> prefs = IApplicationPreferences(ISchoolToolApplication(None))
        >>> prefs.timeformat = '%I:%M %p'
        >>> prefs.dateformat = '%d %B, %Y'
        >>> view = CalendarEventBookingView(event, request)

    Now we can see the changes:

        >>> view.start
        u'02 February, 2002 - 02:02 AM'
        >>> view.end
        u'02 February, 2002 - 04:02 AM'

    """


def doctest_CalendarEventBookingView_justAddedThisEvent():
    """Test for CalendarEventBookingView.justAddedThisEvent

        >>> context = EventStub('uid1')
        >>> request = TestRequest()

        >>> from schooltool.app.browser.cal import CalendarEventBookingView
        >>> view = CalendarEventBookingView(context, request)

    At this moment the view knows nothing about adding this event:

        >>> view.justAddedThisEvent()
        False

    Let's register a different event as added:

        >>> session_data = ISession(request)['schooltool.calendar']
        >>> session_data['added_event_uids'] = set(['uid2'])

    The view still refuses to acknowledge that you have added the event:

        >>> view.justAddedThisEvent()
        False

    Ok, that's enough.  We really *did* add the event:

        >>> session_data['added_event_uids'] = set(['uid1', 'uid2'])

    This time the view is not so stubborn:

        >>> view.justAddedThisEvent()
        True

    """


def doctest_CalendarEventBookingView_clearJustAddedStatus():
    """Test for CalendarEventBookingView.clearJustAddedStatus

        >>> context = EventStub('uid1')
        >>> request = TestRequest()

        >>> from schooltool.app.browser.cal import CalendarEventBookingView
        >>> view = CalendarEventBookingView(context, request)

    This method should not break even if the list of added events is
    not initialized.

        >>> view.clearJustAddedStatus()

    Let's register an event as added:

        >>> session_data = ISession(request)['schooltool.calendar']
        >>> session_data['added_event_uids'] = set(['uid3'])

    The view will not delete this registration, because it's not ours:

        >>> view.clearJustAddedStatus()
        >>> session_data['added_event_uids']
        set(['uid3'])

    Ok, that's enough.  We really *did* add the event:

        >>> session_data['added_event_uids'] = set(['uid1', 'uid2'])

    This time the other registration remains, but uid1 is removed.

        >>> view.clearJustAddedStatus()
        >>> session_data['added_event_uids']
        set(['uid2'])

    """


def doctest_CalendarEventBookingView_getConflictingEvents():
    """Test for CalendarEventBookingView.getConflictingEvents

        >>> from schooltool.app.browser.cal import CalendarEventBookingView

        >>> class CalendarStub(object):
        ...     def __init__(self, title, events):
        ...         self.events = events
        ...         self.title = title
        ...     def expand(self, dtstart, dtend):
        ...         print "%s.expand(%s, %s)" % (self.title, dtstart, dtend)
        ...         return self.events

    Let's give ourselves the permission to access the calendar events:

        >>> from zope.security.checker import defineChecker
        >>> from zope.security.checker import Checker
        >>> defineChecker(CalendarStub,
        ...               Checker({'expand': 'zope.Public'},
        ...                       {'expand': 'zope.Public'}))

        >>> class ResourceStub(object):
        ...     calendar = CalendarStub("calendar", [EventStub("cal"), EventStub("tt")])
        ...     def __conform__(self, iface):
        ...         if iface is ISchoolToolCalendar:
        ...             return self.calendar

        >>> context = EventStub("evt")
        >>> view = CalendarEventBookingView(context, TestRequest())

        >>> resource = ResourceStub()
        >>> conflicts = view.getConflictingEvents(resource)
        calendar.expand(2006-04-20 20:07:00+00:00, 2006-04-21 20:07:00+00:00)

    All conflicting events are returned:

        >>> [evt.unique_id for evt in conflicts]
        ['cal', 'tt']

    If the event that is booking the resources is ignored:

        >>> resource.calendar = CalendarStub("calendar", [context, EventStub("tt")])
        >>> conflicts = view.getConflictingEvents(resource)
        calendar.expand(2006-04-20 20:07:00+00:00, 2006-04-21 20:07:00+00:00)

        >>> [evt.unique_id for evt in conflicts]
        ['tt']

    """


def doctest_getEvents_booking():
    """Test for CalendarViewBase.getEvents when booking is involved

    CalendarViewBase.getEvents returns a list of wrapped calendar
    events.

        >>> from schooltool.app.browser.cal import CalendarViewBase
        >>> from schooltool.resource.resource import Resource

        >>> person = Person(u"frog")
        >>> calendar = ISchoolToolCalendar(person)
        >>> directlyProvides(calendar, IContainmentRoot)
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
        >>> for e in view.getEvents(datetime(2005, 2, 21, tzinfo=utc),
        ...                         datetime(2005, 3, 1, tzinfo=utc)):
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
        >>> for e in view.getEvents(datetime(2005, 2, 21, tzinfo=utc),
        ...                         datetime(2005, 3, 1, tzinfo=utc)):
        ...     print e.title, '(%s)' % e.color1
        code (r)
        swim (b)
        swim (m)

    """


class TestDailyCalendarView(unittest.TestCase):

    today = date(2005, 3, 12)

    def setUp(self):
        setup.placefulSetUp()
        self.app = sbsetup.setUpSchoolToolSite()
        registerCalendarHelperViews()
        registerCalendarSubscribers()
        sbsetup.setUpSessions()
        setUpTimetabling()
        sbsetup.setUpCalendaring()
        setUpDateManagerStub(self.today)

    def tearDown(self):
        setup.placefulTearDown()

    def test_title(self):
        from schooltool.app.browser.cal import DailyCalendarView

        view = DailyCalendarView(ISchoolToolCalendar(Person()), TestRequest())
        view.update()
        self.assertEquals(view.cursor, self.today)

        from zope.publisher.interfaces import IRequest
        from zope.interface import Interface

        class TestDateFormatterFullView( BrowserView ):
            """
            A Stub view for formating the date
            """
            def __call__(self):
                return unicode(self.context.strftime("%A, %B%e, %Y"))

        provideAdapter(TestDateFormatterFullView,
                       [date, IRequest], Interface, name='fullDate')

        view.request = TestRequest(form={'date': '2005-01-06'})
        view.update()
        self.assertEquals(view.title(), u'Thursday, January 6, 2005')
        view.request = TestRequest(form={'date': '2005-01-07'})
        view.update()
        self.assertEquals(view.title(), u'Friday, January 7, 2005')

    def test__setRange(self):
        from schooltool.app.browser.cal import DailyCalendarView

        person = Person("Da Boss")
        cal = ISchoolToolCalendar(person)
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 16)

        def do_test(events, periods, expected):
            view.starthour, view.endhour = 8, 19
            view._setRange(events, periods)
            self.assertEquals((view.starthour, view.endhour), expected)

        do_test([], [], (8, 19))

        events = [createEvent('2004-08-16 7:00', '1min', 'workout')]
        do_test(events, [], (7, 19))

        events = [createEvent('2004-08-15 8:00', '1d', "long workout")]
        do_test(events, [], (0, 19))

        events = [createEvent('2004-08-16 20:00', '30min', "late workout")]
        do_test(events, [], (8, 21))

        events = [createEvent('2004-08-16 20:00', '5h', "long late workout")]
        do_test(events, [], (8, 24))

        dummy_event = createEvent('2004-08-16 7:00', '1min', 'workout')
        periods = [('', dummy_event.dtstart, dummy_event.duration)]
        do_test(events, periods, (7, 24))

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
            view._setRange(events, [])
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
        directlyProvides(cal, IContainmentRoot)
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
        directlyProvides(cal, IContainmentRoot)
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
        directlyProvides(cal, IContainmentRoot)
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
        directlyProvides(cal, IContainmentRoot)
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)
        view.calendarRows = lambda evs: iter([
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
        result = list(view.calendarRows([]))
        expected = [('%d:00' % hr, datetime(2004, 8, 12, hr, tzinfo=utc),
                     timedelta(0, 3600)) for hr in range(10, 16)]
        self.assertEquals(result, expected)

    def test_getHours(self):
        from schooltool.app.browser.cal import DailyCalendarView

        person = Person(title="Da Boss")
        cal = ISchoolToolCalendar(person)
        directlyProvides(cal, IContainmentRoot)
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
                            'top': 0.0, 'height': 4.0,
                            'active': False,
                            'full_title': u'Add new event starting at 10:00'},
                           {'duration': 60, 'time': '11:00',
                            'title': '11:00', 'cols': (None,),
                            'top': 4.0, 'height': 4.0,
                            'active': False,
                            'full_title': u'Add new event starting at 11:00'},
                           {'duration': 60, 'time': '12:00',
                            'title': '12:00', 'cols': (None,),
                            'top': 8.0, 'height': 4.0,
                            'active': False,
                            'full_title': u'Add new event starting at 12:00'},
                           {'duration': 60, 'time': '13:00',
                            'title': '13:00', 'cols': (None,),
                            'top': 12.0, 'height': 4.0,
                            'active': False,
                            'full_title': u'Add new event starting at 13:00'},
                           {'duration': 60, 'time': '14:00',
                            'title': '14:00', 'cols': (None,),
                            'top': 16.0, 'height': 4.0,
                            'active': False,
                            'full_title': u'Add new event starting at 14:00'},
                           {'duration': 60, 'time': '15:00',
                            'title': '15:00', 'cols': (None,),
                            'top': 20.0, 'height': 4.0,
                            'active': False,
                            'full_title': u'Add new event starting at 15:00'},
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
                del d['active']
                del d['full_title']
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
                          [{'title': '00:00', 'cols': (ev4, None, None)},
                           {'title': '01:00', 'cols': ('', None, None)},
                           {'title': '02:00', 'cols': ('', None, None)},
                           {'title': '03:00', 'cols': ('', None, None)},
                           {'title': '04:00', 'cols': ('', None, None)},
                           {'title': '05:00', 'cols': ('', None, None)},
                           {'title': '06:00', 'cols': ('', None, None)},
                           {'title': '07:00', 'cols': ('', None, None)},
                           {'title': '08:00', 'cols': ('', None, None)},
                           {'title': '09:00', 'cols': ('', None, None)},
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
        directlyProvides(cal, IContainmentRoot)
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

    def test_getHoursActivePeriod(self):
        from schooltool.app.browser.cal import DailyCalendarView

        # Some setup.
        person = Person(title="Da Boss")
        cal = ISchoolToolCalendar(person)
        directlyProvides(cal, IContainmentRoot)
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 1, 1)
        view._getCurrentTime = lambda: utc.localize(datetime(2004, 1, 1, 13, 0))
        ev1 = createEvent('2004-01-01 00:01', '5min', "Start of the day")
        ev2 = createEvent('2004-01-01 23:30', '5min', "End of the day")

        cal.addEvent(ev1)
        cal.addEvent(ev2)

        result = list(view.getHours())
        self.assert_(len(result) == 24)
        self.assertEquals([hour for hour in result
                           if hour['active'] is True],
                          [{'title': '13:00',
                            'top': 52.0,
                            'cols': (None, None),
                            'height': 4.0,
                            'duration': 60,
                            'time': '13:00',
                            'active': True,
                            'full_title': u'Add new event starting at 13:00'}])

    def test_getHours_short_periods(self):
        from schooltool.app.browser.cal import DailyCalendarView

        # Some setup.
        person = Person(title="Da Boss")
        cal = ISchoolToolCalendar(person)
        directlyProvides(cal, IContainmentRoot)
        view = DailyCalendarView(cal, TestRequest())
        view.cursor = date(2004, 8, 12)

        # Patch in a custom simpleCalendarRows method to test short periods.

        from schooltool.app.browser.cal import DailyCalendarRowsView
        rows_view = DailyCalendarRowsView(view.context, view.request)

        def simpleCalendarRows(events):
            today = datetime.combine(view.cursor, time(13, tzinfo=utc))
            durations = [0, 1800, 1351, 1349, 600, 7200]
            row_ends = [today + timedelta(seconds=sum(durations[:i+1]))
                        for i in range(1, len(durations))]

            start = today + timedelta(hours=view.starthour)
            for end in row_ends:
                duration = end - start
                yield (rows_view.rowTitle(start, duration),
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

            >>> view.snapToGrid(datetime(2004, 8, 1, 8, 0, tzinfo=utc))
            0.0

            >>> view.snapToGrid(datetime(2004, 8, 1, 8, 1, tzinfo=utc))
            0.066...
            >>> view.snapToGrid(datetime(2004, 8, 1, 8, 7, tzinfo=utc))
            0.466...
            >>> view.snapToGrid(datetime(2004, 8, 1, 8, 8, tzinfo=utc))
            0.533...
            >>> view.snapToGrid(datetime(2004, 8, 1, 8, 15, tzinfo=utc))
            1.0

        Timestamps before starthour are clipped to 0

            >>> view.snapToGrid(datetime(2004, 8, 1, 7, 30, tzinfo=utc))
            0.0
            >>> view.snapToGrid(datetime(2004, 7, 30, 16, 30, tzinfo=utc))
            0.0

        Timestamps after endhour are clipped to the bottom

            >>> view.snapToGrid(datetime(2004, 8, 1, 18, 0, tzinfo=utc))
            40.0
            >>> view.snapToGrid(datetime(2004, 8, 1, 18, 20, tzinfo=utc))
            40.0
            >>> view.snapToGrid(datetime(2004, 8, 2, 10, 40, tzinfo=utc))
            40.0

        Corner case: starthour == 0, endhour == 24

            >>> view.starthour = 0
            >>> view.endhour = 24

            >>> view.snapToGrid(datetime(2004, 8, 1, 0, 0, tzinfo=utc))
            0.0
            >>> view.snapToGrid(datetime(2004, 8, 1, 2, 0, tzinfo=utc))
            8.0
            >>> view.snapToGrid(datetime(2004, 7, 30, 16, 30, tzinfo=utc))
            0.0
            >>> view.snapToGrid(datetime(2004, 8, 1, 23, 55, tzinfo=utc))
            95.666...
            >>> view.snapToGrid(datetime(2004, 8, 2, 10, 40, tzinfo=utc))
            96.0

        """

    def test_eventTop(self):
        from schooltool.app.browser.cal import DailyCalendarView
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
            >>> app = sbsetup.setUpSchoolToolSite()
            >>> setup.setUpAnnotations()
            >>> registerCalendarHelperViews()
            >>> registerCalendarSubscribers()
            >>> sbsetup.setUpSessions()
            >>> setUpTimetabling()
            >>> setUpDateManagerStub(date(2005, 5, 13))

        DailyCalendarView.getAllDayEvents returns a list of wrapped
        all-day calendar events for the date of the view cursor.

            >>> from schooltool.app.browser.cal import DailyCalendarView
            >>> from schooltool.app.cal import Calendar
            >>> from schooltool.person.person import Person
            >>> person = app['persons']['ignas'] = Person(u'Ignas')
            >>> cal = Calendar(person)
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

        >>> sbsetup.setUpSessions()

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
        >>> view.cursor == test_today
        True

    The date can be provided in the request:

        >>> request.form['date'] = '2005-01-02'
        >>> view.update()
        >>> view.cursor
        datetime.date(2005, 1, 2)

    update() stores the last visited day in the session:

        >>> from zope.session.interfaces import ISession
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
        >>> view.current() == 'http://127.0.0.1/calendar/%s' % test_today
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
        >>> view.current() == fmt % test_today.isocalendar()[:2]
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


class SimpleEventStub(object):
    def __init__(self, dtstart, duration, title, allday):
        self.dtstart = dtstart
        self.duration = duration
        self.title = title
        self.allday = allday


def makeEventForDisplay(y, m, d, h, min, title='', duration=None, allday=False):
    if duration is None:
        duration = timedelta(0, 3600)
    ev = SimpleEventStub(datetime(y, m, d, h, min, tzinfo=utc),
                         duration, title, allday)
    return EventForDisplay(
        ev, 'request', 'color1', 'color2', ISchoolToolCalendar(Person()),
        ev.dtstart.tzinfo)


def setUpWeekForCalendar():
    sun = CalendarDay(datetime(2009, 06, 21))
    mon = CalendarDay(datetime(2009, 06, 22))
    tue = CalendarDay(datetime(2009, 06, 23))
    wed = CalendarDay(datetime(2009, 06, 24), events=[
        makeEventForDisplay(2009, 06, 24, 10, 15, title='3a'),
        makeEventForDisplay(2009, 06, 24, 12, 15, title='3b'),
        ])
    thu = CalendarDay(datetime(2009, 06, 25), events=[
        makeEventForDisplay(2009, 06, 25, 10, 45, title='4a'),
        makeEventForDisplay(2009, 06, 25, 10, 45, title='4b'),
        makeEventForDisplay(2009, 06, 25, 12, 15, title='4c'),
        ])
    fri = CalendarDay(datetime(2009, 06, 26), events=[
        makeEventForDisplay(2009, 06, 26, 10, 00, title='allday', allday=True)])
    sat = CalendarDay(datetime(2009, 06, 27))
    return [sun, mon, tue, wed, thu, fri, sat]


def doctest_WeeklyCalendarView_getCurrentWeekEvents():
    """Tests for WeeklyCalendarView.getCurrentWeekEvents

        >>> from schooltool.app.browser.cal import WeeklyCalendarView

        >>> from schooltool.app.cal import Calendar
        >>> calendar = Calendar(Person())
        >>> directlyProvides(calendar, IContainmentRoot)

        >>> this_week = []
        >>> class ViewForTest(WeeklyCalendarView):
        ...     cursor = None
        ...     getWeek = lambda self, cursor: this_week

    Populate this week with events and look at the calendar.

        >>> this_week[:] = setUpWeekForCalendar()
        >>> from schooltool.app.browser.cal import short_day_of_week_names
        >>> day_names = [translate(short_day_of_week_names[day.date.weekday()])
        ...              for day in this_week]
        >>> def print_table(events):
        ...     print '     |'.join(day_names)
        ...     for slot in events:
        ...         print '|'.join(
        ...             ['%7s ' % ', '.join([e and e.title or '' for e in evs])
        ...              for evs in slot])

        >>> view = ViewForTest(calendar, TestRequest())
        >>> print_table(view.getCurrentWeekEvents(lambda e, day: True))
        Sun     |Mon     |Tue     |Wed     |Thu     |Fri     |Sat
                |        |        |        |        | allday |
                |        |        |     3a |        |        |
                |        |        |        | 4a, 4b |        |
                |        |        |     3b |     4c |        |

    """


def doctest_WeeklyCalendarView_getCurrentWeekTimetableEvents():
    """Tests for WeeklyCalendarView.getCurrentWeekTimetableEvents

        >>> from schooltool.app.browser.cal import WeeklyCalendarView

        >>> from schooltool.app.cal import Calendar
        >>> calendar = Calendar(Person())
        >>> directlyProvides(calendar, IContainmentRoot)

        >>> def format_events(events):
        ...     if isinstance(events, EventForDisplay):
        ...         return '%d:%d %s' % (
        ...             events.dtstart.hour, events.dtstart.minute, events.title)
        ...     elif hasattr(events, '__iter__'):
        ...         return [format_events(e) for e in events]
        ...     else:
        ...         return events

        >>> def print_table(events):
        ...     print '     |'.join(day_names)
        ...     for slot in events:
        ...         print '|'.join(
        ...             ['%7s ' % ', '.join([e and e.title or '' for e in evs])
        ...              for evs in slot])

        >>> this_week = []
        >>> class ViewForTest(WeeklyCalendarView):
        ...     cursor = None
        ...     getWeek = lambda self, cursor: this_week

    Set up the timetable view.

        >>> def makePeriodTuple(day, h, m):
        ...     starts = datetime(2009, 06, day, h, m, tzinfo=utc)
        ...     return ('period', starts, timedelta(0, 3600))

        >>> periods = {
        ...     str(date(2009, 06, 22)):
        ...         [makePeriodTuple(22, 10, 45),
        ...          makePeriodTuple(22, 11, 45),
        ...          makePeriodTuple(22, 12, 45),
        ...         ],
        ...     str(date(2009, 06, 23)):
        ...         [makePeriodTuple(23, 8, 0),
        ...         ],
        ...     str(date(2009, 06, 24)):
        ...         [makePeriodTuple(24, 9, 15),
        ...          makePeriodTuple(24, 10, 15),
        ...          makePeriodTuple(24, 11, 15),
        ...          makePeriodTuple(24, 12, 15),
        ...         ],
        ...     str(date(2009, 06, 25)):
        ...         [makePeriodTuple(25, 12, 15),
        ...         ],
        ... }

        >>> class CalendarRowsStub(object):
        ...     getPeriods = lambda self, date: periods.get(str(date.date()), [])
        >>> daily_calendar_rows = CalendarRowsStub()

        >>> provideAdapter(lambda c, r: daily_calendar_rows,
        ...                adapts=(ISchoolToolCalendar, IHTTPRequest),
        ...                provides=Interface,
        ...                name='daily_calendar_rows')

    Populate this week with events and look at the calendar.

        >>> this_week[:] = setUpWeekForCalendar()
        >>> from schooltool.app.browser.cal import short_day_of_week_names
        >>> day_names = [translate(short_day_of_week_names[day.date.weekday()])
        ...              for day in this_week]

        >>> view = ViewForTest(calendar, TestRequest())
        >>> events = format_events(view.getCurrentWeekTimetableEvents())

        >>> for period in events:
        ...    print period
        [[None], [None], [None], [None], ['12:15 4c'], [], []]
        [[None], [None], ['10:15 3a'], [], [], [], []]
        [[None], ['12:15 3b'], [], [], [], [], []]

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
        >>> dt = test_today.strftime("%Y-%m")
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
        >>> expected = 'http://127.0.0.1/calendar/%d' % test_today.year
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

        >>> week = view.getWeek(test_today)
        >>> print view.renderRow(week, test_today.month)
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
        >>> app = sbsetup.setUpSchoolToolSite()
        >>> setUpTimetabling()
        >>> registerCalendarHelperViews()
        >>> registerCalendarSubscribers()

        >>> today = date(2005, 3, 13)
        >>> setUpDateManagerStub(today)

        >>> from schooltool.app.browser.cal import AtomCalendarView

        >>> from schooltool.app.cal import Calendar
        >>> person = Person()
        >>> calendar = Calendar(person)
        >>> directlyProvides(person, IContainmentRoot)

    Populate the calendar:

        >>> lastweek = CalendarEvent(datetime(today.year,
        ...                                   today.month,
        ...                                   today.day, hour=12) -
        ...                          timedelta(8),
        ...                          timedelta(hours=3), "Last Week")
        >>> monday_date = (datetime(today.year, today.month, today.day, hour=12) -
        ...                timedelta(today.weekday()))
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

        >>> dt = datetime(2005, 03, 29, 15, 33, 22, tzinfo=utc)
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
        >>> view.simple_event_template = lambda: 'Do you realy want to delete this event?'
        >>> view()
        'Do you realy want to delete this event?'

    And confirm:

        >>> request = TestRequest(form={'event_id': 'killme',
        ...                             'date': '2005-02-03',
        ...                             'DELETE': 'Delete'})
        >>> view = EventDeleteView(cal, request)
        >>> view()

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
        >>> view()

        >>> redirected(request)
        True

    That was easy.  Now the hard part: recurrent events.  Let's create one.

        >>> dtstart = datetime(2005, 2, 3, 12, 15)
        >>> exceptions = [date(2005, 2, 4), date(2005, 2, 6)]
        >>> rrule = DailyRecurrenceRule(exceptions=exceptions)
        >>> recurrer = CalendarEvent(dtstart, timedelta(hours=3), "Recurrer",
        ...                          unique_id='rec', recurrence=rrule)
        >>> cal.addEvent(recurrer)

    Now, if we try to delete this event, the view will not know what
    to do, so it will ask the user and set the attribute event on
    itself to the event being deleted.

        >>> request = TestRequest(form={'event_id': 'rec',
        ...                             'date': '2005-02-05'})
        >>> view = EventDeleteView(cal, request)
        >>> view.recevent_template = lambda: 'What do you want to do with this event?'
        >>> view()
        'What do you want to do with this event?'
        >>> view.event is recurrer
        True
        >>> redirected(request)
        False

    The event has not been touched, because we did not issue a command.  We'll
    just check that no exceptions have been added:

        >>> cal.find('rec').recurrence.exceptions
        (datetime.date(2005, 2, 4), datetime.date(2005, 2, 6))

    We can easily return back to the daily view:

        >>> request.form['CANCEL'] = 'Cancel'
        >>> view()
        >>> redirected(request)
        True
        >>> del request.form['CANCEL']

    OK.  First, let's try and delete only the current recurrence:

        >>> request.form['CURRENT'] = 'Current'
        >>> view()
        >>> redirected(request)
        True

    As a result, a new exception date should have been added:

        >>> cal.find('rec').recurrence.exceptions[-1]
        datetime.date(2005, 2, 5)

    Now, if we decide to remove all exceptions in the future, the recurrence
    rule's until argument will be updated:

        >>> del request.form['CURRENT']
        >>> request.form['FUTURE'] = 'Future'
        >>> view()
        >>> redirected(request)
        True

        >>> cal.find('rec').recurrence.until
        datetime.date(2005, 2, 4)

    Finally, let's remove the event altogether.

        >>> del request.form['FUTURE']
        >>> request.form['ALL'] = 'All'
        >>> view()

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
        >>> view()
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
        >>> view()
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
        >>> print view()
        None


    Note that if the context calendar's parent is different from the
    principal's calendar, overlaid events are not even scanned.

        >>> foe = container['foe'] = Person('foe')
        >>> view.context.__parent__ = foe

        >>> print view()
        None

    """


class TestDailyCalendarRowsView(NiceDiffsMixin, unittest.TestCase):

    def setUp(self):
        layeredTestSetup()
        app = ISchoolToolApplication(None)
        self.person = app['persons']['person'] = Person('person')

        # set up schoolyear
        from schooltool.schoolyear.schoolyear import SchoolYear
        from schooltool.schoolyear.interfaces import ISchoolYearContainer
        ISchoolYearContainer(app)['2004'] = SchoolYear("2004", date(2004, 9, 1), date(2004, 12, 31))

        # set up the timetable schema
        days = ['A', 'B', 'C']
        schema = self.createSchema(days,
                                   ['1', '2', '3', '4'],
                                   ['1', '2', '3', '4'],
                                   ['1', '2', '3', '4'])
        schema.timezone = 'Europe/London'
        template = SchooldayTemplate()
        template.add(SchooldaySlot(time(8, 0), timedelta(hours=1)))
        template.add(SchooldaySlot(time(10, 15), timedelta(hours=1)))
        template.add(SchooldaySlot(time(11, 30), timedelta(hours=1)))
        template.add(SchooldaySlot(time(12, 30), timedelta(hours=2)))
        schema.model = SequentialDaysTimetableModel(days, {None: template})

        ITimetableSchemaContainer(app)['default'] = schema

        # set up terms
        from schooltool.term.term import Term
        terms = ITermContainer(app)
        terms['term'] = term = Term("Some term", date(2004, 9, 1),
                                    date(2004, 12, 31))
        term.add(date(2004, 11, 5))

    def tearDown(self):
        layeredTestTearDown()

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
        result = list(view.calendarRows(date(2004, 11, 5), 8, 19, events=[]))

        expected = [("8:00", dt('08:00'), timedelta(hours=1)),
                    ("9:00", dt('09:00'), timedelta(hours=1)),
                    ("10:00", dt('10:00'), timedelta(hours=1)),
                    ("11:00", dt('11:00'), timedelta(hours=1)),
                    ("12:00", dt('12:00'), timedelta(hours=1)),
                    ("13:00", dt('13:00'), timedelta(hours=1)),
                    ("14:00", dt('14:00'), timedelta(hours=1)),
                    ("15:00", dt('15:00'), timedelta(hours=1)),
                    ("16:00", dt('16:00'), timedelta(hours=1)),
                    ("17:00", dt('17:00'), timedelta(hours=1)),
                    ("18:00", dt('18:00'), timedelta(hours=1))]

        self.assertEquals(result, expected)

    def test_calendarRows_otherTZ(self):
        from schooltool.app.browser.cal import DailyCalendarRowsView
        from schooltool.app.security import Principal

        request = TestRequest()
        principal = Principal('person', 'Some person', person=self.person)
        request.setPrincipal(principal)
        view = DailyCalendarRowsView(ISchoolToolCalendar(self.person), request)

        km = timezone('Asia/Kamchatka')
        view.getPersonTimezone = lambda: km

        result = list(view.calendarRows(date(2004, 11, 5), 8, 19, events=[]))

        kmdt = lambda arg: km.localize(parse_datetime('2004-11-05 %s:00' %
                                                      arg))

        expected = [('8:00', kmdt('8:00'), timedelta(0, 3600)),
                    ('9:00', kmdt('9:00'), timedelta(0, 3600)),
                    ('10:00', kmdt('10:00'),timedelta(0, 3600)),
                    ('11:00', kmdt('11:00'),timedelta(0, 3600)),
                    ('12:00', kmdt('12:00'),timedelta(0, 3600)),
                    ('13:00', kmdt('13:00'),timedelta(0, 3600)),
                    ('14:00', kmdt('14:00'),timedelta(0, 3600)),
                    ('15:00', kmdt('15:00'),timedelta(0, 3600)),
                    ('16:00', kmdt('16:00'),timedelta(0, 3600)),
                    ('17:00', kmdt('17:00'),timedelta(0, 3600)),
                    ('18:00', kmdt('18:00'),timedelta(0, 3600))]

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

        result = list(view.calendarRows(date(2004, 11, 5), 8, 19, events=[]))

        expected = [("%d:00" % i, dt('%d:00' % i), timedelta(hours=1))
                    for i in range(8, 19)]
        self.assertEquals(result, expected)

    def test_calendarRows_default(self):
        from schooltool.app.browser.cal import DailyCalendarRowsView

        request = TestRequest()
        # do not set the principal
        view = DailyCalendarRowsView(ISchoolToolCalendar(self.person), request)
        result = list(view.calendarRows(date(2004, 11, 5), 8, 19, events=[]))

        # the default is not to show periods
        expected = [("%d:00" % i, dt('%d:00' % i), timedelta(hours=1))
                    for i in range(8, 19)]
        self.assertEquals(result, expected)

    def test_getPersonTimezone(self):
        from schooltool.app.browser.cal import DailyCalendarRowsView
        request = TestRequest()
        view = DailyCalendarRowsView(ISchoolToolCalendar(self.person), request)

        # when there is no principal - the default timezone should be
        # returned
        self.assertEquals(view.getPersonTimezone(), timezone('UTC'))


def doctest_CalendarListSubscriber(self):
    """Tests for CalendarListSubscriber.

    This subscriber only has the getCalendars() method.

    CalendarListSubscriber.getCalendars returns a list of calendars
    that should be displayed.  This list always includes the context
    of the subscriber, but it may also include other calendars as
    well.

    Some initial setup:

        >>> sbsetup.setUpCalendaring()

    A handful of useful stubs:

        >>> class CalendarStub:
        ...     def __init__(self, title):
        ...         self.title = title
        ...     def _getParent(self):
        ...         return PersonStub(self.title, self)
        ...     __parent__ = property(_getParent)

        >>> from zope.interface import implements
        >>> class OverlayInfoStub:
        ...
        ...     def __init__(self, title, color1, color2,
        ...                  show=True):
        ...         self.calendar = CalendarStub(title)
        ...         self.color1 = color1
        ...         self.color2 = color2
        ...         self.show = show

        >>> from schooltool.person.interfaces import IPersonPreferences
        >>> from schooltool.app.interfaces import IHaveCalendar
        >>> from schooltool.app.cal import CALENDAR_KEY
        >>> from zope.annotation.interfaces import IAttributeAnnotatable
        >>> class PersonStub:
        ...     implements(IAttributeAnnotatable, IHaveCalendar)
        ...     def __init__(self, title, calendar=None):
        ...         self.title = title
        ...         self.__annotations__= {CALENDAR_KEY: calendar}
        ...     def __conform__(self, interface):
        ...         if interface is IPersonPreferences:
        ...             return PreferenceStub()
        ...     overlaid_calendars = [
        ...         OverlayInfoStub('Other Calendar', 'red', 'blue',
        ...                         True),
        ...         OverlayInfoStub('Another Calendar', 'green', 'red',
        ...                         False),
        ...         OverlayInfoStub('Interesting Calendar', 'yellow', 'white',
        ...                         True),
        ...         OverlayInfoStub('Boring Calendar', 'brown', 'magenta',
        ...                         False)]

        >>> class PreferenceStub:
        ...     def __init__(self):
        ...         self.weekstart = pycalendar.MONDAY
        ...         self.timeformat = "%H:%M"
        ...         self.dateformat = "YYYY-MM-DD"
        ...         self.timezone = 'UTC'

    A simple check:

        >>> import calendar as pycalendar
        >>> calendar = CalendarStub('My Calendar')
        >>> request = TestRequest()
        >>> subscriber = CalendarListSubscriber(calendar, request)
        >>> for c, col1, col2 in subscriber.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        My Calendar (#9db8d2, #7590ae)

    If the authenticated user is looking at his own calendar, then
    a list of overlaid calendars is taken into consideration

        >>> class PrincipalStub:
        ...     def __init__(self):
        ...         self.person = PersonStub('x', calendar=calendar)
        ...     def __conform__(self, interface):
        ...         if interface is IPerson:
        ...             return self.person
        >>> principal = PrincipalStub()
        >>> request.setPrincipal(principal)

        >>> for c, col1, col2 in subscriber.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        My Calendar (#9db8d2, #7590ae)
        Other Calendar (red, blue)
        Interesting Calendar (yellow, white)

    Only the context calendar is shown if the user is looking at
    someone else's calendar:

        >>> subscriber = CalendarListSubscriber(CalendarStub('Some Calendar'),
        ...                                     request)
        >>> for c, col1, col2 in subscriber.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        Some Calendar (#9db8d2, #7590ae)

    """


def doctest_DaysCache():
    """Unit tests for DaysCache.

    We will need a pretend expensive computation function that returns
    a list of dates.  Since it is expensive, we want to see when exactly
    it gets called.

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
    suite.addTest(makeLayeredSuite(TestDailyCalendarRowsView,
                                   app_functional_layer))
    suite.addTest(doctest.DocTestSuite(
        setUp=setUp, tearDown=tearDown,
        optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF|
                    doctest.NORMALIZE_WHITESPACE|
                    doctest.REPORT_ONLY_FIRST_FAILURE))
    suite.addTest(doctest.DocTestSuite('schooltool.app.browser.cal'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
