#!/usr/bin/python
"""
Benchmark the daily calendar view with some long lasting recurrent events.
"""

from datetime import datetime, timedelta

from benchmark import *

import transaction
from schooltool.app.cal import CalendarEvent
from schooltool.person.person import Person
from schooltool.group.group import Group
from schooltool.calendar.recurrent import DailyRecurrenceRule
from schooltool.calendar.recurrent import WeeklyRecurrenceRule
from schooltool.calendar.recurrent import MonthlyRecurrenceRule
from schooltool.calendar.recurrent import YearlyRecurrenceRule
from schooltool.app.interfaces import ISchoolToolCalendar


def setup_benchmark():
    setup = load_ftesting_zcml()
    r = http("""POST /@@contents.html HTTP/1.1
Authorization: Basic mgr:mgrpw
Content-Length: 81
Content-Type: application/x-www-form-urlencoded

type_name=BrowserAdd__schooltool.app.app.SchoolToolApplication&new_value=frogpond""")
    assert r.getStatus() == 303

    app = setup.getRootFolder()['frogpond']
    create_user_and_recurrent_events(app)
    transaction.commit()

    r = http(r"""GET /frogpond/persons HTTP/1.1
Authorization: Basic mgr:mgrpw
""")
    assert r.getStatus() == 200


def create_user_and_recurrent_events(app):
    """Create a user with some recurrent events in his calendar.

    The user's username will be 'manager', and his calendar will have
    exactly four events, recurring daily, weekly, monthly, and yearly
    respectively.  All these events start on the same day.
    """
    person = Person('manager', 'Manager')
    app['persons']['manager'] = person
    calendar = ISchoolToolCalendar(person)

    recurrence = DailyRecurrenceRule()
    daily_event = CalendarEvent(datetime(2005, 1, 1, 10, 0),
                                timedelta(60),
                                'Daily Event',
                                recurrence=recurrence)
    calendar.addEvent(daily_event)

    recurrence = WeeklyRecurrenceRule(weekdays=(0, 1, 2, 3, 4, 5, 6))
    weekly_event = CalendarEvent(datetime(2005, 1, 1, 11, 0),
                                timedelta(60),
                                'Weekly event',
                                recurrence=recurrence)
    calendar.addEvent(weekly_event)

    recurrence = MonthlyRecurrenceRule()
    monthly_event = CalendarEvent(datetime(2005, 1, 1, 12, 0),
                                  timedelta(60),
                                  'Monthly event',
                                  recurrence=recurrence)
    calendar.addEvent(monthly_event)

    recurrence = YearlyRecurrenceRule()
    yearly_event = CalendarEvent(datetime(2005, 1, 1, 13, 0),
                                 timedelta(60),
                                 'Yearly event',
                                 recurrence=recurrence)
    calendar.addEvent(yearly_event)


def daily_view_start_date():
    """Render the DailyCalendarView on the starting date."""
    r = http(r"""GET /frogpond/persons/manager/calendar/2005-01-01 HTTP/1.1
Authorization: Basic mgr:mgrpw
""")
    assert r.getStatus() == 200


def daily_view_in_a_year():
    """Render the DailyCalendarView a year after the starting date."""
    r = http(r"""GET /frogpond/persons/manager/calendar/2006-01-01 HTTP/1.1
Authorization: Basic mgr:mgrpw
""")
    assert r.getStatus() == 200


def daily_view_in_ten_years():
    """Render the DailyCalendarView ten years after the starting date."""
    r = http(r"""GET /frogpond/persons/manager/calendar/2015-01-01 HTTP/1.1
Authorization: Basic mgr:mgrpw
""")
    assert r.getStatus() == 200


def main():
    print "ZCML took %.3f seconds." % measure(load_ftesting_zcml)
    print "Setup took %.3f seconds." % measure(setup_benchmark)
    benchmark("Daily calendar view on the start date.",
              daily_view_start_date)
    benchmark("Daily calendar view a year after the start date.",
              daily_view_in_a_year)
    benchmark("Daily calendar view ten years after the start date.",
              daily_view_in_ten_years)


if __name__ == '__main__':
    main()
