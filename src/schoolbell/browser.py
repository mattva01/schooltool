r"""
Browser views for schoolbell.

iCalendar views
---------------

CalendarICalendarView can export calendars in iCalendar format

    >>> from datetime import datetime, timedelta
    >>> from schoolbell.simple import ImmutableCalendar, SimpleCalendarEvent
    >>> event = SimpleCalendarEvent(datetime(2004, 12, 16, 11, 46, 16),
    ...                             timedelta(hours=1), "doctests",
    ...                             location=u"Matar\u00f3",
    ...                             unique_id="12345678-5432@example.com")
    >>> calendar = ImmutableCalendar([event])

    >>> from zope.publisher.browser import TestRequest
    >>> view = CalendarICalendarView()
    >>> view.context = calendar
    >>> view.request = TestRequest()
    >>> output = view.show()

    >>> lines = output.splitlines(True)
    >>> from pprint import pprint
    >>> pprint(lines)
    ['BEGIN:VCALENDAR\r\n',
     'VERSION:2.0\r\n',
     'PRODID:-//SchoolTool.org/NONSGML SchoolBell//EN\r\n',
     'BEGIN:VEVENT\r\n',
     'UID:12345678-5432@example.com\r\n',
     'SUMMARY:doctests\r\n',
     'LOCATION:Matar\xc3\xb3\r\n',
     'DTSTART:20041216T114616\r\n',
     'DURATION:PT1H\r\n',
     'DTSTAMP:...\r\n',
     'END:VEVENT\r\n',
     'END:VCALENDAR']

XXX: Should the last line also end in '\r\n'?  Go read RFC 2445 and experiment
with calendaring clients.

Register the iCalendar read view in ZCML as

    <browser:page
        for="schoolbell.interfaces.ICalendar"
        name="calendar.ics"
        permission="zope.Public"
        class="schoolbell.browser.CalendarICalendarView"
        attribute="show"
        />

"""

from schoolbell.icalendar import convert_calendar_to_ical

__metaclass__ = type


class CalendarICalendarView:
    """RFC 2445 (ICalendar) view for calendars."""

    def show(self):
        data = "\r\n".join(convert_calendar_to_ical(self.context))
        request = self.request
        if request is not None:
            request.response.setHeader('Content-Type',
                                       'text/calendar; charset=UTF-8')
            request.response.setHeader('Content-Length', len(data))

        return data

