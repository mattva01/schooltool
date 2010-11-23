#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
SchoolTool XLS export views.
"""
import xlwt
from StringIO import StringIO
import datetime
from operator import attrgetter

from zope.security.proxy import removeSecurityProxy
from zope.publisher.browser import BrowserView

from schooltool.basicperson.demographics import DateFieldDescription
from schooltool.basicperson.interfaces import IDemographics
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.group.interfaces import IGroupContainer
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import IAsset
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.timetable.browser import format_time_range
from schooltool.timetable.interfaces import ITimetableCalendarEvent
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable.interfaces import ITimetableSchemaContainer
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.term.interfaces import ITermContainer
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.interfaces import ISectionContainer


class ExcelExportView(BrowserView):

    def __init__(self, context, request):
        self.context, self.request = context, request
        self._font_cache = {}
        self._style_cache = {}

    def setUpHeaders(self, data):
        """Set up HTTP headers to serve data as PDF."""
        response = self.request.response
        response.setHeader('Content-Type', 'application/excel')
        response.setHeader('Content-Length', len(data))

    def listIds(self, header, items, ws, offset, last=False):
        if not items:
            return offset - 1
        self.write_header(ws, offset + 1, 0,  header, merge=1)
        for n, item in enumerate(sorted(items, key=lambda i: i.__name__)):
            self.write(ws, offset + 2 + n, 0,  item.__name__)
            self.write(ws, offset + 2 + n, 1,  "")
        return 1 + offset + len(items)

    def skipRow(self, ws, offset):
        return offset + 1

    def listFields(self, item, accessors, ws, offset):
        for n, accessor in enumerate(accessors):
            header, field, style = accessor(item)
            self.write_header(ws, offset + n, 0, header)
            self.write(ws, offset + n, 1, field, format_str=style)
        return offset + len(accessors)

    def _makeFont(self, font_key):
        font = xlwt.Font()
        for attr, value in font_key:
            setattr(font, attr, value)
        return font

    def getFont(self, font_key):
        font = self._font_cache.get(font_key, None)
        if font is None:
            self._font_cache[font_key] = font = self._makeFont(font_key)
        return font

    def write(self, ws, row, col, data,
              bold=False,
              color=None,
              format_str=None,
              borders=None,
              merge=None):
        if borders is None:
            borders = []
        if data is None:
            data = ""
        key = (bold, color, format_str, tuple(borders))
        style = self._style_cache.get(key, None)
        if style is None:
            style = xlwt.XFStyle()
            if bold:
                style.font = self.getFont((("bold", True),))

            if color is not None:
                pattern = xlwt.Pattern()
                pattern.pattern = xlwt.Pattern.SOLID_PATTERN
                pattern.pattern_fore_colour = color
                style.pattern = pattern

            if format_str is not None:
                style.num_format_str = 'YYYY-MM-DD'

            if borders:
                b = xlwt.Formatting.Borders()
                for border in borders:
                    setattr(b, border, xlwt.Formatting.Borders.THIN)
                style.borders = b
            self._style_cache[key] = style
        if merge is None:
            ws.write(row, col, data, style)
        else:
            ws.write_merge(row, row, col, col + merge, data, style)

    def write_header(self, ws, row, col, data,
                     borders=None, merge=None):
        YELLOW = 5
        self.write(ws, row, col, data, borders=borders, bold=True, color=YELLOW,
                   merge=merge)


class SchoolTimetableExportView(ExcelExportView):

    dows = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday']

    def format_day_templates(self, school_tt, ws, offset):
        self.write_header(ws, offset, 0, "Day Templates")
        offset += 1

        day_templates = school_tt.model.dayTemplates.items()
        for row, (id, day) in enumerate(day_templates):
            if id is None:
                used = "default"
            elif id in school_tt.keys():
                used = id
            else:
                used = self.dows[id]
            self.write(ws, offset + row, 0, used)
            periods = []
            for col, period in enumerate(sorted(day, key=lambda p: p.tstart)):
                period_str = format_time_range(period.tstart, period.duration)
                self.write(ws, offset + row, col + 1, period_str)
        return offset + len(day_templates)

    def format_days(self, school_tt, ws, offset):
        self.write_header(ws, offset, 0, "Days")
        max_periods = max([len(day.periods) for day_id, day in school_tt.items()])
        self.write_header(ws, offset, 1, "Periods", merge=max_periods - 1)

        max_homerooms = max([len(day.homeroom_period_ids)
                             for day_id, day in school_tt.items()])
        if max_homerooms:
            self.write_header(ws, offset, 1 + max_periods, "Homeroom periods",
                              merge=max_homerooms - 1)

        for row, (day_id, day) in enumerate(school_tt.items()):
            self.write(ws, offset + row + 1, 0, day_id)
            for col, period in enumerate(day.periods):
                self.write(ws, offset + row + 1, col + 1, period)
            for col, period in enumerate(day.homeroom_period_ids):
                self.write(ws, offset + row + 1, max_periods + col + 1, period)

        return offset + len(school_tt.items())

    def format_school_timetable(self, school_tt, ws, offset):
        fields = [lambda i: ("School Timetable", i.title, None),
                  lambda i: ("ID", i.__name__, None),
                  lambda i: ("School Year", ISchoolYear(i).__name__, None),
                  lambda i: ("Model", i.model.factory_id, None)]

        offset = self.listFields(school_tt, fields, ws, offset)
        offset = self.skipRow(ws, offset)
        offset = self.format_day_templates(school_tt, ws, offset)
        offset = self.skipRow(ws, offset)
        offset = self.format_days(school_tt, ws, offset)
        return offset + 1

    def export_school_timetables(self, wb):
        ws = wb.add_sheet("School Timetables")
        school_years = sorted(ISchoolYearContainer(self.context).values(),
                              key=lambda s: s.first)
        row = 0
        for school_year in sorted(school_years, key=lambda i: i.last):
            school_tts = ITimetableSchemaContainer(school_year)
            for school_tt in sorted(school_tts.values(), key=lambda i: i.__name__):
                row = self.format_school_timetable(school_tt, ws, row) + 1


def merge_date_ranges(dates):
    ranges = []
    start = None
    previous_day = None
    for day in dates:
        if start is None:
            previous_day = start = day
        elif day - datetime.timedelta(days=1) == previous_day:
            previous_day = day
        else:
            ranges.append((start, previous_day))
            previous_day = start = day
    if start is not None:
        ranges.append((start, previous_day))

    return ranges


class Text(object):

    style = {}
    def __init__(self, data):
        self.data = data

    def __cmp__(self, other):
        return cmp(self.data, other.data)

    def __repr__(self):
        return 'Text(%r)' % self.data


class Header(Text):
    YELLOW = 5
    style = {'bold': True,
             'color': YELLOW}

    def __repr__(self):
        return 'Header(%r)' % self.data


class Date(Text):
    style = {'format_str': 'YYYY-MM-DD'}

    def __repr__(self):
        return 'Date(%r)' % self.data


class MegaExporter(SchoolTimetableExportView):

    def print_table(self, table, ws):
        for x, row in enumerate(table):
            for y, cell in enumerate(row):
                self.write(ws, x, y, cell.data, **cell.style)
        return len(table)

    def format_table(self, fields, items):
        headers = [Header(header)
                   for header, style, getter in fields]
        rows = []
        for item in items:
            row = [style(getter(item))
                   for header, style, getter in fields]
            rows.append(row)
        rows.sort()
        return [headers] + rows

    def format_school_years(self):
        fields = [('ID', Text, attrgetter('__name__')),
                  ('Title', Text, attrgetter('title')),
                  ('Start', Date, attrgetter('first')),
                  ('End', Date, attrgetter('last'))]
        items = ISchoolYearContainer(self.context).values()
        return self.format_table(fields, items)

    def export_school_years(self, wb):
        ws = wb.add_sheet("School Years")
        self.print_table(self.format_school_years(), ws)

    def calculate_holidays_and_weekdays(self):

        work_days = 0.0

        days_of_week = {}
        for dow in range(7):
            days_of_week[dow] = [0, 0]

        school_years = ISchoolYearContainer(self.context).values()
        for school_year in school_years:
            terms = ITermContainer(school_year).values()
            for term in terms:
                for date in term:
                    if term.isSchoolday(date):
                        days_of_week[date.weekday()][0] += 1
                        work_days += 1
                    else:
                        days_of_week[date.weekday()][1] += 1

        if work_days == 0:
            return [[], list(range(7)), []]

        coefficients = [counts[0] / work_days
                        for day, counts in sorted(days_of_week.items())]

        # Weekends
        weekends = []
        for n, k in enumerate(coefficients):
            if k < 0.1:
                weekends.append(n)

        # Weekend exceptions and holidays
        holidays = []
        weekend_exceptions = []
        for school_year in school_years:
            terms = ITermContainer(school_year).values()
            for term in terms:
                for date in term:
                    if term.isSchoolday(date) and date.weekday() in weekends:
                        weekend_exceptions.append(date)
                    elif not term.isSchoolday(date) and date.weekday() not in weekends:
                        holidays.append(date)

        holiday_ranges = merge_date_ranges(holidays)
        return [holiday_ranges, weekends, weekend_exceptions]

    def format_holidays(self, holidays):
        if not holidays:
            return []
        table = [[], [Header("Holidays")]]
        table.extend([[Date(start), Date(end)]
                      for start, end in holidays])
        return table

    def format_weekends(self, weekends):
        if not weekends:
            return []

        table = [[], [Header("Weekends")]]
        weekdays = map(Text, ['Monday',
                              'Tuesday',
                              'Wednesday',
                              'Thursday',
                              'Friday',
                              'Saturday',
                              'Sunday'])
        table.append(weekdays)
        table.append([weekday in weekends and Text('X') or Text('')
                      for weekday in range(len(weekdays))])
        return table

    def format_weekend_exceptions(self, working_weekends):
        if not working_weekends:
            return []

        table = [[], [Header("Working weekends")]]
        table.extend([[Date(day)]
                      for day in working_weekends])
        return table

    def format_terms(self):
        fields = [('SchoolYear', Text, lambda t: t.__parent__.__name__),
                  ('ID', Text, attrgetter('__name__')),
                  ('Title', Text, attrgetter('title')),
                  ('Start', Date, attrgetter('first')),
                  ('End', Date, attrgetter('last'))]

        school_years = ISchoolYearContainer(self.context).values()
        items = []
        for year in school_years:
            items.extend([term for term in
                          ITermContainer(year).values()])
        terms_table = self.format_table(fields, items)
        holidays, weekends, exceptions = self.calculate_holidays_and_weekdays()
        terms_table.extend(self.format_holidays(holidays))
        terms_table.extend(self.format_weekends(weekends))
        terms_table.extend(self.format_weekend_exceptions(exceptions))
        return terms_table

    def export_terms(self, wb):
        ws = wb.add_sheet("Terms")
        self.print_table(self.format_terms(), ws)

    def format_persons(self):
        fields = [('User Name', Text, attrgetter('__name__')),
                  ('Prefix', Text, attrgetter('prefix')),
                  ('First Name', Text, attrgetter('first_name')),
                  ('Middle Name', Text, attrgetter('middle_name')),
                  ('Last Name', Text, attrgetter('last_name')),
                  ('Suffix', Text, attrgetter('suffix')),
                  ('Preferred Name', Text, attrgetter('preferred_name')),
                  ('Birth Date', Date, attrgetter('birth_date')),
                  ('Gender', Text, attrgetter('gender')),
                  ('Password', Text, lambda p: None)]

        def demographics_getter(attribute):
            def getter(person):
                demographics = IDemographics(person)
                return demographics[attribute]
            return getter

        app = ISchoolToolApplication(None)
        demographics_fields = IDemographicsFields(app)
        for field in demographics_fields.values():
            title = field.title
            format = Text
            if isinstance(field, DateFieldDescription):
                format = Date
            getter = demographics_getter(field.name)
            fields.append((title, format, getter))

        items = self.context['persons'].values()
        return self.format_table(fields, items)

    def export_persons(self, wb):
        ws = wb.add_sheet("Persons")
        self.print_table(self.format_persons(), ws)

    def format_resources(self):
        fields = [('ID', Text, attrgetter('__name__')),
                  ('Type', Text, lambda r: r.__class__.__name__),
                  ('Title', Text, attrgetter('title'))]
        items = self.context['resources'].values()
        return self.format_table(fields, items)

    def export_resources(self, wb):
        ws = wb.add_sheet("Resources")
        self.print_table(self.format_resources(), ws)

    def format_courses(self):
        fields = [('School Year', Text, lambda c: ISchoolYear(c).__name__),
                  ('ID', Text, attrgetter('__name__')),
                  ('Title', Text, attrgetter('title')),
                  ('Description', Date, attrgetter('description'))]

        school_years = ISchoolYearContainer(self.context).values()
        items = []
        for year in school_years:
            items.extend([term for term in
                          ICourseContainer(year).values()])
        return self.format_table(fields, items)

    def export_courses(self, wb):
        ws = wb.add_sheet("Courses")
        self.print_table(self.format_courses(), ws)

    def format_timetables(self, section, ws, offset):
        timetables = ITimetables(section).timetables.values()
        if not timetables:
            return offset
        timetables.sort(key=lambda t: t.schooltt.__name__)
        for timetable in timetables:
            self.write_header(ws, offset, 0,  "School Timetable")
            self.write(ws, offset, 1,  timetable.schooltt.__name__)
            offset += 1

            self.write_header(ws, offset, 0,  "Day")
            self.write_header(ws, offset, 1,  "Period ID")
            self.write_header(ws, offset, 2,  "Location ID")
            offset += 1

            for n, (day_id, period_id, activity) in enumerate(timetable.activities()):
                resource = None
                for event in ISchoolToolCalendar(section):
                    if ITimetableCalendarEvent.providedBy(event):
                        if event.activity == activity:
                            if event.resources:
                                resource = event.resources[0]
                            break
                self.write(ws, offset + n, 0,  day_id)
                self.write(ws, offset + n, 1,  period_id)
                if resource is not None:
                    self.write(ws, offset + n, 2,  resource.__name__)
            offset += 1 + len(timetable.activities())
        return offset

    def format_section(self, section, ws, offset):
        fields = [lambda i: ("Section Title", i.title, None),
                  lambda i: ("ID", i.__name__, None),
                  lambda i: ("Description", i.description, None)]

        offset = self.listFields(section, fields, ws, offset)
        offset = self.listIds("Courses", section.courses, ws, offset)
        offset = self.skipRow(ws, offset)
        offset = self.listIds("Students", section.members, ws, offset)
        offset = self.skipRow(ws, offset)
        offset = self.listIds("Instructors", section.instructors, ws, offset)
        offset = self.skipRow(ws, offset) + 1
        offset = self.format_timetables(section, ws, offset)
        return offset

    def export_sections(self, wb):
        school_years = sorted(ISchoolYearContainer(self.context).values(),
                              key=lambda s: s.first)

        for school_year in sorted(school_years, key=lambda i: i.last):
            for term in sorted(school_year.values(), key=lambda i: i.last):
                row = 0
                ws = wb.add_sheet("Sections %s %s" % (school_year.__name__[:10],
                                                      term.__name__[:11]))

                self.write_header(ws, row, 0,  "School Year")
                self.write(ws, row, 1,  school_year.__name__)
                self.write_header(ws, row, 2,  "Term")
                self.write(ws, row, 3,  term.__name__)

                row += 2
                sections = removeSecurityProxy(ISectionContainer(term))
                for section in sorted(sections.values(), key=lambda i: i.__name__):
                    row = self.format_section(section, ws, row) + 1

    def format_group(self, group, ws, offset):
        fields = [lambda i: ("Group Title", i.title, None),
                  lambda i: ("ID", i.__name__, None),
                  lambda i: ("School Year", ISchoolYear(i.__parent__).__name__, None),
                  lambda i: ("Description", i.description, None)]

        offset = self.listFields(group, fields, ws, offset)
        offset = self.listIds("Members", group.members, ws, offset) + 1
        offset = self.listIds("Leaders", IAsset(group).leaders, ws, offset,
                              last=True) + 1
        return offset

    def export_groups(self, wb):
        ws = wb.add_sheet("Groups")
        school_years = sorted(ISchoolYearContainer(self.context).values(),
                              key=lambda s: s.first)
        row = 0
        for school_year in sorted(school_years, key=lambda i: i.last):
            groups = IGroupContainer(school_year)
            for group in sorted(groups.values(), key=lambda i: i.__name__):
                row = self.format_group(group, ws, row) + 1

    def __call__(self):
        wb = xlwt.Workbook()

        self.export_school_years(wb)
        self.export_terms(wb)
        self.export_school_timetables(wb)
        self.export_resources(wb)
        self.export_persons(wb)
        self.export_courses(wb)
        self.export_sections(wb)
        self.export_groups(wb)

        datafile = StringIO()
        wb.save(datafile)
        data = datafile.getvalue()
        self.setUpHeaders(data)
        return data
