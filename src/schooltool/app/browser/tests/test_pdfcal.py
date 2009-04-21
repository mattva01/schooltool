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
import calendar
from datetime import datetime, date, timedelta

from zope.testing import doctest
from zope.interface import implements
from zope.publisher.browser import TestRequest
from zope.app.testing import setup, ztapi
from zope.publisher.browser import BrowserView
from zope.annotation.interfaces import IAttributeAnnotatable

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.common import SchoolToolMessage as _
from schooltool.app.cal import CalendarEvent
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.person.person import Person
from schooltool.resource.resource import Resource
from schooltool.testing import setup as sbsetup
from schooltool.app.app import getApplicationPreferences


class ApplicationStub(object):
    implements(ISchoolToolApplication, IAttributeAnnotatable)
    def __init__(self):
        pass


def pdfSetUp(test=None):
    setup.placefulSetUp()
    sbsetup.setUpCalendaring()
    app = ApplicationStub()
    ztapi.provideAdapter(None, ISchoolToolApplication,
                         lambda x: app)
    ztapi.provideAdapter(ISchoolToolApplication,
                         IApplicationPreferences,
                         getApplicationPreferences)


def pdfTearDown(test=None):
    setup.placefulTearDown()


##class StubbedBaseView(PDFCalendarViewBase):
##    """A subclass of PDFCalendarViewBase for use in tests."""
##
##    title = _("Calendar for %s")
##
##    def getCalendars(self):
##        return [self.context]
##
##    def buildEventTables(self, date):
##        events = self.dayEvents(date)
##        return events and [self.buildDayTable(events)] or []
##
##    def dateTitle(self, date):
##        return date.isoformat()


def doctest_PDFCalendarViewBase():
    """Tests for PDFCalendarViewBase.

        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> person = Person(title="Mr. Smith")
        >>> view = StubbedBaseView(ISchoolToolCalendar(person), request)

        >>> print view.pdfdata()
        %PDF-1.3...
        ...

        >>> request.response.getHeader('Content-Type')
        'application/pdf'
        >>> request.response.getHeader('Accept-Ranges')
        'bytes'

    If we do not specify a date, today is taken by default:

        >>> request = TestRequest()
        >>> view = StubbedBaseView(ISchoolToolCalendar(person), request)

        >>> print view.pdfdata()
        %PDF-1.3...
        ...

    """


def doctest_PDFCalendarViewBase_getTimezone():
    """Tests for PDFCalendarViewBase.getTimezone.

    We need some extra setup here:

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> setup.setUpAnnotations()

        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> person = Person(title="Mr. Smith")
        >>> view = StubbedBaseView(ISchoolToolCalendar(person), request)
        >>> view.getTimezone()
        <UTC>

        >>> app = ISchoolToolApplication(None)
        >>> IApplicationPreferences(app).timezone = "Europe/Vilnius"

        >>> from pytz import timezone
        >>> view.getTimezone() == timezone('Europe/Vilnius')
        True

    """


def doctest_PDFCalendarViewBase_buildStory():
    r"""Tests for PDFCalendarViewBase.buildStory.

    buildStory returns a list of platypus objects.

        >>> calendar = ISchoolToolCalendar(Person(title="Mr. Smith"))
        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> view = StubbedBaseView(calendar, request)

        >>> view.configureStyles()
        >>> view.buildStory(date(2005, 7, 8))
        [...
        ...
        ...]

        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(minutes=72), "Some event")
        >>> calendar.addEvent(evt)
        >>> rsrc = Resource(title='Some resource')
        >>> evt.bookResource(rsrc)

        >>> story = view.buildStory(date(2005, 7, 8))
        >>> len(story)
        3
        >>> story[0].text
        'Calendar for Mr. Smith'
        >>> story[1].text
        '2005-07-08'
        >>> story[2]._cellvalues[0][0].text
        '09:10-10:22'
        >>> evt_info = story[2]._cellvalues[0][1]
        >>> len(evt_info)
        2
        >>> evt_info[0].text
        'Some event'
        >>> evt_info[1].text
        'Booked resources: Some resource'

    """


