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
from schooltool.basicperson.interfaces import IDemographics, IBasicPerson
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.common import SchoolToolMessage as _
from schooltool.group.interfaces import IGroupContainer
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import IAsset
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.common import format_time_range
from schooltool.contact.contact import URIPerson, URIContact
from schooltool.contact.contact import URIContactRelationship
from schooltool.contact.interfaces import IContact, IContactContainer
from schooltool.contact.interfaces import IContactable
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.term.interfaces import ITermContainer
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.interfaces import ISectionContainer
from schooltool.relationship.relationship import IRelationshipLinks
from schooltool.timetable.interfaces import ITimetableContainer
from schooltool.timetable.interfaces import IScheduleContainer
from schooltool.timetable.interfaces import IHaveTimetables
from schooltool.timetable.daytemplates import CalendarDayTemplates
from schooltool.timetable.daytemplates import WeekDayTemplates
from schooltool.timetable.daytemplates import SchoolDayTemplates


class ExcelExportView(BrowserView):

    def __init__(self, context, request):
        super(ExcelExportView, self).__init__(context, request)
        self._font_cache = {}
        self._style_cache = {}

    def setUpHeaders(self, data):
        """Set up HTTP headers to serve data as excel spreadsheet."""
        response = self.request.response
        response.setHeader('Content-Type', 'application/vnd.ms-excel')
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
        if type(data) == type(True):
            data = str(data)
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

    def format_periods(self, periods, ws, offset):
        self.write_header(ws, offset, 0, "Days")
        max_periods = max([len(day) for day in periods.templates.values()])
        self.write_header(ws, offset, 1, "Periods", merge=max_periods - 1)
        offset += 1

        for day in periods.templates.values():
            self.write(ws, offset, 0, day.title)
            for col, period in enumerate(day.values()):
                self.write(ws, offset, col + 1, period.title)
                self.write(ws, offset + 1, col + 1, period.activity_type)
            offset += 2
        return offset

    def format_time_slots(self, time_slots, ws, offset):
        self.write_header(ws, offset, 0, "Time schedule")
        offset += 1

        for day in time_slots.templates.values():
            self.write(ws, offset, 0, day.title)
            for col, slot in enumerate(day.values()):
                time = format_time_range(slot.tstart, slot.duration)
                self.write(ws, offset, col + 1, time)
                self.write(ws, offset + 1, col + 1, slot.activity_type)
            offset += 2
        return offset

    day_templates = (
        ('calendar_days', CalendarDayTemplates),
        ('week_days', WeekDayTemplates),
        ('school_days', SchoolDayTemplates),
        )

    def format_school_timetable(self, timetable, ws, offset):
        template_ids = dict([(cls, tid)
                             for tid, cls in self.day_templates])
        factory_id = lambda t: template_ids[t.__class__]
        schoolyear_id = lambda t: IHaveTimetables(t).__name__
        fields = [lambda i: ("School Timetable", i.title, None),
                  lambda i: ("ID", i.__name__, None),
                  lambda i: ("School Year", schoolyear_id(i), None),
                  lambda i: ("Period days", factory_id(i.periods), None),
                  lambda i: ("Time slots", factory_id(i.time_slots), None)]

        offset = self.listFields(timetable, fields, ws, offset)
        offset = self.skipRow(ws, offset)
        offset = self.format_periods(timetable.periods, ws, offset)
        offset = self.skipRow(ws, offset)
        offset = self.format_time_slots(timetable.time_slots, ws, offset)
        return offset + 1

    def export_school_timetables(self, wb):
        ws = wb.add_sheet("School Timetables")
        school_years = sorted(ISchoolYearContainer(self.context).values(),
                              key=lambda s: s.first)
        row = 0
        for school_year in sorted(school_years, key=lambda i: i.last):
            timetables = ITimetableContainer(school_year)
            for timetable in sorted(timetables.values(), key=lambda i: i.__name__):
                row = self.format_school_timetable(timetable, ws, row) + 1


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


