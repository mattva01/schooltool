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
"""\
A text calendar script to demonstrate the calendaring functionality.

$Id$

Usage:

  textcal.py <config.xml>
"""
import datetime
import libxml2
import sys
import os.path
from sets import Set
import schooltool.cal
from schooltool.cal import Timetable, TimetableDay, TimetableActivity
from schooltool.cal import SchooldayModel, SchooldayPeriod, SchooldayTemplate
from schooltool.schema.rng import validate_against_schema


def createSchooldayModel(config):
    data = config.schooldays
    sc = SchooldayModel(data['first'], data['last'])
    sc.addWeekdays(*data['weekdays'])
    for holiday in data['holidays']:
        if sc.isSchoolday(holiday):
            sc.remove(holiday)
    return sc


def createTimetable(config):
    days = [item[0] for item in config.timetable]
    tt_data = config.timetable
    tt = Timetable(days)
    for day, periods in tt_data:
        ttday = TimetableDay([item[0] for item in periods])
        tt[day] = ttday
        for period, activity in periods:
            ttday.add(period, TimetableActivity(activity))
    return tt


def createTimetableModel(config):
    days = [item[0] for item in config.timetable]
    dt_data = config.day_templates.copy()
    dtemplates = {}
    for weekday in dt_data:
        dt = SchooldayTemplate()
        title = dt_data[weekday]["title"]
        dt.title = title
        period_ids = dt_data[weekday].keys()
        period_ids.remove('title')
        for pid in period_ids:
            start, duration = dt_data[weekday][pid]
            dt.add(SchooldayPeriod(pid, start, duration))
        if weekday == "default":
            weekday = None
        dtemplates[weekday] = dt
    return config.timetable_model_factory(days, dtemplates)


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


def package_home(pkg):
    filename = getattr(pkg, "__file__")
    return os.path.dirname(filename)


class XMLConfig:

    def __init__(self, xml):
        schema = file(os.path.join(package_home(schooltool.cal),
                                   'schema', 'ttconfig.rng')).read()
        if not validate_against_schema(schema, xml):
            print >> sys.stderr, "Config not valid"
            return 1
        doc = libxml2.parseDoc(xml)
        self.context = doc.xpathNewContext()
        ns = 'http://schooltool.org/ns/ttconfig/0.1'
        self.context.xpathRegisterNs('tt', ns)

        self.timetable = self.extractTimetableData()
        self.day_templates = self.extractDayTemplates()
        self.schooldays = self.extractSchooldays()
        self.timetable_model_factory = self.extractFactory()

    def extractTimetableData(self):
        tt = []
        for day in self.context.xpathEval('/tt:ttconfig/tt:timetable/tt:day'):
            day_id = day.nsProp('id', None)
            periods = []
            for period in day.xpathEval('*'):
                periods.append((period.nsProp('id', None),
                                period.get_content()))
            tt.append((day_id, tuple(periods)))
        return tuple(tt)

    def extractDayTemplates(self):
        result = {}
        for template in self.context.xpathEval('/tt:ttconfig/tt:daytemplate'):
            dayid = template.nsProp('id', None)
            self.context.setContextNode(template)
            day = {'title': dayid}
            for period in self.context.xpathEval('tt:period'):
                pid = period.nsProp('id', None)
                tstart_str = period.nsProp('tstart', None)
                dur_str = period.nsProp('duration', None)
                h, m = [int(s) for s in tstart_str.split(":")]
                dur = int(dur_str)
                day[pid] = (datetime.time(h, m),
                            datetime.timedelta(minutes=dur))
            used = self.context.xpathEval('tt:used')[0].nsProp('when', None)
            if used == 'default':
                result[None] = day
            else:
                for dow in used.split():
                    result[dow] = day
        return result

    dow_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
               "Friday": 4, "Saturday": 5, "Sunday": 6}

    def extractSchooldays(self):
        result = {}  # first, last, weekdays, holidays
        schooldays = self.context.xpathEval('/tt:ttconfig/tt:schooldays')[0]
        self.context.setContextNode(schooldays)
        first = schooldays.nsProp('first', None)
        last = schooldays.nsProp('last', None)
        y, m, d = map(int, first.split('-'))
        result['first'] = datetime.date(y, m, d)
        y, m, d = map(int, last.split('-'))
        result['last'] = datetime.date(y, m, d)
        holidays = []
        for holiday in self.context.xpathEval('tt:holiday'):
            ds = holiday.nsProp('date', None)
            y, m, d = map(int, ds.split('-'))
            holidays.append(datetime.date(y, m, d))
        result['holidays'] = tuple(holidays)
        dows_str = self.context.xpathEval('tt:daysofweek')[0].get_content()
        result['weekdays'] = tuple([self.dow_map[d] for d in dows_str.split()])
        return result

    def extractFactory(self):
        ttm = self.context.xpathEval('/tt:ttconfig/tt:timetablemodel')[0]
        class_ = ttm.nsProp('class', None)
        endmod = class_.rindex(".")
        modname = class_[:endmod]

        obj = __import__(modname)
        components = class_.split('.')
        for component in components[1:]:
            obj = getattr(obj, component)
        return obj


def main():

    if len(sys.argv) > 1:
        xml = file(sys.argv[1]).read()
        config = XMLConfig(xml)
    else:
        print __doc__
        return 1

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

    return 0

if __name__ == '__main__':
    sys.exit(main())