def doctest_PDFCalendarViewBase_buildStory_unicode():
    r"""Tests for PDFCalendarViewBase.buildStory.

    Unicode text is treated properly:

        >>> person = Person(title=u"\u0105 person")
        >>> calendar = ISchoolToolCalendar(person)
        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=5), u"\u0105 event")
        >>> calendar.addEvent(evt)
        >>> rsrc = Resource(title=u"\u0105 resource")
        >>> evt.bookResource(rsrc)

        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> view = StubbedBaseView(calendar, request)
        >>> view.configureStyles()
        >>> story = view.buildStory(date(2005, 7, 8))

        >>> len(story)
        3
        >>> story[0].text
        'Calendar for \xc4\x85 person'
        >>> story[1].text
        '2005-07-08'
        >>> evt_info = story[2]._cellvalues[0][1]
        >>> len(evt_info)
        2
        >>> evt_info[0].text
        '\xc4\x85 event'
        >>> evt_info[1].text
        'Booked resources: \xc4\x85 resource'

    """


def test_buildPageHeader():
    r"""Tests for PDFCalendarViewBase.buildPageHeader.

        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> view = StubbedBaseView(ISchoolToolCalendar(Person()), request)

        >>> view.configureStyles()
        >>> paras = view.buildPageHeader(u'\0105n owner', date(2005, 7, 3))

        >>> len(paras)
        2
        >>> paras[0].text
        'Calendar for \x085n owner'
        >>> paras[1].text
        '2005-07-03'

    """


def test_disabled():
    """Test for PDFCalendarViewBase in disabled state.

        >>> from schooltool.app.browser import pdfcal
        >>> real_pdfcal_disabled = pdfcal.disabled

    Reset the disabled flag to True for the moment:

        >>> pdfcal.disabled = True

    The PDFCalendarViewBase.pdfdata returns a message:

        >>> view = pdfcal.PDFCalendarViewBase(object(), TestRequest())
        >>> view.pdfdata()
        u'PDF support is disabled.  It can be enabled by your administrator.'

    Clean up:

        >>> pdfcal.disabled = real_pdfcal_disabled

    """


def doctest_PDFCalendarViewBase_dayEvents():
    """Event listing tests.

        >>> calendar = ISchoolToolCalendar(Person(title="Mr. Smith"))
        >>> resource = Resource()
        >>> calendar2 = ISchoolToolCalendar(resource)
        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> view = StubbedBaseView(calendar, request)
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

def doctest_PDFCalendarViewBase_dayEvents_timezone():
    """Let's test that dayEvents handles timezones correctly.

    First' let's someone setup the user a timezone:

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> setup.setUpAnnotations()
        >>> app = ISchoolToolApplication(None)
        >>> IApplicationPreferences(app).timezone = "Europe/Vilnius"

    Let's create a calendar and a view:

        >>> calendar = ISchoolToolCalendar(Person(title="Mr. Smith"))
        >>> request = TestRequest()
        >>> view = StubbedBaseView(calendar, request)

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

def doctest_PDFCalendarViewBase_buildEventTable():
    """Tests for buildEventTable.

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> setup.setUpAnnotations()
        >>> app = ISchoolToolApplication(None)
        >>> IApplicationPreferences(app).timezone = "Europe/Vilnius"

        >>> calendar = ISchoolToolCalendar(Person(title="Mr. Smith"))
        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> view = StubbedBaseView(calendar, request)
        >>> view.configureStyles()

    Let's check the representation of an ordinary event:

        >>> from pytz import utc
        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10, tzinfo=utc),
        ...                     timedelta(hours=2), "Some event")
        >>> calendar.addEvent(evt)

        >>> table = view.buildDayTable([evt])
        >>> table._cellvalues[0][0].text
        '12:10-14:10'
        >>> table._cellvalues[0][1][0].text
        'Some event'

    All-day events are identified as such.

        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=2), "evt3", allday=True)
        >>> calendar.addEvent(evt)

        >>> table = view.buildDayTable([evt])
        >>> table._cellvalues[0][0].text
        'all day'

    """


