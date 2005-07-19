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

import os
import sys
import unittest
from datetime import datetime, date, timedelta
from zope.testing import doctest
from zope.publisher.browser import TestRequest
from zope.app.tests import setup, ztapi
from zope.app.publisher.browser import BrowserView
from schoolbell.app.app import Person, Resource
from schoolbell.app.cal import CalendarEvent
from schoolbell.app.browser.pdfcal import PDFCalendarViewBase
from schoolbell.app.browser.pdfcal import setUpMSTTCoreFonts
from schoolbell import SchoolBellMessageID as _


class StubbedBaseView(PDFCalendarViewBase):
    """A subclass of PDFCalendarViewBase for use in tests."""

    title = _("Calendar for %s")

    def getCalendars(self):
        return [self.context]

    def buildEventTables(self, date):
        events = self.dayEvents(date)
        return events and [self.buildDayTable(events)] or []

    def dateTitle(self, date):
        return date.isoformat()


def doctest_PDFCalendarViewBase():
    """Tests for PDFCalendarViewBase.

        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> person = Person(title="Mr. Smith")
        >>> view = StubbedBaseView(person.calendar, request)

        >>> print view.pdfdata()
        %PDF-1.3...
        ...

        >>> request.response.getHeader('Content-Type')
        'application/pdf'
        >>> request.response.getHeader('Accept-Ranges')
        'bytes'

    If we do not specify a date, today is taken by default:

        >>> request = TestRequest()
        >>> view = StubbedBaseView(person.calendar, request)

        >>> print view.pdfdata()
        %PDF-1.3...
        ...

    """


def doctest_PDFCalendarViewBase_buildStory():
    r"""Tests for PDFCalendarViewBase.buildStory.

    buildStory returns a list of platypus objects.

        >>> calendar = Person(title="Mr. Smith").calendar
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
        4
        >>> story[1].text
        'Calendar for Mr. Smith'
        >>> story[2].text
        '2005-07-08'
        >>> story[3]._cellvalues[0][0].text
        '09:10-10:22'
        >>> evt_info = story[3]._cellvalues[0][1]
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
        >>> calendar = person.calendar
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
        4
        >>> story[1].text
        'Calendar for \xc4\x85 person'
        >>> story[2].text
        '2005-07-08'
        >>> evt_info = story[3]._cellvalues[0][1]
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
        >>> view = StubbedBaseView(Person().calendar, request)

        >>> view.configureStyles()
        >>> paras = view.buildPageHeader(u'\0105n owner', date(2005, 7, 3))

        >>> len(paras)
        3
        >>> paras[0]
        <...Image...>
        >>> paras[0].hAlign
        'LEFT'
        >>> paras[1].text
        'Calendar for \x085n owner'
        >>> paras[2].text
        '2005-07-03'

    """


def test_disabled():
    """Test for PDFCalendarViewBase in disabled state.

        >>> from schoolbell.app.browser import pdfcal

    The `disabled` flag is set to True by default, but we have run the
    initialization routine already, so it has been set to False.  Reset it
    for the moment:

        >>> pdfcal.disabled = True

    The PDFCalendarViewBase.pdfdata returns a message:

        >>> view = pdfcal.PDFCalendarViewBase(object(), TestRequest())
        >>> view.pdfdata()
        'PDF support is disabled.  It can be enabled by your administrator.'

    Clean up:

        >>> pdfcal.disabled = False

    """


def doctest_PDFCalendarViewBase_dayEvents():
    """Event listing tests.

        >>> calendar = Person(title="Mr. Smith").calendar
        >>> calendar2 = Person().calendar
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

        >>> evt3 = CalendarEvent(datetime(2005, 7, 8, 9, 3),
        ...                      timedelta(hours=2), "evt3")
        >>> calendar2.addEvent(evt3)

        >>> result = view.dayEvents(date(2005, 7, 8))
        >>> [evt.title for evt in result]
        ['evt3', 'evt', 'evt2']

    All-day events always appear in front:

        >>> ad_evt = CalendarEvent(datetime(2005, 7, 8, 20, 3),
        ...                        timedelta(hours=2), "allday", allday=True)
        >>> calendar.addEvent(ad_evt)

        >>> result = view.dayEvents(date(2005, 7, 8))
        >>> [evt.title for evt in result]
        ['allday', 'evt3', 'evt', 'evt2']

    """