class ContactRelationship(object):

    def __init__(self, person, contact, relationship):
        self.person = person
        self.contact = contact
        self.relationship = relationship


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

    def format_contact_persons(self):
        def contact_getter(attribute):
            def getter(contact):
                person = IBasicPerson(contact.__parent__, None)
                if person is None:
                    return getattr(contact, attribute)
                if attribute == '__name__':
                    return person.username
                return ''
            return getter

        fields = [('ID', Text, contact_getter('__name__')),
                  ('Prefix', Text, contact_getter('prefix')),
                  ('First Name', Text, contact_getter('first_name')),
                  ('Middle Name', Text, contact_getter('middle_name')),
                  ('Last Name', Text, contact_getter('last_name')),
                  ('Suffix', Text, contact_getter('suffix')),
                  ('Address line 1', Text, attrgetter('address_line_1')),
                  ('Address line 2', Text, attrgetter('address_line_2')),
                  ('City', Date, attrgetter('city')),
                  ('State', Date, attrgetter('state')),
                  ('Country', Date, attrgetter('country')),
                  ('Postal code', Date, attrgetter('postal_code')),
                  ('Home phone', Text, attrgetter('home_phone')),
                  ('Work phone', Text, attrgetter('work_phone')),
                  ('Mobile phone', Text, attrgetter('mobile_phone')),
                  ('Email', Text, attrgetter('email')),
                  ('Language', Text, attrgetter('language'))]

        items = []
        for person in self.context['persons'].values():
            items.append(IContact(person))
        for contact in IContactContainer(self.context).values():
            items.append(contact)

        return self.format_table(fields, items)

    def format_contact_relationships(self):
        fields = [('Person ID', Text, attrgetter('person')),
                  ('Contact ID', Text, attrgetter('contact')),
                  ('Relationship', Text, attrgetter('relationship'))]

        items = []
        for person in self.context['persons'].values():
            person = removeSecurityProxy(person)
            for contact in IContactable(person).contacts:
                try:
                    links = IRelationshipLinks(person)
                    link = links.find(
                        URIPerson, contact, URIContact, URIContactRelationship)
                except ValueError:
                    continue
                target_person = IBasicPerson(contact.__parent__, None)
                if target_person is None:
                    name = contact.__name__
                else:
                    name = target_person.username
                item = ContactRelationship(person.username,
                    name, link.extra_info.relationship)
                items.append(item)

        return self.format_table(fields, items)

    def export_contacts(self, wb):
        ws = wb.add_sheet("Contact Persons")
        self.print_table(self.format_contact_persons(), ws)
        ws = wb.add_sheet("Contact Relationships")
        self.print_table(self.format_contact_relationships(), ws)

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
                  ('Description', Text, attrgetter('description')),
                  ('Local ID', Text, attrgetter('course_id')),
                  ('Government ID', Text, attrgetter('government_id')),
                  ('Credits', Text, attrgetter('credits'))]

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
        schedules = IScheduleContainer(section)
        if not schedules:
            return offset
        schedules = list(sorted(schedules.values(),
                                key=lambda s: s.timetable.__name__))
        for schedule in schedules:
            timetable = schedule.timetable
            self.write_header(ws, offset, 0,  "School Timetable")
            self.write(ws, offset, 1,  timetable.__name__)
            offset += 1

            self.write(ws, offset, 0,  "Consecutive periods as one")
            self.write(ws, offset, 1,
                       schedule.consecutive_periods_as_one and 'yes' or 'no')
            offset += 1

            self.write_header(ws, offset, 0,  "Day")
            self.write_header(ws, offset, 1,  "Period")
            offset += 1

            for period in schedule.periods:
                day = period.__parent__
                self.write(ws, offset, 0,  day.title)
                self.write(ws, offset, 1,  period.title)
                offset += 1
            offset += 1
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
                    if not list(section.courses):
                        continue
                    row = self.format_section(section, ws, row) + 1

    def format_flat_section(self, section, ws, row):
        self.write(ws, row, 3, section.__name__)
        self.write(ws, row, 4, section.title)
        if section.description:
            self.write(ws, row, 5, section.description)
        if section.previous is not None:
            self.write(ws, row, 9, section.previous.__name__)
        if section.next is not None:
            self.write(ws, row, 10, section.next.__name__)

        teachers = [t.__name__ for t in section.instructors]
        students = [s.__name__ for s in section.members]
        resources = [r.__name__ for r in section.resources]
        schedules = list(IScheduleContainer(section).values())
        if schedules:
            schedule = schedules[0]
            self.write(ws, row, 11, schedule.timetable.__name__)
            self.write(ws, row, 12, (schedule.consecutive_periods_as_one
                                     and 'yes' or 'no'))
            days = [p.__parent__.title for p in schedule.periods]
            periods = [p.title for p in schedule.periods]
        else:
            days = []
            periods = []
        line_maps = map(None, teachers, students, resources, days,
                        periods)
        if line_maps:
            for line_map in line_maps:
                teacher, student, resource, day, period = line_map
                if teacher is not None:
                    self.write(ws, row, 6, teacher)
                if student is not None:
                    self.write(ws, row, 7, student)
                if resource is not None:
                    self.write(ws, row, 8, resource)
                if day is not None:
                    self.write(ws, row, 13, day)
                    self.write(ws, row, 14, period)
                row += 1
        else:
            row += 1
        return row

    def export_flat_sections(self, wb):
        ws = wb.add_sheet("FlatSectionsTable")
        headers = ["School Year", "Courses", "Term", "Section ID", "Title",
                   "Description", "Instructors", "Students", "Resources",
                   "Link Prev", "Link Next", "Timetable", "Consecutive",
                   "Day", "Period ID"]
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        sections = {}
        for year in ISchoolYearContainer(self.context).values():
            current_sections = sections[year] = []
            for term in year.values():
                first = term.first
                for section in ISectionContainer(term).values():
                    if not list(section.courses):
                        continue
                    courses = ', '.join([c.__name__ for c in section.courses])
                    current_sections.append((courses, first, term, section))

        row = 1
        for year in sorted(sections, key=lambda y: y.first):
            self.write(ws, row, 0,  year.__name__)
            timetables = ITimetableContainer(year)
            current_sections = sections[year]
            current_courses = None
            for courses, first, term, section in sorted(current_sections):
                if courses != current_courses:
                    self.write(ws, row, 1,  courses)
                    current_courses = courses
                    current_term = None
                if term != current_term:
                    self.write(ws, row, 2, term.__name__)
                    current_term = term
                row = self.format_flat_section(section, ws, row)

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
        self.export_contacts(wb)
        self.export_courses(wb)
        self.export_flat_sections(wb)
        self.export_groups(wb)

        datafile = StringIO()
        wb.save(datafile)
        data = datafile.getvalue()
        self.setUpHeaders(data)
        return data
