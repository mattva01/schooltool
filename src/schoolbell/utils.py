"""
Utility functions for SchoolBell.

These include various date manipulation routines.
"""

import calendar
from datetime import datetime, date, timedelta, tzinfo


def prev_month(date):
    """Calculate the first day of the previous month for a given date.

        >>> prev_month(date(2004, 8, 1))
        datetime.date(2004, 7, 1)
        >>> prev_month(date(2004, 8, 31))
        datetime.date(2004, 7, 1)
        >>> prev_month(date(2004, 12, 15))
        datetime.date(2004, 11, 1)
        >>> prev_month(date(2005, 1, 28))
        datetime.date(2004, 12, 1)

    """
    return (date.replace(day=1) - timedelta(1)).replace(day=1)


def next_month(date):
    """Calculate the first day of the next month for a given date.

        >>> next_month(date(2004, 8, 1))
        datetime.date(2004, 9, 1)
        >>> next_month(date(2004, 8, 31))
        datetime.date(2004, 9, 1)
        >>> next_month(date(2004, 12, 15))
        datetime.date(2005, 1, 1)
        >>> next_month(date(2004, 2, 28))
        datetime.date(2004, 3, 1)
        >>> next_month(date(2004, 2, 29))
        datetime.date(2004, 3, 1)
        >>> next_month(date(2005, 2, 28))
        datetime.date(2005, 3, 1)

    """
    return (date.replace(day=28) + timedelta(7)).replace(day=1)


def week_start(date, first_day_of_week=0):
    """Calculate the first day of the week for a given date.

    Assuming that week starts on Mondays:

        >>> week_start(date(2004, 8, 19))
        datetime.date(2004, 8, 16)
        >>> week_start(date(2004, 8, 15))
        datetime.date(2004, 8, 9)
        >>> week_start(date(2004, 8, 14))
        datetime.date(2004, 8, 9)
        >>> week_start(date(2004, 8, 21))
        datetime.date(2004, 8, 16)
        >>> week_start(date(2004, 8, 22))
        datetime.date(2004, 8, 16)
        >>> week_start(date(2004, 8, 23))
        datetime.date(2004, 8, 23)

    Assuming that week starts on Sundays:

        >>> import calendar
        >>> week_start(date(2004, 8, 19), calendar.SUNDAY)
        datetime.date(2004, 8, 15)
        >>> week_start(date(2004, 8, 15), calendar.SUNDAY)
        datetime.date(2004, 8, 15)
        >>> week_start(date(2004, 8, 14), calendar.SUNDAY)
        datetime.date(2004, 8, 8)
        >>> week_start(date(2004, 8, 21), calendar.SUNDAY)
        datetime.date(2004, 8, 15)
        >>> week_start(date(2004, 8, 22), calendar.SUNDAY)
        datetime.date(2004, 8, 22)
        >>> week_start(date(2004, 8, 23), calendar.SUNDAY)
        datetime.date(2004, 8, 22)

    """
    assert 0 <= first_day_of_week < 7
    delta = date.weekday() - first_day_of_week
    if delta < 0:
        delta += 7
    return date - timedelta(delta)


def weeknum_bounds(year, weeknum):
    """Calculate the inclusive date bounds for a (year, weeknum) tuple.

    Week numbers are as defined in ISO 8601 and returned by
    datetime.date.isocalendar().

        >>> weeknum_bounds(2003, 52)
        (datetime.date(2003, 12, 22), datetime.date(2003, 12, 28))
        >>> weeknum_bounds(2004, 1)
        (datetime.date(2003, 12, 29), datetime.date(2004, 1, 4))
        >>> weeknum_bounds(2004, 2)
        (datetime.date(2004, 1, 5), datetime.date(2004, 1, 11))

    """
    # The first week of a year is at least 4 days long, so January 4th
    # is in the first week.
    firstweek = week_start(date(year, 1, 4), calendar.MONDAY)
    # move forward to the right week number
    weekstart = firstweek + timedelta(weeks=weeknum-1)
    weekend = weekstart + timedelta(days=6)
    return (weekstart, weekend)


def check_weeknum(year, weeknum):
    """Check to see whether a (year, weeknum) tuple refers to a real
    ISO week number.

        >>> check_weeknum(2004, 1)
        True
        >>> check_weeknum(2004, 53)
        True
        >>> check_weeknum(2004, 0)
        False
        >>> check_weeknum(2004, 54)
        False
        >>> check_weeknum(2003, 52)
        True
        >>> check_weeknum(2003, 53)
        False

    """
    weekstart, weekend = weeknum_bounds(year, weeknum)
    isoyear, isoweek, isoday = weekstart.isocalendar()
    return (year, weeknum) == (isoyear, isoweek)