def doctest_PDFCalendarViewBase_eventInfoCell():
    r"""Tests for buildEventTable.

        >>> calendar = ISchoolToolCalendar(Person(title="Mr. Smith"))
        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> view = StubbedBaseView(calendar, request)
        >>> view.configureStyles()

    In case of a simple event, only the title is shown:

        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=2), "Some event")
        >>> calendar.addEvent(evt)
        >>> paragraphs = view.eventInfoCell(evt)
        >>> len(paragraphs)
        1
        >>> paragraphs[0].text
        'Some event'

    If the event is recurrent, it is flagged.  The location, if provided,
    is also indicated.

        >>> from schooltool.calendar.recurrent import DailyRecurrenceRule
        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=2), "Some event",
        ...                     location=u"\u0105 location",
        ...                     recurrence=DailyRecurrenceRule())
        >>> calendar.addEvent(evt)
        >>> paragraphs = view.eventInfoCell(evt)
        >>> len(paragraphs)
        3
        >>> paragraphs[1].text
        'Location: \xc4\x85 location'
        >>> paragraphs[2].text
        '(recurrent)'

    Overlaid events are also recognized.

        >>> calendar2 = ISchoolToolCalendar(Person(title='Mr. X'))
        >>> evt.__parent__ = calendar2
        >>> paragraphs = view.eventInfoCell(evt)
        >>> paragraphs[2].text
        '(recurrent, from the calendar of Mr. X)'

    """


def doctest_DailyPDFCalendarView():
    r"""Tests for DailyPDFCalendarView.

        >>> from schooltool.app.browser.pdfcal import DailyPDFCalendarView
        >>> calendar = ISchoolToolCalendar(Person())
        >>> request = TestRequest(form={'date': '2005-07-01'})
        >>> view = DailyPDFCalendarView(calendar, request)
        >>> view.getCalendars = lambda: [calendar]

    The view's dateTitle method returns the representation of the date shown:

        >>> view.dateTitle(date(2005, 7, 1))
        u'2005-07-01, Friday'

    First, let's make sure that an empty calendar is rendered properly:

        >>> print view.pdfdata()
        %PDF-1.3...
        ...

    In this case buildEventTables should return an empty list:

        >>> view.buildEventTables(date(2005, 7, 1))
        []

    Let's add a few events and make sure that no crashes occur:

        >>> calendar.addEvent(CalendarEvent(datetime(2005, 7, 1, 9, 10),
        ...                                 timedelta(hours=2), "Some event"))
        >>> calendar.addEvent(CalendarEvent(datetime(2005, 7, 1, 9, 50),
        ...                                 timedelta(hours=3), u"An event"))

        >>> print view.pdfdata()
        %PDF-1.3...
        ...

    buildEventTables now returns one table.

        >>> tables = view.buildEventTables(date(2005, 7, 1))
        >>> len(tables)
        1
        >>> tables[0]
        Table(...
        ...

    """


def doctest_WeeklyPDFCalendarView():
    r"""Tests for WeeklyPDFCalendarView.

        >>> from schooltool.app.browser.pdfcal import WeeklyPDFCalendarView
        >>> calendar = ISchoolToolCalendar(Person())
        >>> request = TestRequest(form={'date': '2005-07-01'})
        >>> view = WeeklyPDFCalendarView(calendar, request)
        >>> view.getCalendars = lambda: [calendar]

    The view's dateTitle method returns the representation of the date shown:

        >>> view.dateTitle(date(2005, 7, 1))
        u'Week 26 (2005-06-27 - 2005-07-04), 2005'

    First, let's make sure that an empty calendar is rendered properly:

        >>> print view.pdfdata()
        %PDF-1.3...
        ...

    In this case buildEventTables should return an empty list:

        >>> view.buildEventTables(date(2005, 7, 1))
        []

    Let's add a few events and make sure that no crashes occur:

        >>> calendar.addEvent(CalendarEvent(datetime(2005, 7, 1, 9, 10),
        ...                                 timedelta(hours=2), "Some event"))
        >>> calendar.addEvent(CalendarEvent(datetime(2005, 7, 1, 9, 50),
        ...                                 timedelta(hours=3), u"An event"))

        >>> print view.pdfdata()
        %PDF-1.3...
        ...

    buildEventTables now returns one headline for July 1st and a table.

        >>> tables = view.buildEventTables(date(2005, 7, 1))
        >>> len(tables)
        2
        >>> print tables[0].text
        2005-07-01, Friday
        >>> tables[1]
        Table(...
        ...

    If we add an event on some other day

        >>> calendar.addEvent(CalendarEvent(datetime(2005, 7, 3, 9, 10),
        ...                                 timedelta(hours=2), "Some event"))

    buildEventTables will return two tables with headlines:

        >>> tables = view.buildEventTables(date(2005, 7, 1))
        >>> len(tables)
        4
        >>> print tables[0].text
        2005-07-01, Friday
        >>> tables[1]
        Table(...
        ...
        >>> print tables[2].text
        2005-07-03, Sunday
        >>> tables[3]
        Table(...
        ...

    """


