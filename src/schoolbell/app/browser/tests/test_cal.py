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
from zope.app.traversing.interfaces import IContainmentRoot


def doctest_CalendarOwnerTraverser():
    """Tests for CalendarOwnerTraverse.

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

    However, we should be able to access other views of the object:

        >>> from zope.app.publisher.browser import BrowserView
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


def doctest_PlainCalendarView():
    """Tests for PlainCalendarView.

        >>> from schoolbell.app.browser.cal import PlainCalendarView
        >>> from schoolbell.app.app import Calendar
        >>> calendar = Calendar()
        >>> request = TestRequest()
        >>> view = PlainCalendarView(calendar, request)
        >>> view.update()
        >>> len(calendar)
        0

        >>> request = TestRequest()
        >>> request.form = {'GENERATE': ''}
        >>> view = PlainCalendarView(calendar, request)
        >>> view.update()
        >>> len(calendar) > 0
        True

    """


def doctest_CalendarDay():
    """A calendar day is a set of events that took place on a particular day.

        >>> from schoolbell.app.browser.cal import CalendarDay
        >>> day1 = CalendarDay(date(2004, 8, 5))
        >>> day2 = CalendarDay(date(2004, 7, 15), ["abc", "def"])
        >>> day1.date
        datetime.date(2004, 8, 5)
        >>> day1.events
        []
        >>> day2.date
        datetime.date(2004, 7, 15)
        >>> day2.events
        ['abc', 'def']

        >>> day1 > day2 and not day1 < day2
        True
        >>> day2 == CalendarDay(date(2004, 7, 15))
        True

    """


def createEvent(dtstart, duration, title, **kw):
    """Create a SimpleCalendarEvent.

      >>> from schoolbell.calendar.simple import SimpleCalendarEvent
      >>> e1 = createEvent('2004-01-02 14:45:50', '5min', 'title')
      >>> e1 == SimpleCalendarEvent(datetime(2004, 1, 2, 14, 45, 50),
      ...                timedelta(minutes=5), 'title', unique_id=e1.unique_id)
      True

      >>> e2 = createEvent('2004-01-02 14:45', '3h', 'title')
      >>> e2 == SimpleCalendarEvent(datetime(2004, 1, 2, 14, 45),
      ...                timedelta(hours=3), 'title', unique_id=e2.unique_id)
      True

      >>> e3 = createEvent('2004-01-02', '2d', 'title')
      >>> e3 == SimpleCalendarEvent(datetime(2004, 1, 2),
      ...                timedelta(days=2), 'title', unique_id=e3.unique_id)
      True

    createEvent is very strict about the format of it arguments, and terse in
    error reporting, but it's OK, as it is only used in unit tests.
    """
    from schoolbell.calendar.simple import SimpleCalendarEvent
    from schoolbell.app.browser.cal import parse_datetime
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
    return SimpleCalendarEvent(dtstart, dur, title, **kw)


class TestCalendarViewBase(unittest.TestCase):
    # Legacy unit tests from SchoolTool.

    def test_dayTitle(self):
        from schoolbell.app.browser.cal import CalendarViewBase
        view = CalendarViewBase(None, None)
        dt = datetime(2004, 7, 1)
        self.assertEquals(view.dayTitle(dt), "Thursday, 2004-07-01")

    def test_ellipsizeTitle(self):
        from schoolbell.app.browser.cal import CalendarViewBase

        under17 = '1234567890123456'
        over17 = '12345678901234567'

        view = CalendarViewBase(None, None)
        self.assertEquals(view.ellipsizeTitle(under17), under17)
        self.assertEquals(view.ellipsizeTitle(over17), '123456789012345...')

    def test_getWeek(self):
        from schoolbell.app.browser.cal import CalendarViewBase, CalendarDay
        from schoolbell.app.app import Calendar

        cal = Calendar()
        view = CalendarViewBase(cal, None)
        self.assertEquals(view.first_day_of_week, 0) # Monday by default

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
        from schoolbell.app.app import Calendar

        cal = Calendar()
        view = CalendarViewBase(cal, None)
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

    def assertEqualEventLists(self, result, expected):
        fmt = lambda x: '[%s]' % ', '.join([e.title for e in x])
        self.assertEquals(result, expected,
                          '%s != %s' % (fmt(result), fmt(expected)))

    def test_getDays(self):
        from schoolbell.app.browser.cal import CalendarViewBase
        from schoolbell.app.app import Calendar

        e0 = createEvent('2004-08-10 11:00', '1h', "e0")
        #e1 = createEvent('2004-08-11 12:00', '1h', "e1", privacy="hidden")
        e2 = createEvent('2004-08-11 11:00', '1h', "e2")
        e3 = createEvent('2004-08-12 23:00', '4h', "e3")
        e4 = createEvent('2004-08-15 11:00', '1h', "e4")
        e5 = createEvent('2004-08-10 09:00', '3d', "e5")
        e6 = createEvent('2004-08-13 00:00', '1d', "e6")
        e7 = createEvent('2004-08-12 00:00', '1d+1sec', "e7")
        e8 = createEvent('2004-08-15 00:00', '0sec', "e8")

        cal = Calendar()
#        for e in [e0, e1, e2, e3, e4, e5, e6, e7, e8]:
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

#        self.assertEqualEventLists(days[0].events, [e5, e0])            # 10
        self.assertEqualEventLists(days[0].events, [e5])                # 10
#        self.assertEqualEventLists(days[1].events, [e5, e2, e1])        # 11
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
#        self.assertEqualEventLists(days[0].events, [e5, e2, e1])
        self.assertEqualEventLists(days[0].events, [e5])

        # XXX Disabled because we do not support hidden events yet.
        ## Check that the hidden event is excluded for another person
        #view.request = RequestStub(authenticated_user=self.person2)
        #start = date(2004, 8, 11)
        #end = date(2004, 8, 12)
        #days = view.getDays(start, end)

        #self.assertEqualEventLists(days[0].events, [e5, e2])            # 11


def doctest_CalendarViewBase():
    """Tests for CalendarViewBase.

        >>> from schoolbell.app.browser.cal import CalendarViewBase

        >>> from schoolbell.app.app import Calendar
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)

    CalendarViewBase has a method calURL used for forming links to other
    calendar views on other dates.

        >>> request = TestRequest()
        >>> view = CalendarViewBase(calendar, request)
        >>> view.cursor = date(2005, 2, 3)

        >>> view.calURL("quarterly")
        'http://127.0.0.1/calendar/quarterly.html?date=2005-02-03'
        >>> view.calURL("quarterly", date(2005, 12, 13))
        'http://127.0.0.1/calendar/quarterly.html?date=2005-12-13'

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

def doctest_WeeklyCalendarView():
    """Tests for WeeklyCalendarView.

        >>> from schoolbell.app.browser.cal import WeeklyCalendarView

        >>> from schoolbell.app.app import Calendar
        >>> calendar = Calendar()
        >>> directlyProvides(calendar, IContainmentRoot)
        >>> view = WeeklyCalendarView(calendar, TestRequest())

    title() forms a nice title for the calendar:

        >>> view.cursor = date(2005, 2, 3)
        >>> view.title()
        u'February, 2005 (week 5)'

    prevWeek() and nextWeek() are provided to get different dates:

        >>> view.cursor = date(2004, 8, 18)
        >>> view.prevWeek()
        datetime.date(2004, 8, 11)
        >>> view.nextWeek()
        datetime.date(2004, 8, 25)

        >>> view.cursor = "works"
        >>> view.getWeek = lambda x: "really " + x
        >>> view.getCurrentWeek()
        'really works'

    """


def setUp(test):
    setup.placelessSetUp()
    setup.setUpTraversal()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCalendarViewBase))
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown))
    suite.addTest(doctest.DocTestSuite('schoolbell.app.browser.cal'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
