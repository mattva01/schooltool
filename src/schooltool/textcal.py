#!/usr/bin/env python2.3
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
A text calendar script to demonstrate the calendaring functionality.

$Id$
"""
import datetime
import calendar
import sys
from sets import Set
from cal import Timetable, TimetableDay, TimetableActivity
from cal import SchooldayModel, SchooldayPeriod, SchooldayTemplate
from cal import SequentialDaysTimetableModel, WeeklyTimetableModel


class TomHoffmanConfig:
    """Hard-coded timetable configuration for a model Tom Hoffman told of."""

    days = ("1A", "2E", "3A", "4E")

    timetable = { "1A" : { "P1": "Science",
                           "P2": "Mathematics",
                           "P3": "Beginning Spanish",
                           "P4": "English"},
                  "2E" : { "P1": "English",
                           "P2": "Social studies",
                           "P3": "Science",
                           "P4": "Music"},
                  "3A" : { "P1": "Science",
                           "P2": "Mathematics",
                           "P3": "Beginning Spanish",
                           "P4": "Social studies"},
                  "4E" : { "P1": "English",
                           "P2": "Social studies",
                           "P3": "Mathematics",
                           "P4": "Music"}}

    long_day = {"title": "Long day",
                "P1": (datetime.time(9, 0), datetime.timedelta(hours=1)),
                "P2": (datetime.time(10, 15), datetime.timedelta(hours=1)),
                "P3": (datetime.time(11, 30), datetime.timedelta(hours=1)),
                "P4": (datetime.time(12, 45), datetime.timedelta(hours=1))}

    short_day = {"title": "Short day",
                "P1": (datetime.time(9, 0), datetime.timedelta(hours=1)),
                 "P2": (datetime.time(10, 5), datetime.timedelta(hours=1)),
                 "P3": (datetime.time(11, 10), datetime.timedelta(hours=1)),
                 "P4": (datetime.time(12, 15), datetime.timedelta(hours=1))}

    day_templates = {"default": long_day,
                     calendar.WEDNESDAY: short_day}

    schooldays = {'first': datetime.date(2003, 9, 1),
                  'last': datetime.date(2003, 12, 19),
                  # Weekdays that are schooldays
                  'weekdays': (calendar.MONDAY, calendar.TUESDAY,
                               calendar.WEDNESDAY, calendar.THURSDAY,
                               calendar.FRIDAY),
                  # Exceptions -- holidays
                  'holidays': (datetime.date(2003, 10, 13), # Columbus day
                               datetime.date(2003, 11, 27), # Thanksgiving day
                               datetime.date(2003, 11, 11), # Veteran's day
                               )
                  }
    timetable_model_factory = SequentialDaysTimetableModel


class LithuanianConfig:
    """Hard-coded timetable configuration for a model used in
    Lithuanian schools.
    """

    # Names of the timetable weekdays, starting from Monday.
    days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")

    timetable = { "Monday" : { "1": "Science",
                               "2": "Mathematics",
                               "3": "Beginning Spanish",
                               "4": "English",
                               "5": "Physics"},
                  "Tuesday" : { "1": "English",
                                "2": "History",
                                "3": "Chemistry",
                                "4": "Music",
                                "5": "History"},
                  "Wednesday" : { "1": "Science",
                                  "2": "Mathematics",
                                  "3": "Russian",
                                  "4": "History"},
                  "Thursday" : { "0": "Ethics",
                                 "1": "English",
                                 "2": "Biology",
                                 "3": "Mathematics",
                                 "4": "Music"},
                  "Friday" : { "1": "English",
                               "2": "Social studies",
                               "3": "Mathematics",
                               "4": "Lithuanian",
                               "5": "Lithuanian",}}

    normal_day = {"title": "Normal day",
                  "0": (datetime.time(8, 10), datetime.timedelta(minutes=45)),
                  "1": (datetime.time(9, 0), datetime.timedelta(minutes=45)),
                  "2": (datetime.time(9, 50), datetime.timedelta(minutes=45)),
                  "3": (datetime.time(10, 45), datetime.timedelta(minutes=45)),
                  "4": (datetime.time(11, 50), datetime.timedelta(minutes=45)),
                  "5": (datetime.time(12, 50), datetime.timedelta(minutes=45)),
                  "6": (datetime.time(13, 45), datetime.timedelta(minutes=45)),
                  "7": (datetime.time(14, 35), datetime.timedelta(minutes=45)),
                  }

    day_templates = {"default": normal_day}

    schooldays = {'first': datetime.date(2003, 9, 1),
                  'last': datetime.date(2003, 11, 30),
                  # Weekdays that are schooldays
                  'weekdays': (calendar.MONDAY, calendar.TUESDAY,
                               calendar.WEDNESDAY, calendar.THURSDAY,
                               calendar.FRIDAY),
                  # Exceptions -- holidays
                  'holidays': (datetime.date(2003, 11, 1), # All saints
                               )
                  }
    timetable_model_factory = WeeklyTimetableModel


def createSchooldayModel(config):
    data = config.schooldays
    sc = SchooldayModel(data['first'], data['last'])
    sc.addWeekdays(*data['weekdays'])
    for holiday in data['holidays']:
        if sc.isSchoolday(holiday):
            sc.remove(holiday)
    return sc


def createTimetable(config):
    days = config.days
    tt_data = config.timetable
    tt = Timetable(days)
    for day in tt_data:
        ttday = TimetableDay(tt_data[day].keys())
        tt[day] = ttday
        for period in tt_data[day]:
            ttday[period] = TimetableActivity(tt_data[day][period])
    return tt


def createTimetableModel(config):
    dt_data = config.day_templates
    dtemplates = {}
    for weekday in dt_data:
        dt = SchooldayTemplate()
        title = dt_data[weekday]["title"]
        dt.title = title
        del dt_data[weekday]["title"]
        for title, (start, duration) in dt_data[weekday].items():
            dt.add(SchooldayPeriod(title, start, duration))
        if weekday == "default":
            weekday = None
        dtemplates[weekday] = dt
    return config.timetable_model_factory(config.days, dtemplates)


class PrintPacker:
    """Basically, this class formats text printed with printLine()
    method into n columns.
    """

    def __init__(self, cols=3, width=79):
        self.cols = cols
        self.width = width
        self.columns = []
        self.column = []

    def printLine(self, line):
        """Add a line to the current column"""
        self.column.append(line)

    def formFeed(self):
        """Signals that a column is completed.

        If enough columns are completed, they are printed.
        """
        self.columns.append(self.column)
        self.column = []
        if len(self.columns) == self.cols:
            self.output()
            print

    def output(self):
        """Print the data that is stored"""
        if self.column:
            self.columns.append(self.column)
            self.column = []
        if self.columns:
            rows = reduce(max, [len(x) for x in self.columns])
            self.columns += [] * (self.cols - len(self.columns))

            for col in self.columns:
                col += [''] * (rows - len(col))

            for row in zip(*self.columns):
                print "".join([s.ljust(self.width/self.cols) for s in row])
        self.columns = []


def printCalendar(cal, model):
    gen = model._dayGenerator()
    pp = PrintPacker(3, 79)
    for date in cal.daterange:
        daycal = cal.byDate(date)
        events = list(daycal)
        if events:
            day = model.schooldayStrategy(date, gen)
            s = "%s %s" % (day[:3], date.strftime('%A %Y-%m-%d'))
            pp.printLine(s)
            pp.printLine("=" * len(s))
            L = [(e.dtstart, e) for e in events]
            L.sort()
            for dt, event in L:
                pp.printLine("%s %s" % (dt.strftime("%H:%M"), event.title))
            pp.formFeed()
    pp.output()


def printSummaryLegend(model):
    print
    print "Legend"
    print "------"
    print "Timetable days:\n   ", ", ".join(model.timetableDayIds)
    print "Day templates:"
    templ = list(Set(model.dayTemplates.values()))
    templ_names = [(t.title, t) for t in templ]
    templ_names.sort()
    for day, template in templ_names:
        print "    %s: %s" % (day[0], day)
    print


def printCalendarSummary(cal, model):
    gen = model._dayGenerator()
    pp = PrintPacker(2)
    week_nr = ['']
    week_type = ['']
    month = None
    for date in cal.daterange:
        daycal = cal.byDate(date)
        events = list(daycal)
        if events:
            day = model.schooldayStrategy(date, gen).title()[:2]
            length = model._getTemplateForDay(date).title[0]
        else:
            day = "--"
            length = "-"

        if month is not None and month < date.month:
            if date.weekday():
                week_type += [' ' * 4] * (7 - date.weekday()) + ['']
                week_nr += [' ' * 4] * (7 - date.weekday()) + ['']

                pp.printLine("|".join(week_nr))
                pp.printLine("|".join(week_type))
                pp.printLine("+----+----+----+----+----+----+----+")
            pp.formFeed()
            week_type = [''] + [' ' * 4] * date.weekday()
            week_nr = [''] + [' ' * 4] * date.weekday()

        week_nr.append(date.strftime('%d').center(4))
        week_type.append("%s %s" % (day, length))

        if month is None or month < date.month:
            m = date.strftime("%B %Y")
            pp.printLine(m.center(35))
            # pp.printLine(("-" * len(m)).center(35))
            pp.printLine("+----+----+----+----+----+----+----+")
            pp.printLine("|Mon |Tue |Wed |Thu |Fri |Sat |Sun |")
            pp.printLine("+----+----+----+----+----+----+----+")
            month = date.month

        if date.weekday() == 6:
            week_nr.append("")
            week_type.append("")
            pp.printLine("|".join(week_nr))
            pp.printLine("|".join(week_type))
            pp.printLine("+----+----+----+----+----+----+----+")
            week_type = ['']
            week_nr = ['']
    if week_nr:
        weekday = (date.weekday() + 1) % 7
        if weekday:
            week_type += [' ' * 4] * (6 - date.weekday()) + ['']
            week_nr += [' ' * 4] * (6 - date.weekday()) + ['']
            pp.printLine("|".join(week_nr))
            pp.printLine("|".join(week_type))
            pp.printLine("+----+----+----+----+----+----+----+")
        pp.output()


def main():
    config = TomHoffmanConfig
    if len(sys.argv) > 1:
        if sys.argv[1] == "-lt":
            config = LithuanianConfig
        elif sys.argv[1] == "-hof":
            config = TomHoffmanConfig
        else:
            print "Only -lt and -hof switches are allowed."
            sys.exit(1)

    scoolday_model = createSchooldayModel(config)
    timetable_model = createTimetableModel(config)
    timetable = createTimetable(config)

    cal = timetable_model.createCalendar(scoolday_model, timetable)

    print "================"
    print "MONTHLY CALENDAR"
    print "================"

    printSummaryLegend(timetable_model)
    printCalendarSummary(cal, timetable_model)

    print
    print "==================="
    print "DAY BY DAY CALENDAR"
    print "==================="
    print

    printCalendar(cal, timetable_model)


if __name__ == '__main__':
    main()