def doctest_MonthlyPDFCalendarView():
    r"""Tests for MonthlyPDFCalendarView.

        >>> from schooltool.app.browser.pdfcal import MonthlyPDFCalendarView
        >>> calendar = ISchoolToolCalendar(Person())
        >>> request = TestRequest(form={'date': '2005-07-01'})
        >>> view = MonthlyPDFCalendarView(calendar, request)
        >>> view.getCalendars = lambda: [calendar]

    The view's dateTitle method returns the representation of the date shown:

        >>> view.dateTitle(date(2005, 7, 1))
        u'July, 2005'

    First, let's make sure that an empty calendar is rendered properly:

        >>> print view.pdfdata()
        %PDF-1.3...
        ...

    In this case buildEventTables should return an empty list:

        >>> view.buildEventTables(date(2005, 7, 1))
        []

    Let's add a few events and make sure that no crashes occur:

        >>> calendar.addEvent(CalendarEvent(datetime(2005, 7, 1, 9, 10),
        ...                                 timedelta(hours=2), "Some event"))
        >>> calendar.addEvent(CalendarEvent(datetime(2005, 7, 1, 9, 50),
        ...                                 timedelta(hours=3), u"An event"))

        >>> print view.pdfdata()
        %PDF-1.3...
        ...

    buildEventTables now returns one headline for July 1st and a table.

        >>> tables = view.buildEventTables(date(2005, 7, 1))
        >>> len(tables)
        2
        >>> print tables[0].text
        2005-07-01, Friday
        >>> tables[1]
        Table(...
        ...

    Let's add some more events.

        >>> calendar.addEvent(CalendarEvent(datetime(2005, 7, 31, 9, 10),
        ...                                 timedelta(hours=2), "Some event"))

    And corner cases, which should not appear in the report:

        >>> calendar.addEvent(CalendarEvent(datetime(2005, 6, 30, 9, 10),
        ...                                 timedelta(hours=2), "No event"))
        >>> calendar.addEvent(CalendarEvent(datetime(2005, 8, 1, 9, 10),
        ...                                 timedelta(hours=2), "No event"))

    buildEventTables will return two tables with headlines.  The events
    that do not fall on the current month will be omitted.

        >>> tables = view.buildEventTables(date(2005, 7, 1))
        >>> len(tables)
        4
        >>> print tables[0].text
        2005-07-01, Friday
        >>> tables[1]
        Table(...
        ...
        >>> print tables[2].text
        2005-07-31, Sunday
        >>> tables[3]
        Table(...
        ...

    """


def test_getCalendars(self):
    """Test for PDFCalendarViewBase.getCalendars().

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
        >>> view = PDFCalendarViewBase(Calendar(None), TestRequest())

    Now, if we call the method, the output of our stub will be returned:

        >>> view.getCalendars()
        ['some calendar', 'another calendar']

    """


def test_suite():
    from schooltool.app.tests.test_pdf import tryToSetUpReportLab
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite('schooltool.app.browser.pdfcal'))
    success = tryToSetUpReportLab()
    if success:
        docsuite = doctest.DocTestSuite(setUp=pdfSetUp, tearDown=pdfTearDown,
                                        optionflags=doctest.ELLIPSIS)
        suite.addTest(docsuite)
    else:
        print >> sys.stderr, ("reportlab or TrueType fonts not found;"
                              " PDF generator tests skipped")

    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
