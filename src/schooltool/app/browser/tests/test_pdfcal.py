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
Tests for SchoolTool calendaring views.
"""

import unittest
import doctest
from pprint import pprint
from datetime import datetime, date, timedelta

from zope.component import provideAdapter
from zope.interface import implements
from zope.publisher.browser import TestRequest
from zope.app.testing import setup
from zope.annotation.interfaces import IAttributeAnnotatable

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.calendar.utils import parse_date
from schooltool.app.cal import CalendarEvent
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.person.person import Person
from schooltool.resource.resource import Resource
from schooltool.testing import setup as sbsetup
from schooltool.app.app import getApplicationPreferences
from schooltool.app.browser.pdfcal import (
    DailyPDFCalendarView,
    WeeklyPDFCalendarView,
    MonthlyPDFCalendarView)


class ApplicationStub(object):
    implements(ISchoolToolApplication, IAttributeAnnotatable)
    def __init__(self):
        pass


def stub_cal_class(klass, extra_calendars=[]):
    extra_calendars = extra_calendars[:]
    class StubbedCalendarView(klass):
        def getCalendars(self):
            return [self.context] + extra_calendars
        def dateTitle(self):
            return parse_date(self.request['date'])
    return StubbedCalendarView


def doctest_DailyPDFCalendarView():
    """Tests for DailyPDFCalendarView basic methods and properties.

        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> person = Person(title="Mr. Smith")
        >>> calendar = ISchoolToolCalendar(person)
        >>> view = stub_cal_class(DailyPDFCalendarView)(calendar, request)

    Daily view has a title.

        >>> print view.owner
        Mr. Smith

        >>> print view.title
        Daily calendar for Mr. Smith

    But no subtitle.

        >>> print view.subtitle
        <BLANKLINE>

    We stubbed the date retrieval mechanism to parse the date from request.
    In reality, if 'date' is absent in request, today is returned.

        >>> view.getDate()
        datetime.date(2005, 7, 8)

        >>> print view.dayTitle(view.getDate())
        2005-07-08, Friday

    """


def doctest_DailyPDFCalendarView_getCalendars(self):
    """Test for DailyPDFCalendarView.getCalendars().

    getCalendars() only delegates the task to the ICalendarProvider
    subscriber.  We will provide a stub subscriber to test the method.

        >>> class CalendarListSubscriberStub(object):
        ...     def __init__(self,context, request):
        ...         pass
        ...     def getCalendars(self):
        ...         return [('some calendar', 'color1', 'color2'),
        ...                 ('another calendar', 'color1', 'color2')]

        >>> from zope.component import provideSubscriptionAdapter
        >>> from zope.publisher.interfaces.http import IHTTPRequest
        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> from schooltool.app.browser.interfaces import ICalendarProvider
        >>> provideSubscriptionAdapter(CalendarListSubscriberStub,
        ...                            (ISchoolToolCalendar, IHTTPRequest),
        ...                            ICalendarProvider)

        >>> from schooltool.app.cal import Calendar
        >>> view = DailyPDFCalendarView(Calendar(None), TestRequest())

    Now, if we call the method, the output of our stub will be returned:

        >>> view.getCalendars()
        ['some calendar', 'another calendar']

    """


def doctest_DailyPDFCalendarView_getTimezone():
    """Tests for DailyPDFCalendarView.getTimezone.

    We need some extra setup here:

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> setup.setUpAnnotations()

        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> person = Person(title="Mr. Smith")
        >>> calendar = ISchoolToolCalendar(person)
        >>> view = stub_cal_class(DailyPDFCalendarView)(calendar, request)
        >>> view.getTimezone()
        <UTC>

        >>> app = ISchoolToolApplication(None)
        >>> IApplicationPreferences(app).timezone = "Europe/Vilnius"

        >>> from pytz import timezone
        >>> view.getTimezone() == timezone('Europe/Vilnius')
        True

    """


def doctest_DailyPDFCalendarViewBase_tables():
    r"""Tests for DailyPDFCalendarView.tables.


        >>> calendar = ISchoolToolCalendar(Person(title="Mr. Smith"))
        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> view = stub_cal_class(DailyPDFCalendarView)(calendar, request)

    There is only a single table for the current day.

        >>> view.buildDayTable = lambda date: 'Table for %s' % date
        >>> view.tables()
        ['Table for 2005-07-08']

    """


def doctest_DailyPDFCalendarViewBase_dayEvents():
    """Event listing tests.

        >>> calendar = ISchoolToolCalendar(Person(title="Mr. Smith"))
        >>> resource = Resource()
        >>> calendar2 = ISchoolToolCalendar(resource)
        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> view = stub_cal_class(DailyPDFCalendarView)(calendar, request)
        >>> view.getCalendars = lambda: [calendar, calendar2]

    First check the simple case when the calendar is empty:

        >>> view.dayEvents(date(2005, 7, 8))
        []

    Let's add one event.

        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=5), "evt")
        >>> calendar.addEvent(evt)

    The event should appear in the result

        >>> view.dayEvents(date(2005, 7, 8)) == [evt]
        True

        >>> view.dayEvents(date(2005, 7, 9))
        []

    We will add some events to the other calendar to test overlaying.
    If several events occur, they should be returned sorted by start time:

        >>> evt2 = CalendarEvent(datetime(2005, 7, 8, 9, 12),
        ...                      timedelta(hours=5), "evt2")
        >>> calendar2.addEvent(evt2)

    Let's add a recurring event to check expansion:

        >>> from schooltool.calendar.recurrent import DailyRecurrenceRule
        >>> evt3 = CalendarEvent(datetime(2005, 7, 5, 9, 3),
        ...                      timedelta(hours=2), "evt3",
        ...                      recurrence=DailyRecurrenceRule())
        >>> calendar2.addEvent(evt3)

        >>> result = view.dayEvents(date(2005, 7, 8))
        >>> [event.title for event in result]
        ['evt3', 'evt', 'evt2']

    All-day events always appear in front:

        >>> ad_evt = CalendarEvent(datetime(2005, 7, 8, 20, 3),
        ...                        timedelta(hours=2), "allday", allday=True)
        >>> calendar.addEvent(ad_evt)

        >>> result = view.dayEvents(date(2005, 7, 8))
        >>> [event.title for event in result]
        ['allday', 'evt3', 'evt', 'evt2']

    Booked event dupes are eliminated:

        >>> evt.bookResource(resource)
        >>> result = view.dayEvents(date(2005, 7, 8))
        >>> [event.title for event in result]
        ['allday', 'evt3', 'evt', 'evt2']

    """


def doctest_DailyPDFCalendarView_dayEvents_timezone():
    """Let's test that dayEvents handles timezones correctly.

    First' let's someone setup the user a timezone:

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> setup.setUpAnnotations()
        >>> app = ISchoolToolApplication(None)
        >>> IApplicationPreferences(app).timezone = "Europe/Vilnius"

    Let's create a calendar and a view:

        >>> calendar = ISchoolToolCalendar(Person(title="Mr. Smith"))
        >>> request = TestRequest()
        >>> view = stub_cal_class(DailyPDFCalendarView)(calendar, request)

    Let's add several edge-case events to the user's calendar:

        >>> from pytz import utc
        >>> calendar.addEvent(
        ...     CalendarEvent(datetime(2005, 7, 7, 20, 0, tzinfo=utc),
        ...                   timedelta(minutes=10), '20Z'))
        >>> calendar.addEvent(
        ...     CalendarEvent(datetime(2005, 7, 7, 21, 0, tzinfo=utc),
        ...                   timedelta(minutes=10), '21Z'))
        >>> calendar.addEvent(
        ...     CalendarEvent(datetime(2005, 7, 7, 22, 0, tzinfo=utc),
        ...                   timedelta(minutes=10), '22Z'))

        >>> calendar.addEvent(
        ...     CalendarEvent(datetime(2005, 7, 8, 19, 0, tzinfo=utc),
        ...                   timedelta(minutes=10), '19Z+1d'))
        >>> calendar.addEvent(
        ...     CalendarEvent(datetime(2005, 7, 8, 20, 0, tzinfo=utc),
        ...                   timedelta(minutes=10), '20Z+1d'))
        >>> calendar.addEvent(
        ...     CalendarEvent(datetime(2005, 7, 8, 21, 0, tzinfo=utc),
        ...                   timedelta(minutes=10), '21Z+1d'))

    We should get only the events that fall into July 8 in Vilnius
    timezone:

        >>> result = view.dayEvents(date(2005, 7, 8))
        >>> [event.title for event in result]
        ['21Z', '22Z', '19Z+1d', '20Z+1d']

    """


def doctest_DailyPDFCalendarView_buildDayTable():
    r"""Tests for DailyPDFCalendarView.buildDayTable.

        >>> calendar = ISchoolToolCalendar(Person(title="Mr. Smith"))
        >>> calendar2 = ISchoolToolCalendar(Person(title='Mr. X'))
        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> ViewForTest = stub_cal_class(DailyPDFCalendarView,
        ...                             extra_calendars=[calendar2])
        >>> view = ViewForTest(calendar, request)

    Let's add an ordinary event:

        >>> from pytz import utc
        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10, tzinfo=utc),
        ...                     timedelta(hours=2), "Some event")
        >>> calendar.addEvent(evt)

        >>> rsrc = Resource(title='Some resource')
        >>> evt.bookResource(rsrc)

        >>> pprint(view.buildDayTable(date(2005, 7, 8)))
        {'rows': [{'description': None,
                   'location': None,
                   'resources': 'Some resource',
                   'tags': '',
                   'time': '09:10-11:10',
                   'title': 'Some event'}],
         'title': u'2005-07-08, Friday'}

        >>> calendar.clear()

    And an all-day event:

        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=2), "Long event", allday=True)
        >>> calendar.addEvent(evt)

        >>> pprint(view.buildDayTable(date(2005, 7, 8)))
        {'rows': [{'description': None,
                   'location': None,
                   'resources': '',
                   'tags': '',
                   'time': u'all day',
                   'title': 'Long event'}],
         'title': u'2005-07-08, Friday'}

        >>> calendar.clear()

    Let's create more interesting events now. Add a recurring event with
    description and location.

        >>> from schooltool.calendar.recurrent import DailyRecurrenceRule
        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=2), "Some recurrent event",
        ...                     location=u"\u0105 location",
        ...                     recurrence=DailyRecurrenceRule())
        >>> evt.description = u"Fun every day!"
        >>> calendar.addEvent(evt)

        >>> pprint(view.buildDayTable(date(2005, 7, 8)))
        {'rows': [{'description': u'Fun every day!',
                   'location': u'\u0105 location',
                   'resources': '',
                   'tags': u'recurrent',
                   'time': '09:10-11:10',
                   'title': 'Some recurrent event'}],
         'title': u'2005-07-08, Friday'}

        >>> calendar.clear()

    Overlaid events are also recognized.

        >>> evt2 = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=2), "Recurrent event X",
        ...                     recurrence=DailyRecurrenceRule())
        >>> calendar2.addEvent(evt2)

        >>> pprint(view.buildDayTable(date(2005, 7, 8)))
        {'rows': [{'description': None,
                   'location': None,
                   'resources': '',
                   'tags': u'recurrent, from the calendar of Mr. X',
                   'time': '09:10-11:10',
                   'title': 'Recurrent event X'}],
         'title': u'2005-07-08, Friday'}

    """


def doctest_WeeklyPDFCalendarView():
    r"""Tests for WeeklyPDFCalendarView.

        >>> calendar = ISchoolToolCalendar(Person(title='John'))
        >>> request = TestRequest(form={'date': '2005-07-15'})
        >>> view = stub_cal_class(WeeklyPDFCalendarView)(calendar, request)

    Weekly view has a title, subtitle:

        >>> print view.title
        Weekly calendar for John

        >>> print view.subtitle
        Week 28 (2005-07-11 - 2005-07-17), 2005

    It builds tables for all 7 days of the week, otherwise its identical to
    the daily view.

        >>> view.buildDayTable = lambda date: 'Table for %s' % date
        >>> pprint(view.tables())
        ['Table for 2005-07-11',
         'Table for 2005-07-12',
         'Table for 2005-07-13',
         'Table for 2005-07-14',
         'Table for 2005-07-15',
         'Table for 2005-07-16',
         'Table for 2005-07-17']

    """


def doctest_MonthlyPDFCalendarView():
    r"""Tests for MonthlyPDFCalendarView.

        >>> calendar = ISchoolToolCalendar(Person(title='John'))
        >>> request = TestRequest(form={'date': '2005-02-15'})
        >>> view = stub_cal_class(MonthlyPDFCalendarView)(calendar, request)

    Monthly view has a title, subtitle:

        >>> print view.title
        Monthly calendar for John

        >>> print view.subtitle
        February, 2005

    It builds tables for every day of the month, otherwise its identical to
    the daily view.

        >>> view.buildDayTable = lambda date: 'Table for %s' % date
        >>> pprint(view.tables())
        ['Table for 2005-02-01',
         'Table for 2005-02-02',
         'Table for 2005-02-03',
         'Table for 2005-02-04',
         ...
         'Table for 2005-02-12',
         'Table for 2005-02-13',
         'Table for 2005-02-14',
         ...
         'Table for 2005-02-25',
         'Table for 2005-02-26',
         'Table for 2005-02-27',
         'Table for 2005-02-28']

    """


def pdfSetUp(test=None):
    setup.placefulSetUp()
    sbsetup.setUpCalendaring()
    app = ApplicationStub()
    provideAdapter(lambda x: app, (None,), ISchoolToolApplication)
    provideAdapter(getApplicationPreferences,
                   (ISchoolToolApplication,), IApplicationPreferences)


def pdfTearDown(test=None):
    setup.placefulTearDown()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite('schooltool.app.browser.pdfcal'))
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF
                   | doctest.NORMALIZE_WHITESPACE)
    docsuite = doctest.DocTestSuite(setUp=pdfSetUp, tearDown=pdfTearDown,
                                    optionflags=optionflags)
    suite.addTest(docsuite)
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
