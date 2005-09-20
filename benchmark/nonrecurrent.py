#!/usr/bin/python
"""
Benchmark for calendar views when there are many nonrecurrent events.
"""

import random
from datetime import datetime, timedelta

from benchmark import *

import transaction
from zope.app.testing.functional import FunctionalTestSetup
from zope.app.testing.functional import HTTPCaller
from schooltool.app.browser.ftests.test_all import find_ftesting_zcml
from schooltool.app.cal import CalendarEvent
from schooltool.person.person import Person
from schooltool.group.group import Group
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
    create_random_events(app)
    transaction.commit()

    r = http(r"""GET /frogpond/persons HTTP/1.1
Authorization: Basic mgr:mgrpw
""")
    assert r.getStatus() == 200


def create_random_events(app, count=5000, seed=42):
    """Create a user with many nonrecurrent events in his calendar.

    The user's username will be 'manager', and his calendar will have
    a given number of random nonrecurring events in the year 2005.
    """
    rng = random.Random(seed)
    person = Person('manager', 'Manager')
    app['persons']['manager'] = person

    year = 2005
    months = range(1, 13)
    days = range(1, 29)
    hours = range(24)
    minutes = range(60)
    durations = range(15, 180)

    for i in range(count):
        dtstart = datetime(2005, rng.choice(months), rng.choice(days),
                           rng.choice(hours), rng.choice(minutes))
        duration = timedelta(minutes=rng.choice(durations))
        event = CalendarEvent(dtstart, duration, 'Lorem ipsum %d' % i,
                              recurrence=None, location='Booha',
                              allday=False, description='Some words.')
        ISchoolToolCalendar(person).addEvent(event)


def daily_view():
    """Benchmark the DailyCalendarView."""
    r = http(r"""GET /frogpond/persons/manager/calendar/2005-05-06 HTTP/1.1
Authorization: Basic mgr:mgrpw
""")
    assert r.getStatus() == 200


def weekly_view():
    """Benchmark the WeeklyCalendarView."""
    r = http(r"""GET /frogpond/persons/manager/calendar/2005-w20 HTTP/1.1
Authorization: Basic mgr:mgrpw
""")
    assert r.getStatus() == 200


def monthly_view():
    """Benchmark the MonthlyCalendarView."""
    r = http(r"""GET /frogpond/persons/manager/calendar/2005-06 HTTP/1.1
Authorization: Basic mgr:mgrpw
""")
    assert r.getStatus() == 200


def yearly_view():
    """Benchmark the YearlyCalendarView."""
    r = http(r"""GET /frogpond/persons/manager/calendar/2005 HTTP/1.1
Authorization: Basic mgr:mgrpw
""")
    assert r.getStatus() == 200


def main():
    print "ZCML took %.3f seconds." % measure(load_ftesting_zcml)
    print "Setup took %.3f seconds." % measure(setup_benchmark)
    benchmark("Daily calendar view with many simple events", daily_view)
    benchmark("Weekly calendar view with many simple events", weekly_view)
    benchmark("Monthly calendar view with many simple events", monthly_view)
    benchmark("Yearly calendar view with many simple events", yearly_view)


if __name__ == '__main__':
    main()