def doctest_PDFCalendarViewBase_buildEventTable():
    """Tests for buildEventTable.

        >>> calendar = Person(title="Mr. Smith").calendar
        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> view = StubbedBaseView(calendar, request)
        >>> view.configureStyles()

    Let's check the representation of an ordinary event:

        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=2), "Some event")
        >>> table = view.buildDayTable([evt])
        >>> table._cellvalues[0][0].text
        '09:10-11:10'
        >>> table._cellvalues[0][1][0].text
        'Some event'

    All-day events are identified as such.

        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=2), "evt3", allday=True)
        >>> table = view.buildDayTable([evt])
        >>> table._cellvalues[0][0].text
        'all day'

    """


def doctest_PDFCalendarViewBase_eventInfoCell():
    r"""Tests for buildEventTable.

        >>> calendar = Person(title="Mr. Smith").calendar
        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> view = StubbedBaseView(calendar, request)
        >>> view.configureStyles()

    In case of a simple event, only the title is shown:

        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=2), "Some event")
        >>> paragraphs = view.eventInfoCell(evt)
        >>> len(paragraphs)
        1
        >>> paragraphs[0].text
        'Some event'

    If the event is recurrent, it is flagged.  The location, if provided,
    is also indicated:

        >>> from schoolbell.calendar.recurrent import DailyRecurrenceRule
        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=2), "Some event",
        ...                     location=u"\u0105 location",
        ...                     recurrence=DailyRecurrenceRule())
        >>> paragraphs = view.eventInfoCell(evt)
        >>> len(paragraphs)
        3
        >>> paragraphs[1].text
        'Location: \xc4\x85 location'
        >>> paragraphs[2].text
        '(recurrent)'

    """


def doctest_DailyPDFCalendarView():
    r"""Tests for DailyPDFCalendarView.

        >>> from schoolbell.app.browser.pdfcal import DailyPDFCalendarView
        >>> calendar = Person().calendar
        >>> request = TestRequest(form={'date': '2005-07-01'})
        >>> view = DailyPDFCalendarView(calendar, request)
        >>> view.getCalendars = lambda: [calendar]

    The view's dateTitle method returns the representation of the date shown:

        >>> view.dateTitle(date(2005, 7, 1))
        '2005-07-01, Friday'

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

        >>> from schoolbell.app.browser.pdfcal import WeeklyPDFCalendarView
        >>> calendar = Person().calendar
        >>> request = TestRequest(form={'date': '2005-07-01'})
        >>> view = WeeklyPDFCalendarView(calendar, request)
        >>> view.getCalendars = lambda: [calendar]

    The view's dateTitle method returns the representation of the date shown:

        >>> view.dateTitle(date(2005, 7, 1))
        'Week 26 (2005-06-27 - 2005-07-04), 2005'

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
        >>> tables[0].text
        '2005-07-01, Friday'
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
        >>> tables[0].text
        '2005-07-01, Friday'
        >>> tables[1]
        Table(...
        ...
        >>> tables[2].text
        '2005-07-03, Sunday'
        >>> tables[3]
        Table(...
        ...

    """


def doctest_MonthlyPDFCalendarView():
    r"""Tests for MonthlyPDFCalendarView.

        >>> from schoolbell.app.browser.pdfcal import MonthlyPDFCalendarView
        >>> calendar = Person().calendar
        >>> request = TestRequest(form={'date': '2005-07-01'})
        >>> view = MonthlyPDFCalendarView(calendar, request)
        >>> view.getCalendars = lambda: [calendar]

    The view's dateTitle method returns the representation of the date shown:

        >>> view.dateTitle(date(2005, 7, 1))
        'July, 2005'

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
        >>> tables[0].text
        '2005-07-01, Friday'
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
        >>> tables[0].text
        '2005-07-01, Friday'
        >>> tables[1]
        Table(...
        ...
        >>> tables[2].text
        '2005-07-31, Sunday'
        >>> tables[3]
        Table(...
        ...

    """


def doctest_setUpMSTTCoreFonts():
    r"""TrueType font setup tests.

        >>> from schoolbell.app.browser import pdfcal

    The actual setup has been done at import-time by the test_suite function.
    We only test the results here.

    Let's check that the TrueType fonts have been configured:

        >>> from reportlab.pdfbase import pdfmetrics

        >>> pdfmetrics.getFont('Times_New_Roman')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>
        >>> pdfmetrics.getFont('Times_New_Roman_Bold')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>
        >>> pdfmetrics.getFont('Times_New_Roman_Italic')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>
        >>> pdfmetrics.getFont('Times_New_Roman_Bold_Italic')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>

        >>> pdfmetrics.getFont('Arial_Normal')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>
        >>> pdfmetrics.getFont('Arial_Bold')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>
        >>> pdfmetrics.getFont('Arial_Italic')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>
        >>> pdfmetrics.getFont('Arial_Bold_Italic')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>

    For our Serif font (normal paragraphs), the bold/italic mappings
    are registered:

        >>> from reportlab.lib.fonts import tt2ps, ps2tt

        >>> tt2ps('Times_New_Roman', 0, 0)
        'Times_New_Roman'
        >>> tt2ps('Times_New_Roman', 1, 0)
        'Times_New_Roman_Bold'
        >>> tt2ps('Times_New_Roman', 0, 1)
        'Times_New_Roman_Italic'
        >>> tt2ps('Times_New_Roman', 1, 1)
        'Times_New_Roman_Bold_Italic'

        >>> ps2tt('Times_New_Roman')
        ('times_new_roman', 0, 0)
        >>> ps2tt('Times_New_Roman_Bold')
        ('times_new_roman', 1, 0)
        >>> ps2tt('Times_New_Roman_Italic')
        ('times_new_roman', 0, 1)
        >>> ps2tt('Times_New_Roman_Bold_Italic')
        ('times_new_roman', 1, 1)

        >>> tt2ps('Arial_Normal', 0, 0)
        'Arial_Normal'
        >>> tt2ps('Arial_Normal', 1, 0)
        'Arial_Bold'
        >>> tt2ps('Arial_Normal', 0, 1)
        'Arial_Italic'
        >>> tt2ps('Arial_Normal', 1, 1)
        'Arial_Bold_Italic'

        >>> ps2tt('Arial_Normal')
        ('arial_normal', 0, 0)
        >>> ps2tt('Arial_Bold')
        ('arial_normal', 1, 0)
        >>> ps2tt('Arial_Italic')
        ('arial_normal', 0, 1)
        >>> ps2tt('Arial_Bold_Italic')
        ('arial_normal', 1, 1)

        >>> pdfcal.SANS
        'Arial_Normal'
        >>> pdfcal.SANS_OBLIQUE
        'Arial_Italic'
        >>> pdfcal.SANS_BOLD
        'Arial_Bold'
        >>> pdfcal.SERIF
        'Times_New_Roman'

    If the fonts can not be found, setUpMSTTCoreFonts() will
    raise an exception:

        >>> import reportlab.rl_config
        >>> real_path = reportlab.rl_config.TTFSearchPath[-1]
        >>> del reportlab.rl_config.TTFSearchPath[-1]

        >>> pdfcal.setUpMSTTCoreFonts('/definitely/nonexistent')
        Traceback (most recent call last):
          ...
        TTFError: Can't open file "....ttf"

    Clean up:

        >>> reportlab.rl_config.TTFSearchPath.append(real_path)

    """


def test_getCalendars(self):
    """Test for PDFCalendarViewBase.getCalendars().

        >>> setup.placelessSetUp()

    getCalendars() only delegates the task to a calendar list view.  We
    will provide a stub view to test the method.

        >>> class CalendarListViewStub(BrowserView):
        ...     def getCalendars(self):
        ...         return [('some calendar', 'color1', 'color2'),
        ...                 ('another calendar', 'color1', 'color2')]
        >>> from schoolbell.app.interfaces import ISchoolBellCalendar
        >>> ztapi.browserView(ISchoolBellCalendar, 'calendar_list',
        ...                   CalendarListViewStub)

        >>> from schoolbell.app.cal import Calendar
        >>> view = PDFCalendarViewBase(Calendar(), TestRequest())

    Now, if we call the method, the output of our stub will be returned:

        >>> view.getCalendars()
        ['some calendar', 'another calendar']

    We're done:

        >>> setup.placelessTearDown()

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite('schoolbell.app.browser.pdfcal'))

    try:
        import reportlab
    except ImportError:
        # We don't have reportlab, so we can't get anywhere.
        print >> sys.stderr, "reportlab not found; PDF generator tests skipped"
    else:
        # We have reportlab, but may not have TrueType fonts.

        # Dumb heuristic to try and find the TrueType fonts.
        font_dirs = ['/usr/share/fonts/truetype/msttcorefonts',
                     r'C:\WINDOWS\Fonts'] # TODO: actually test this on Windows
        for font_dir in font_dirs:
            if os.path.exists(os.path.join(font_dir, 'arial.ttf')):
                setUpMSTTCoreFonts(font_dir)
                docsuite = doctest.DocTestSuite(optionflags=doctest.ELLIPSIS)
                suite.addTest(docsuite)
                break
        else:
            # TODO: suite.addTest(some_tests)
            print >> sys.stderr, ("TrueType fonts not found;"
                                  " skipping some PDF generator tests")

    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
