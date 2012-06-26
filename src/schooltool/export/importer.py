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
SchoolTool simple import views.
"""
import xlrd
import transaction
import datetime
from decimal import Decimal, InvalidOperation

from zope.container.contained import containedEvent
from zope.container.interfaces import INameChooser
from zope.event import notify
from zope.i18n import translate
from zope.security.proxy import removeSecurityProxy
from zope.publisher.browser import BrowserView
from zope.traversing.browser.absoluteurl import absoluteURL

import schooltool.skin.flourish.page
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.interfaces import IDemographics
from schooltool.basicperson.demographics import DateFieldDescription
from schooltool.basicperson.demographics import BoolFieldDescription
from schooltool.basicperson.person import BasicPerson
from schooltool.contact.contact import Contact, ContactPersonInfo
from schooltool.contact.interfaces import IContact, IContactContainer
from schooltool.contact.interfaces import IContactPersonInfo, IContactable
from schooltool.resource.resource import Resource
from schooltool.resource.resource import Location
from schooltool.resource.resource import Equipment
from schooltool.group.group import Group
from schooltool.group.interfaces import IGroupContainer
from schooltool.term.interfaces import ITerm
from schooltool.term.term import Term, getNextTerm, getPreviousTerm
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.app import SimpleNameChooser
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.skin import flourish
from schooltool.course.section import Section
from schooltool.course.interfaces import ISectionContainer
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.course import Course
from schooltool.common import DateRange
from schooltool.common import parse_time_range
from schooltool.timetable.daytemplates import CalendarDayTemplates
from schooltool.timetable.daytemplates import WeekDayTemplates
from schooltool.timetable.daytemplates import SchoolDayTemplates
from schooltool.timetable.daytemplates import DayTemplate
from schooltool.timetable.daytemplates import TimeSlot
from schooltool.timetable.interfaces import ITimetableContainer
from schooltool.timetable.interfaces import IScheduleContainer
from schooltool.timetable.schedule import Period
from schooltool.timetable.timetable import Timetable
from schooltool.timetable.timetable import SelectedPeriodsSchedule

from schooltool.common import format_message
from schooltool.common import SchoolToolMessage as _


ERROR_NOT_INT = _('is not a valid integer')
ERROR_NOT_UNICODE_OR_ASCII = _('not unicode or ascii string')
ERROR_MISSING_REQUIRED_TEXT = _('missing required text')
ERROR_NO_DATE = _('has no date in it')
ERROR_END_BEFORE_START = _('end date cannot be before start date')
ERROR_START_OVERLAP = _('start date overlaps another year')
ERROR_END_OVERLAP = _('end date overlaps another year')
ERROR_INVALID_SCHOOL_YEAR = _('invalid school year')
ERROR_START_BEFORE_YEAR_START = _('start date before start of school year')
ERROR_END_AFTER_YEAR_END = _('end date after end of school year')
ERROR_START_OVERLAP_TERM = _('start date overlaps another term')
ERROR_END_OVERLAP_TERM = _('end date overlaps another term')
ERROR_HAS_NO_DAYS = _("${title} has no days in A${row}")
ERROR_HAS_NO_DAY_TEMPLATES = _("${title} has no day templates in A${row}")
ERROR_TIME_RANGE = _("is not a valid time range")
ERROR_TIMETABLE_MODEL = _("is not a valid timetable model")
ERROR_DUPLICATE_DAY_ID = _("is the same day id as another in this timetable")
ERROR_UNKNOWN_DAY_ID = _("is not defined in the 'Day Templates' section")
ERROR_DUPLICATE_PERIOD = _("is the same period id as another in this day")
ERROR_DUPLICATE_HOMEROOM_PERIOD = _("is the same homeroom period id as another in this day")
ERROR_RESOURCE_TYPE = _("must be either 'Location', 'Equipment' or 'Resource'")
ERROR_INVALID_TERM_ID = _('is not a valid term in the given school year')
ERROR_INVALID_COURSE_ID = _('is not a valid course in the given school year')
ERROR_HAS_NO_COURSES = _('${title} has no courses in A${row}')
ERROR_INVALID_PERSON_ID = _('is not a valid username')
ERROR_INVALID_SCHEMA_ID = _('is not a valid timetable in the given school year')
ERROR_INVALID_DAY_ID = _('is not a valid day id for the given timetable')
ERROR_INVALID_PERIOD_ID = _('is not a valid period id for the given day')
ERROR_INVALID_CONTACT_ID = _('is not a valid username or contact id')
ERROR_UNWANTED_CONTACT_DATA = _('must be empty when ID is a user id')
ERROR_INVALID_RESOURCE_ID = _('is not a valid resource id')
ERROR_UNICODE_CONVERSION = _("Username cannot contain non-ascii characters")
ERROR_WEEKLY_DAY_ID = _('is not a valid weekday number (0-6)')
ERROR_CONTACT_RELATIONSHIP = _("is not a valid contact relationship")
ERROR_NOT_BOOLEAN = _("must be either True or False")
ERROR_MISSING_YEAR_ID = _("must have a school year")
ERROR_MISSING_COURSES = _("must have a course")
ERROR_MISSING_TERM_ID = _("must have a term")
ERROR_CURRENT_SECTION_FIRST_TERM = _("the current section is in the first term of the school year")
ERROR_CURRENT_SECTION_LAST_TERM = _("the current section is in the last term of the school year")
ERROR_INVALID_PREV_TERM_SECTION = _("is not a valid section id in the previous term")
ERROR_INVALID_NEXT_TERM_SECTION = _("is not a valid section id in the next term")
ERROR_NO_TIMETABLE_DEFINED = _("no timetable is defined for this section")
ERROR_NO_DAY_DEFINED = _("no day is defined in this row")
ERROR_MISSING_PERIOD_ID = _('must have a valid period id')
ERROR_INVALID_COURSE_CREDITS = _("course credits need to be a valid number")
ERROR_INVALID_GENDER = _("gender must be male or female")
ERROR_INVALID_PERSON_ID_LIST = _("has an invalid username")
ERROR_INVALID_RESOURCE_ID_LIST = _("gender must be male")
ERROR_END_TERM_BEFORE_START = _('end term cannot be before start term')
ERROR_TERM_SECTION_ID = _('one of the specified terms does not have this section id')
ERROR_ID_MUST_BE_TEXT = _('numeric ids must be formatted as text, not numeric')


no_date = object()
no_data = object()


class ImporterBase(object):

    def __init__(self, context, request):
        self.context, self.request = context, request
        self.errors = []

    def getCellValue(self, sheet, row, col, default=no_data):
        try:
            return sheet.cell_value(rowx=row, colx=col)
        except IndexError:
            if default != no_data:
                return default
            raise

    def error(self, row, col, message):
        full_message = (self.sheet_name, row, col, message)
        self.errors.append(full_message)

    def getCellAndFound(self, sheet, row, col, default=u''):
        try:
            return sheet.cell_value(rowx=row, colx=col), True
        except:
            return default, False

    def getIntFoundValid(self, sheet, row, col, default=0):
        value, found = self.getCellAndFound(sheet, row, col, default)
        valid = True
        if found:
            if isinstance(value, float):
                if int(value) != value:
                    self.error(row, col, ERROR_NOT_INT)
                    valid = False
                else:
                    value = int(value)
            elif not isinstance(value, int):
                self.error(row, col, ERROR_NOT_INT)
                valid = False
        return value, found, valid

    def getIntFromCell(self, sheet, row, col, default=0):
        value, found, valid = self.getIntFoundValid(sheet, row, col, default)
        return value

    def getRequiredIntFromCell(self, sheet, row, col):
        value, found, valid = self.getIntFoundValid(sheet, row, col)
        if not found:
            self.error(row, col, ERROR_NOT_INT)
        return value

    def getTextFoundValid(self, sheet, row, col, default=u''):
        value, found = self.getCellAndFound(sheet, row, col, default)
        valid = True
        if found:
            if isinstance(value, float):
                if int(value) == value:
                    value = int(value)
            try:
                value = unicode(value)
            except UnicodeError:
                self.error(row, col, ERROR_NOT_UNICODE_OR_ASCII)
                valid = False
        return value, found, valid

    def getTextFromCell(self, sheet, row, col, default=u''):
        value, found, valid = self.getTextFoundValid(sheet, row, col, default)
        return value

    def getRequiredTextFromCell(self, sheet, row, col):
        value, found, valid = self.getTextFoundValid(sheet, row, col)
        if valid and not value:
            self.error(row, col, ERROR_MISSING_REQUIRED_TEXT)
        return value

    def getDateFromCell(self, sheet, row, col, default=no_date):
        value, found = self.getCellAndFound(sheet, row, col)
        if not found or value == '':
            if default is no_date:
                self.error(row, col, ERROR_NO_DATE)
                return None
            else:
                return default
        try:
            dt = xlrd.xldate_as_tuple(value, self.wb.datemode)
        except:
            self.error(row, col, ERROR_NO_DATE)
            return None
        return datetime.datetime(*dt).date()

    def getBoolFromCell(self, sheet, row, col):
        value, found = self.getCellAndFound(sheet, row, col)
        if not found:
            return None
        if type(value) == type(True):
            return value
        if type(value) == type(0):
            return bool(value)
        value, found, valid = self.getTextFoundValid(sheet, row, col)
        if not valid or not value:
            return None
        if value.upper() in ['TRUE', 'YES']:
            return True
        elif value.upper() in ['FALSE', 'NO']:
            return False
        else:
            self.error(row, col, ERROR_NOT_BOOLEAN)
            return None

    def getRequiredBoolFromCell(self, sheet, row, col):
        value, found = self.getCellAndFound(sheet, row, col)
        if not found or value == '':
            self.error(row, col, ERROR_MISSING_REQUIRED_TEXT)
            return None
        return self.getBoolFromCell(sheet, row, col)

    def getIdFromCell(self, sheet, row, col, default=u''):
        value, found = self.getCellAndFound(sheet, row, col, default)
        if found:
            if not isinstance(value, str) and not isinstance(value, unicode):
                self.error(row, col, ERROR_ID_MUST_BE_TEXT)
                return None
            return value
        return default

    def getRequiredIdFromCell(self, sheet, row, col):
        value = self.getIdFromCell(sheet, row, col)
        if value is not None and not value:
            self.error(row, col, ERROR_MISSING_REQUIRED_TEXT)
        return value

    def getIdsFromCell(self, sheet, row, col):
        value, found = self.getCellAndFound(sheet, row, col)
        return [p.strip() for p in str(value).split(',') if p.strip()]

    def getRequiredIdsFromCell(self, sheet, row, col):
        value, found = self.getCellAndFound(sheet, row, col)
        if not found or value == '':
            self.error(row, col, ERROR_MISSING_REQUIRED_TEXT)
            return None
        return self.getIdsFromCell(sheet, row, col)

    def validateUnicode(self, value, row, col):
        # XXX: this has to be fixed
        # XXX: SchoolTool should handle UTF-8
        try:
            value.encode('ascii')
        except UnicodeEncodeError:
            self.error(row, col, ERROR_UNICODE_CONVERSION)

    @property
    def sheet(self):
        if self.sheet_name not in self.wb.sheet_names():
            return
        return self.wb.sheet_by_name(self.sheet_name)

    def import_data(self, wb):
        self.wb = wb
        if self.sheet:
            return self.process()

    def ensure_students_group(self, year):
        gc = IGroupContainer(year)
        if 'students' in gc:
            return gc['students']
        else:
            students = Group(_('Students'))
            students.__name__ = 'students'
            gc['students'] = students
            return students

    def ensure_teachers_group(self, year):
        gc = IGroupContainer(year)
        if 'teachers' in gc:
            return gc['teachers']
        else:
            teachers = Group(_('Teachers'))
            teachers.__name__ = 'teachers'
            gc['teachers'] = teachers
            return teachers

    def validateStartEndTerms(self, year, data, row, col):
        if data['start_term'] not in year:
            self.error(row, col, ERROR_INVALID_TERM_ID)
            return []
        start_term = year[data['start_term']]
        if data['end_term']:
            if data['end_term'] not in year:
                self.error(row, col + 1, ERROR_INVALID_TERM_ID)
                return []
            else:
                end_term = year[data['end_term']]
        else:
            end_term = start_term
        if start_term.first > end_term.first:
            self.error(row, col + 1, ERROR_END_TERM_BEFORE_START)
            return []
        return [term for term in year.values()
                if term.first >= start_term.first and
                   term.first <= end_term.first]

    def validateSectionsByTerm(self, data, terms, row, col):
        sections_by_term = []
        for term in terms:
            sc = ISectionContainer(term)
            if data['__name__'] not in sc:
                self.error(row, col, ERROR_TERM_SECTION_ID)
                return []
            sections_by_term.append(sc[data['__name__']])
        return sections_by_term

    def createSection(self, data, term, courses):
        sc = ISectionContainer(term)
        if data['__name__'] in sc:
            section = sc[data['__name__']]
            section.title = data['title']
            section.description = data['description']
            for course in section.courses:
                section.courses.remove(course)
            for resource in section.resources:
                section.resources.remove(resource)
            for student in section.members:
                section.members.remove(student)
            for teacher in section.instructors:
                section.instructors.remove(teacher)
        else:
            section = Section(data['title'], data['description'])
            section.__name__ = data['__name__']
            sc[section.__name__] = section
        for course in courses:
            section.courses.add(removeSecurityProxy(course))
        return section

    def createSectionsByTerm(self, data, terms, courses):
        sections_by_term = []
        previous_section = None
        for term in terms:
            section = self.createSection(data, term, courses)
            if previous_section is not None:
                previous_section.next = section
            previous_section = section
            sections_by_term.append(section)
        return sections_by_term


class SchoolYearImporter(ImporterBase):

    sheet_name = 'School Years'

    def createSchoolYear(self, data):
        syc = ISchoolYearContainer(self.context)
        name = data['__name__']
        if name in syc:
            sy = syc[name]
            sy.first = data['first']
            sy.last = data['last']
        else:
            sy = SchoolYear(data['title'], data['first'], data['last'])
            sy.__name__ = name
        return sy

    def addSchoolYear(self, sy, data):
        syc = ISchoolYearContainer(self.context)
        if sy.__name__ in syc:
            return
        if sy.__name__ is None:
            sy.__name__ = SimpleNameChooser(syc).chooseName('', sy)
        syc[sy.__name__] = sy

    def testOverlap(self, name, date):
        for sy in ISchoolYearContainer(self.context).values():
            if name == sy.__name__:
                continue
            if date >= sy.first and date <= sy.last:
                return True
        return False

    def process(self):
        sh = self.sheet
        for row in range(1, sh.nrows):
            num_errors = len(self.errors)
            data = {}
            data['__name__'] = self.getRequiredTextFromCell(sh, row, 0)
            data['title'] = self.getRequiredTextFromCell(sh, row, 1)
            data['first'] = self.getDateFromCell(sh, row, 2)
            data['last'] = self.getDateFromCell(sh, row, 3)
            if data['last'] < data['first']:
                self.error(row, 3, ERROR_END_BEFORE_START)
            elif self.testOverlap(data['__name__'], data['first']):
                self.error(row, 2, ERROR_START_OVERLAP)
            elif self.testOverlap(data['__name__'], data['last']):
                self.error(row, 3, ERROR_END_OVERLAP)
            if num_errors == len(self.errors):
                sy = self.createSchoolYear(data)
                self.addSchoolYear(sy, data)


class TermImporter(ImporterBase):

    sheet_name = 'Terms'

    def createTerm(self, data):
        syc = ISchoolYearContainer(self.context)
        sy = syc[data['school_year']]
        name = data['__name__']
        if name in sy:
            term = sy[name]
            term.first = data['first']
            term.last = data['last']
        else:
            term = Term(data['title'], data['first'], data['last'])
            term.__name__ = data['__name__']
        term.addWeekdays(*range(7))
        return term

    def addTerm(self, term, data):
        syc = ISchoolYearContainer(self.context)
        sy = syc[data['school_year']]
        if term.__name__ in sy:
            return
        if term.__name__ is None:
            term.__name__ = SimpleNameChooser(sy).chooseName('', term)
        sy[term.__name__] = term

    def testBeforeYearStart(self, sy, date):
        return date < ISchoolYearContainer(self.context)[sy].first

    def testAfterYearEnd(self, sy, date):
        return date > ISchoolYearContainer(self.context)[sy].last

    def testOverlap(self, sy, name, date):
        for trm in ISchoolYearContainer(self.context)[sy].values():
            if trm.__name__ == name:
                continue
            if date >= trm.first and date <= trm.last:
                return True
        return False

    def process(self):
        sh = self.sheet

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            num_errors = len(self.errors)
            data = {}
            data['school_year'] = self.getRequiredTextFromCell(sh, row, 0)
            data['__name__'] = self.getRequiredTextFromCell(sh, row, 1)
            data['title'] = self.getRequiredTextFromCell(sh, row, 2)
            data['first'] = self.getDateFromCell(sh, row, 3)
            data['last'] = self.getDateFromCell(sh, row, 4)
            if num_errors < len(self.errors):
                continue

            if data['school_year'] not in ISchoolYearContainer(self.context):
                self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
                continue

            if data['last'] < data['first']:
                self.error(row, 4, ERROR_END_BEFORE_START)
            elif self.testBeforeYearStart(data['school_year'], data['first']):
                self.error(row, 3, ERROR_START_BEFORE_YEAR_START)
            elif self.testAfterYearEnd(data['school_year'], data['last']):
                self.error(row, 4, ERROR_END_AFTER_YEAR_END)
            elif self.testOverlap(data['school_year'], data['__name__'],
                                  data['first']):
                self.error(row, 3, ERROR_START_OVERLAP_TERM)
            elif self.testOverlap(data['school_year'], data['__name__'],
                                  data['last']):
                self.error(row, 4, ERROR_END_OVERLAP_TERM)

            if num_errors == len(self.errors):
                term = self.createTerm(data)
                self.addTerm(term, data)

        row += 1
        if self.getCellValue(sh, row, 0, '') == 'Holidays':
            for row in range(row + 1, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break
                start = self.getDateFromCell(sh, row, 0)
                end = self.getDateFromCell(sh, row, 1)
                if not start or not end:
                    continue
                elif end < start:
                    self.error(row, 4, ERROR_END_BEFORE_START)
                    continue

                holiday_region = DateRange(start, end)
                for day in holiday_region:
                    for sy in ISchoolYearContainer(self.context).values():
                        for term in sy.values():
                            if day in term:
                                term.remove(day)

        row += 1
        if self.getCellValue(sh, row, 0, '') == 'Weekends':
            row += 2
            for col in range(7):
                if sh.cell_value(rowx=row, colx=col) != '':
                    for sy in ISchoolYearContainer(self.context).values():
                        for term in sy.values():
                            term.removeWeekdays(col)


class SchoolTimetableImporter(ImporterBase):

    sheet_name = 'School Timetables'

    dows = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday']

    day_templates = (
        ('calendar_days', CalendarDayTemplates),
        ('week_days', WeekDayTemplates),
        ('school_days', SchoolDayTemplates),
        )

    def createSchoolTimetable(self, data):
        syc = ISchoolYearContainer(self.context)
        schoolyear = syc[data['school_year']]

        app = ISchoolToolApplication(None)
        tzname = IApplicationPreferences(app).timezone
        timetable = Timetable(schoolyear.first, schoolyear.last,
                              title=data['title'], timezone=tzname)

        factories = dict(self.day_templates)

        container = ITimetableContainer(schoolyear)

        if data['__name__'] in container:
            del container[data['__name__']]
        timetable.__name__ = data['__name__']

        container[timetable.__name__] = timetable

        timetable.periods, event = containedEvent(
                factories[data['period_templates']](), timetable, 'periods')
        notify(event)
        timetable.periods.initTemplates()

        timetable.time_slots, event = containedEvent(
                factories[data['time_templates']](), timetable, 'time_slots')
        notify(event)
        timetable.time_slots.initTemplates()

        name_chooser = INameChooser(timetable.periods.templates)
        for entry in data['periods']:
            day_id = entry['id']
            day_title = day_id
            if data['period_templates'] == 'week_days':
                day_title = self.dows[int(day_id)]
            day = DayTemplate(day_title)
            if data['period_templates'] == 'week_days':
                name = day_id
            else:
                name = name_chooser.chooseName('', day)
            timetable.periods.templates[name] = day
            p_chooser = INameChooser(day)
            for period_entry in entry['periods']:
                period = Period(title=period_entry['title'],
                                activity_type=period_entry['activity'] or None)
                p_name = p_chooser.chooseName('', period)
                day[p_name] = period

        name_chooser = INameChooser(timetable.time_slots.templates)
        for entry in data['time_slots']:
            day_id = entry['id']
            day_title = day_id
            if data['time_templates'] == 'week_days':
                day_title = self.dows[int(day_id)]
            day = DayTemplate(day_title)
            if data['time_templates'] == 'week_days':
                name = day_id
            else:
                name = name_chooser.chooseName('', day)
            timetable.time_slots.templates[name] = day
            ts_chooser = INameChooser(day)
            for ts_entry in entry['time_slots']:
                time_slot = TimeSlot(
                    ts_entry['starts'], ts_entry['duration'],
                    activity_type=ts_entry['activity'] or None)
                ts_name = ts_chooser.chooseName('', time_slot)
                day[ts_name] = time_slot

    def getWeeklyDayId(self, sh, row, col):
        value, found = self.getCellAndFound(sh, row, col)
        if not found:
            self.error(row, col, ERROR_WEEKLY_DAY_ID)
            return None

        if isinstance(value, float):
            if int(value) == value:
                value = int(value)
        else:
            try:
                value = self.dows.index(value)
            except ValueError:
                self.errors.append("Unrecognised day id %s" % value)

            if isinstance(value, float):
                if int(value) != value:
                    self.error(row, col, ERROR_NOT_INT)
                else:
                    value = int(value)
        return unicode(value)

    def import_school_timetable(self, sh, row):
        num_errors = len(self.errors)
        data = {}
        data['title'] = self.getRequiredTextFromCell(sh, row, 1)
        data['__name__'] = self.getRequiredTextFromCell(sh, row+1, 1)
        data['school_year'] = self.getRequiredTextFromCell(sh, row+2, 1)
        data['period_templates'] = self.getRequiredTextFromCell(sh, row+3, 1)
        data['time_templates'] = self.getRequiredTextFromCell(sh, row+4, 1)
        if num_errors < len(self.errors):
            return

        num_errors = len(self.errors)
        if data['school_year'] not in ISchoolYearContainer(self.context):
            self.error(row + 2, 1, ERROR_INVALID_SCHOOL_YEAR)

        factories = dict(self.day_templates)
        if data['period_templates'] not in factories:
            self.error(row + 3, 1, ERROR_TIMETABLE_MODEL)
        if data['time_templates'] not in factories:
            self.error(row + 4, 1, ERROR_TIMETABLE_MODEL)

        if num_errors < len(self.errors):
            return

        num_errors = len(self.errors)
        row += 5

        row += 1
        if self.getCellValue(sh, row, 0, '').lower() == 'days':
            data['periods'] = []
            row += 1

            while row < sh.nrows:
                if sh.cell_value(rowx=row, colx=0) == '':
                    break

                if data['period_templates'] == 'week_days':
                    day_id = self.getWeeklyDayId(sh, row, 0)
                else:
                    day_id = self.getRequiredTextFromCell(sh, row, 0)

                if day_id in [day['id'] for day in data['periods']]:
                    self.error(row, 0, ERROR_DUPLICATE_DAY_ID)

                periods = []
                col = 1
                while True:
                    cell = self.getCellValue(sh, row, col, default='')
                    if cell == '':
                        break
                    activity = sh.cell_value(rowx=row+1, colx=col)
                    if cell in periods:
                        self.error(row, col, ERROR_DUPLICATE_PERIOD)
                    else:
                        periods.append({'title': cell,
                                        'activity': activity})
                    col += 1
                row += 2

                data['periods'].append({
                        'id': day_id,
                        'periods': periods,
                        })
        else:
            self.errors.append(format_message(
                ERROR_HAS_NO_DAYS,
                mapping={'title': data['title'], 'row': row + 1}
                ))

        row += 1
        if self.getCellValue(sh, row, 0, '').lower() == 'time schedule':
            data['time_slots'] = []
            row += 1

            while row < sh.nrows:
                if sh.cell_value(rowx=row, colx=0) == '':
                    break

                if data['time_templates'] == 'week_days':
                    day_id = self.getWeeklyDayId(sh, row, 0)
                else:
                    day_id = self.getRequiredTextFromCell(sh, row, 0)

                if day_id in [day['id'] for day in data['time_slots']]:
                    self.error(row, 0, ERROR_DUPLICATE_DAY_ID)

                time_slots = []
                col = 1
                while True:
                    cell = self.getCellValue(sh, row, col, default='')
                    if cell == '':
                        break
                    try:
                        starts, duration = parse_time_range(cell)
                    except:
                        self.error(row, col, ERROR_TIME_RANGE)
                        continue
                    activity = self.getCellValue(sh, row+1, col, default='')
                    time_slots.append({
                            'starts': starts,
                            'duration': duration,
                            'activity': activity,
                            })
                    col += 1
                data['time_slots'].append({'id': day_id, 'time_slots': time_slots})
                row += 2
        else:
            self.errors.append(format_message(
                ERROR_HAS_NO_DAY_TEMPLATES,
                mapping={'title': data['title'], 'row': row + 1}
                ))
        if num_errors < len(self.errors):
            return

        if not self.errors:
            self.createSchoolTimetable(data)

    def process(self):
        sh = self.sheet
        for row in range(0, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == 'School Timetable':
                self.import_school_timetable(sh, row)


class ResourceImporter(ImporterBase):

    sheet_name = 'Resources'

    def createResource(self, data):
        res_types = {
            'Location': Location,
            'Equipment': Equipment,
            'Resource': Resource,
            }
        res_factory = res_types[data['type']]
        resource = res_factory(data['title'])
        resource.__name__ = data['__name__']
        resource.description = data['description']
        return resource

    def addResource(self, resource, data):
        rc = self.context['resources']
        if resource.__name__ in rc:
            resource = rc[resource.__name__]
            resource.title = data['title']
            resource.description = data['description']
        else:
            if not resource.__name__:
                resource.__name__ = INameChooser(rc).chooseName('', resource)
            rc[resource.__name__] = resource

    def process(self):
        sh = self.sheet
        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break
            num_errors = len(self.errors)
            data = {}
            data['__name__'] = self.getRequiredTextFromCell(sh, row, 0)
            data['type'] = self.getRequiredTextFromCell(sh, row, 1)
            data['title'] = self.getRequiredTextFromCell(sh, row, 2)
            data['description'] = self.getTextFromCell(sh, row, 3)
            if num_errors < len(self.errors):
                continue
            if data['type'] not in ['Location', 'Equipment', 'Resource']:
                self.error(row, 1, ERROR_RESOURCE_TYPE)
                continue
            resource = self.createResource(data)
            self.addResource(resource, data)


class PersonImporter(ImporterBase):

    sheet_name = 'Persons'
    group_name = None

    def applyData(self, person, data):
        person.prefix = data['prefix']
        person.first_name = data['first_name']
        person.middle_name = data['middle_name']
        person.last_name = data['last_name']
        person.suffix = data['suffix']
        person.preferred_name = data['preferred_name']
        person.birth_date = data['birth_date']
        person.gender = data['gender']
        if data['password']:
            person.setPassword(data['password'])

    def createPerson(self, data):
        person = BasicPerson(data['__name__'],
                             data['first_name'],
                             data['last_name'])
        self.applyData(person, data)
        return person

    def addPerson(self, person, data):
        pc = self.context['persons']
        if person.username in pc:
            person = pc[person.username]
            self.applyData(person, data)
        else:
            pc[person.username] = person

    def process(self):
        sh = self.sheet

        fields = IDemographicsFields(ISchoolToolApplication(None))
        if self.group_name:
            num_errors = len(self.errors)
            year_id = self.getRequiredTextFromCell(sh, 0, 1)
            if num_errors != len(self.errors):
                return
            syc = ISchoolYearContainer(self.context)
            if year_id not in syc:
                self.error(0, 1, ERROR_INVALID_SCHOOL_YEAR)
                return
            year = syc[year_id]
            if self.group_name == 'students':
                group = self.ensure_students_group(year)
            elif self.group_name == 'teachers':
                group = self.ensure_teachers_group(year)
            first_row = 3
            fields = fields.filter_key(self.group_name)
        else:
            group = None
            first_row = 1
            fields = list(fields.values())

        for row in range(first_row, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            num_errors = len(self.errors)
            data = {}
            data['__name__'] = self.getRequiredTextFromCell(sh, row, 0)
            data['prefix'] = self.getTextFromCell(sh, row, 1)
            data['first_name'] = self.getRequiredTextFromCell(sh, row, 2)
            data['middle_name'] = self.getTextFromCell(sh, row, 3)
            data['last_name'] = self.getRequiredTextFromCell(sh, row, 4)
            data['suffix'] = self.getTextFromCell(sh, row, 5)
            data['preferred_name'] = self.getTextFromCell(sh, row, 6)
            data['birth_date'] = self.getDateFromCell(sh, row, 7, default=None)
            data['gender'] = self.getTextFromCell(sh, row, 8)
            if data['gender'] == '':
                data['gender'] = None
            elif data['gender'] not in ['male', 'female']:
                self.error(row, 8, ERROR_INVALID_GENDER)
            data['password'] = self.getTextFromCell(sh, row, 9)

            # XXX: this has to be fixed
            # XXX: SchoolTool should handle UTF-8
            try:
                str(data['__name__'])
            except UnicodeEncodeError:
                self.error(row, 0, ERROR_UNICODE_CONVERSION)

            if num_errors == len(self.errors):
                person = self.createPerson(data)
            else:
                person = BasicPerson('name', 'first_name', 'last_name')

            demographics = IDemographics(person)
            for n, field in enumerate(fields):
                if field.required:
                    if isinstance(field, DateFieldDescription):
                        value = self.getDateFromCell(sh, row, n + 10)
                    elif isinstance(field, BoolFieldDescription):
                        value = self.getRequiredBoolFromCell(sh, row, n + 10)
                    else:
                        value = self.getRequiredTextFromCell(sh, row, n + 10)
                else:
                    if isinstance(field, DateFieldDescription):
                        value = self.getDateFromCell(sh, row, n + 10,
                                                     default=None)
                    elif isinstance(field, BoolFieldDescription):
                        value = self.getBoolFromCell(sh, row, n + 10)
                    else:
                        value = self.getTextFromCell(sh, row, n + 10)
                    if value == '':
                        value = None
                demographics[field.name] = value

            if num_errors == len(self.errors):
                self.addPerson(person, data)
                if group and person not in group.members:
                    group.members.add(person)


class TeacherImporter(PersonImporter):

    sheet_name = 'Teachers'
    group_name = 'teachers'


class StudentImporter(PersonImporter):

    sheet_name = 'Students'
    group_name = 'students'


class ContactPersonImporter(ImporterBase):

    sheet_name = 'Contact Persons'

    def applyData(self, contact, data):
        if data['__name__'] not in ISchoolToolApplication(None)['persons']:
            contact.prefix = data['prefix']
            contact.first_name = data['first_name']
            contact.middle_name = data['middle_name']
            contact.last_name = data['last_name']
            contact.suffix = data['suffix']
        contact.address_line_1 = data['address_line_1']
        contact.address_line_2 = data['address_line_2']
        contact.city = data['city']
        contact.state = data['state']
        contact.country = data['country']
        contact.postal_code = data['postal_code']
        contact.home_phone = data['home_phone']
        contact.work_phone = data['work_phone']
        contact.mobile_phone = data['mobile_phone']
        contact.email = data['email']
        contact.language = data['language']

    def establishContact(self, data):
        app = ISchoolToolApplication(None)
        persons = app['persons']
        contacts = IContactContainer(app)
        name = data['__name__']
        if name in persons:
            person = persons[name]
            contact = IContact(person)
            self.applyData(contact, data)
        elif name in contacts:
            contact = contacts[name]
            self.applyData(contact, data)
        else:
            contact = Contact()
            self.applyData(contact, data)
            contacts[name] = contact

    def process(self):
        sh = self.sheet
        persons = ISchoolToolApplication(None)['persons']
        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            num_errors = len(self.errors)
            data = {}

            data['__name__'] = self.getRequiredTextFromCell(sh, row, 0)
            self.validateUnicode(data['__name__'], row, 0)
            if num_errors == len(self.errors):
                if data['__name__'] not in persons:
                    data['prefix'] = self.getTextFromCell(sh, row, 1)
                    data['first_name'] = self.getRequiredTextFromCell(sh, row, 2)
                    data['middle_name'] = self.getTextFromCell(sh, row, 3)
                    data['last_name'] = self.getRequiredTextFromCell(sh, row, 4)
                    data['suffix'] = self.getTextFromCell(sh, row, 5)
                else:
                    for index in range(5):
                        value, found = self.getCellAndFound(sh, row, index + 1)
                        if value:
                            self.error(row, index + 1,
                                       ERROR_UNWANTED_CONTACT_DATA)

            data['address_line_1'] = self.getTextFromCell(sh, row, 6)
            data['address_line_2'] = self.getTextFromCell(sh, row, 7)
            data['city'] = self.getTextFromCell(sh, row, 8)
            data['state'] = self.getTextFromCell(sh, row, 9)
            data['country'] = self.getTextFromCell(sh, row, 10)
            data['postal_code'] = self.getTextFromCell(sh, row, 11)
            data['home_phone'] = self.getTextFromCell(sh, row, 12)
            data['work_phone'] = self.getTextFromCell(sh, row, 13)
            data['mobile_phone'] = self.getTextFromCell(sh, row, 14)
            data['email'] = self.getTextFromCell(sh, row, 15)
            data['language'] = self.getTextFromCell(sh, row, 16)

            if num_errors == len(self.errors):
                self.establishContact(data)


class ContactRelationshipImporter(ImporterBase):

    sheet_name = 'Contact Relationships'

    def process(self):
        sh = self.sheet
        app = ISchoolToolApplication(None)
        persons = app['persons']
        contacts = IContactContainer(app)
        vocab = IContactPersonInfo['relationship'].vocabulary
        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            num_errors = len(self.errors)
            data = {}

            data['__name__'] = self.getRequiredTextFromCell(sh, row, 0)
            self.validateUnicode(data['__name__'], row, 0)
            if num_errors == len(self.errors):
                if data['__name__'] not in persons:
                    self.error(row, 0, ERROR_INVALID_PERSON_ID)
                else:
                    person = persons[data['__name__']]

            current_errors = len(self.errors)
            data['contact_name'] = self.getRequiredTextFromCell(sh, row, 1)
            name = data['contact_name']
            if current_errors == len(self.errors):
                self.validateUnicode(name, row, 1)
            if current_errors == len(self.errors):
                if name in persons:
                    contact = IContact(persons[name])
                elif name in contacts:
                    contact = contacts[name]
                else:
                    self.error(row, 1, ERROR_INVALID_CONTACT_ID)

            data['relationship'] = self.getTextFromCell(sh, row, 2)
            relationship = data['relationship']
            if relationship and relationship not in vocab:
                self.error(row, 2, ERROR_CONTACT_RELATIONSHIP)

            if num_errors == len(self.errors):
                info = ContactPersonInfo()
                info.__parent__ = person
                if relationship:
                    info.relationship = relationship
                if contact not in IContactable(person).contacts:
                    IContactable(person).contacts.add(contact, info)


class CourseImporter(ImporterBase):

    sheet_name = 'Courses'

    def createCourse(self, data):
        syc = ISchoolYearContainer(self.context)
        cc = ICourseContainer(syc[data['school_year']])
        name = data['__name__']
        if name in cc:
            course = cc[name]
            course.title = data['title']
            course.description = data['description']
        else:
            course = Course(data['title'], data['description'])
            course.__name__ = data['__name__']
        course.course_id = data['course_id'] or None
        course.government_id = data['government_id'] or None
        course.credits = data['credits'] or None
        return course

    def addCourse(self, course, data):
        syc = ISchoolYearContainer(self.context)
        cc = ICourseContainer(syc[data['school_year']])
        if course.__name__ in cc:
            return
        if course.__name__ is None:
            course.__name__ = SimpleNameChooser(cc).chooseName('', course)
        cc[course.__name__] = course

    def process(self):
        sh = self.sheet
        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break
            num_errors = len(self.errors)
            data = {}
            data['school_year'] = self.getRequiredTextFromCell(sh, row, 0)
            data['__name__'] = self.getRequiredTextFromCell(sh, row, 1)
            data['title'] = self.getRequiredTextFromCell(sh, row, 2)
            data['description'] = self.getTextFromCell(sh, row, 3)
            data['course_id'] = self.getTextFromCell(sh, row, 4)
            data['government_id'] = self.getTextFromCell(sh, row, 5)
            data['credits'] = self.getTextFromCell(sh, row, 6)
            if num_errors < len(self.errors):
                continue
            if data['school_year'] not in ISchoolYearContainer(self.context):
                self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
            try:
                if data['credits']:
                    data['credits'] = Decimal(data['credits'])
            except InvalidOperation:
                self.error(row, 6, ERROR_INVALID_COURSE_CREDITS)
            if num_errors < len(self.errors):
                continue
            course = self.createCourse(data)
            self.addCourse(course, data)


class SectionImporter(ImporterBase):

    def createSection(self, data, year, term):
        sc = ISectionContainer(term)
        if data['__name__'] in sc:
            section = sc[data['__name__']]
            section.title = data['title']
            section.description = data['description']
        else:
            section = Section(data['title'], data['description'])
            section.__name__ = data['__name__']
        return section

    def addSection(self, section, data, year, term):
        sc = ISectionContainer(term)
        if section.__name__ is None:
            section.__name__ = SimpleNameChooser(sc).chooseName('', section)

        if section.__name__ not in sc:
            sc[section.__name__] = section

        if data['link']:
            previous_term = getPreviousTerm(term)
            if previous_term is not None:
                previous_sections = ISectionContainer(previous_term)
                if section.__name__ in previous_sections:
                    previous_sections[section.__name__].next = section
            next_term = getNextTerm(term)
            if next_term is not None:
                next_sections = ISectionContainer(next_term)
                if section.__name__ in next_sections:
                    next_sections[section.__name__].previous = section

    def import_timetable(self, sh, row, section):
        timetables = ITimetableContainer(ISchoolYear(section))

        timetable_id = self.getRequiredTextFromCell(sh, row, 1)
        if timetable_id not in timetables:
            self.error(row, 0, ERROR_INVALID_SCHEMA_ID)
            return row
        timetable = timetables[timetable_id]

        schedules = IScheduleContainer(section)

        term = ITerm(section)
        schedule = SelectedPeriodsSchedule(
            timetable, term.first, term.last,
            title=timetable.title, timezone=timetable.timezone)
        row += 1

        collapse_periods = self.getTextFromCell(sh, row, 1, 'no')
        schedule.consecutive_periods_as_one = bool(
            collapse_periods.lower() == 'yes')

        row += 2

        for row in range(row, sh.nrows):

            if sh.cell_value(rowx=row, colx=0) == '':
                break
            num_errors = len(self.errors)
            day_title = self.getRequiredTextFromCell(sh, row, 0)
            period_title = self.getRequiredTextFromCell(sh, row, 1)
            if num_errors < len(self.errors):
                continue

            day = None
            for tt_day in timetable.periods.templates.values():
                if tt_day.title == day_title:
                    day = tt_day
                    break
            if day is None:
                self.error(row, 0, ERROR_INVALID_DAY_ID)
                continue

            period = None
            for tt_period in day.values():
                if tt_period.title == period_title:
                    period = tt_period
            if period is None:
                self.error(row, 1, ERROR_INVALID_PERIOD_ID)
                continue

            schedule.addPeriod(period)

            if num_errors < len(self.errors):
                continue

        s_chooser = INameChooser(schedules)
        name = s_chooser.chooseName('', schedule)
        schedules[name] = schedule

        return row

    def import_timetables(self, sh, row, section):
        for row in range(row, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == 'School Timetable':
                self.import_timetable(sh, row, section)
            elif sh.cell_value(rowx=row, colx=0) == '':
                break
        return row

    def import_section(self, sh, row, year, term):
        data = {}
        data['title'] = self.getRequiredTextFromCell(sh, row, 1)
        data['__name__'] = self.getRequiredTextFromCell(sh, row+1, 1)
        link = self.getTextFromCell(sh, row+1, 3)
        data['link'] = link.lower() in ['y', 'yes']
        data['description'] = self.getTextFromCell(sh, row+2, 1)

        section = self.createSection(data, year, term)
        self.addSection(section, data, year, term)
        courses = ICourseContainer(section)

        students = self.ensure_students_group(year)
        teachers = self.ensure_teachers_group(year)

        row += 4
        if self.getCellValue(sh, row, 0, '') == 'Courses':
            row += 1
            for row in range(row, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break
                num_errors = len(self.errors)

                course_id = self.getRequiredTextFromCell(sh, row, 0)
                if num_errors < len(self.errors):
                    continue
                if course_id not in courses:
                    self.error(row, 0, ERROR_INVALID_COURSE_ID)
                    continue
                course = courses[course_id]

                if course not in section.courses:
                    section.courses.add(removeSecurityProxy(course))
            row += 1

        if not list(section.courses):
            self.errors.append(format_message(
                ERROR_HAS_NO_COURSES,
                mapping={'title': data['title'], 'row': row + 1}
                ))
            return

        persons = self.context['persons']
        if self.getCellValue(sh, row, 0, '') == 'Students':
            row += 1
            for row in range(row, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break
                num_errors = len(self.errors)

                username = self.getRequiredTextFromCell(sh, row, 0)
                if num_errors < len(self.errors):
                    continue
                if username not in persons:
                    self.error(row, 0, ERROR_INVALID_PERSON_ID)
                    continue
                member = persons[username]

                if member not in section.members:
                    section.members.add(removeSecurityProxy(member))
                if member not in students.members:
                    students.members.add(removeSecurityProxy(member))
            row += 1

        if self.getCellValue(sh, row, 0, '') == 'Instructors':
            row += 1
            for row in range(row, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break
                num_errors = len(self.errors)

                username = self.getRequiredTextFromCell(sh, row, 0)
                if num_errors < len(self.errors):
                    continue
                if username not in persons:
                    self.error(row, 0, ERROR_INVALID_PERSON_ID)
                    continue
                instructor = persons[username]

                if instructor not in section.instructors:
                    section.instructors.add(removeSecurityProxy(instructor))
                if instructor not in teachers.members:
                    teachers.members.add(removeSecurityProxy(instructor))
            row += 1

        if self.getCellValue(sh, row, 0, '') == 'School Timetable':
            self.import_timetables(sh, row, section)

    def process(self):
        app = ISchoolToolApplication(None)
        schoolyears = ISchoolYearContainer(app)
        for self.sheet_name in self.sheet_names:
            sheet = self.wb.sheet_by_name(self.sheet_name)

            num_errors = len(self.errors)
            year_id = self.getRequiredTextFromCell(sheet, 0, 1)
            term_id = self.getRequiredTextFromCell(sheet, 0, 3)
            if num_errors < len(self.errors):
                continue

            if year_id not in schoolyears:
                self.error(0, 1, ERROR_INVALID_SCHOOL_YEAR)
                continue
            year = schoolyears[year_id]

            if term_id not in year:
                self.error(0, 3, ERROR_INVALID_TERM_ID)
                continue
            term = year[term_id]

            for row in range(2, sheet.nrows):
                if sheet.cell_value(rowx=row, colx=0) == 'Section Title':
                    self.import_section(sheet, row, year, term)

    def import_data(self, wb):
        self.wb = wb
        self.sheet_names = []
        for sheet_name in self.wb.sheet_names():
            if (sheet_name.startswith('Section') and sheet_name not in
                ['Sections', 'SectionTimetables', 'SectionEnrollment']):
                self.sheet_names.append(sheet_name)
        if self.sheet_names:
            self.process()


class SectionsImporter(ImporterBase):

    sheet_name = 'Sections'

    def process(self):
        sh = self.sheet
        schoolyears = ISchoolYearContainer(self.context)
        persons = self.context['persons']
        resources = self.context['resources']

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            data = {}
            num_errors = len(self.errors)
            data['year'] = self.getRequiredIdFromCell(sh, row, 0)
            data['courses'] = self.getRequiredIdsFromCell(sh, row, 1)
            data['start_term'] = self.getRequiredIdFromCell(sh, row, 2)
            data['end_term'] = self.getIdFromCell(sh, row, 3)
            data['__name__'] = self.getRequiredIdFromCell(sh, row, 4)
            data['title'] = self.getRequiredTextFromCell(sh, row, 5)
            data['description'] = self.getTextFromCell(sh, row, 6)
            data['instructors'] = self.getIdsFromCell(sh, row, 7)
            data['resources'] = self.getIdsFromCell(sh, row, 8)
            if num_errors < len(self.errors):
                continue

            if data['year'] not in schoolyears:
                self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
                continue
            year = schoolyears[data['year']]
            teachers = self.ensure_teachers_group(year)
            course_container = ICourseContainer(year)

            num_errors = len(self.errors)
            courses = []
            for course_id in data['courses']:
                if course_id not in course_container:
                    self.error(row, 1, ERROR_INVALID_COURSE_ID)
                else:
                    course = course_container[course_id]
                    courses.append(removeSecurityProxy(course))
            if num_errors < len(self.errors):
                continue

            terms = self.validateStartEndTerms(year, data, row, 2)
            if not terms:
                continue

            sections = self.createSectionsByTerm(data, terms, courses)

            for person_id in data['instructors']:
                if person_id not in persons:
                    self.error(row, 6, ERROR_INVALID_PERSON_ID_LIST)
                    break
                else:
                    teacher = persons[person_id]
                    for section in sections:
                        if teacher not in section.instructors:
                            section.instructors.add(removeSecurityProxy(teacher))
                        if teacher not in teachers.members:
                            teachers.members.add(removeSecurityProxy(teacher))

            for resource_id in data['resources']:
                if resource_id not in resources:
                    self.error(row, 8, ERROR_INVALID_RESOURCE_ID_LIST)
                    break
                else:
                    resource = resources[resource_id]
                    for section in sections:
                        if resource not in section.resources:
                            section.resources.add(removeSecurityProxy(resource))


class SectionEnrollmentImporter(ImporterBase):

    sheet_name = 'SectionEnrollment'

    def process(self):
        sh = self.sheet
        schoolyears = ISchoolYearContainer(self.context)
        persons = self.context['persons']

        for row in range(1, sh.nrows):
            data = {}
            num_errors = len(self.errors)
            data['year'] = self.getRequiredIdFromCell(sh, row, 0)
            data['start_term'] = self.getRequiredIdFromCell(sh, row, 1)
            data['end_term'] = self.getIdFromCell(sh, row, 2)
            data['__name__'] = self.getRequiredIdFromCell(sh, row, 3)
            data['student'] = self.getRequiredIdFromCell(sh, row, 4)
            if num_errors < len(self.errors):
                continue

            if data['year'] not in schoolyears:
                self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
                continue
            year = schoolyears[data['year']]
            students = self.ensure_students_group(year)

            terms = self.validateStartEndTerms(year, data, row, 1)
            if not terms:
                continue

            sections = self.validateSectionsByTerm(data, terms, row, 3)
            if not sections:
                continue

            person_id = data['student']
            if person_id not in persons:
                self.error(row, 4, ERROR_INVALID_PERSON_ID)
            else:
                student = persons[person_id]
                for section in sections:
                    if student not in section.members:
                        section.members.add(removeSecurityProxy(student))
                    if student not in students.members:
                        students.members.add(removeSecurityProxy(student))


class SectionTimetablesImporter(ImporterBase):

    sheet_name = 'SectionTimetables'

    def process(self):
        sh = self.sheet
        schoolyears = ISchoolYearContainer(self.context)
        resources = self.context['resources']
        year = term = section = timetable = schedule = None

        for row in range(1, sh.nrows):
            data = {}
            num_errors = len(self.errors)
            data['year'] = self.getRequiredIdFromCell(sh, row, 0)
            data['start_term'] = self.getRequiredIdFromCell(sh, row, 1)
            data['end_term'] = self.getIdFromCell(sh, row, 2)
            data['__name__'] = self.getRequiredIdFromCell(sh, row, 3)
            data['timetable'] = self.getRequiredTextFromCell(sh, row, 4)
            data['consecutive'] = self.getBoolFromCell(sh, row, 5)
            data['day'] = self.getRequiredTextFromCell(sh, row, 6)
            data['period'] = self.getRequiredTextFromCell(sh, row, 7)
            if num_errors < len(self.errors):
                continue

            if data['year'] not in schoolyears:
                self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
                continue
            year = schoolyears[data['year']]
            timetables = ITimetableContainer(year)

            terms = self.validateStartEndTerms(year, data, row, 1)
            if not terms:
                continue

            sections = self.validateSectionsByTerm(data, terms, row, 3)
            if not sections:
                continue

            if data['timetable'] not in timetables:
                self.error(row, 4, ERROR_INVALID_SCHEMA_ID)
                continue
            timetable = timetables[data['timetable']]

            for section in sections:
                term = ITerm(section)
                schedules = IScheduleContainer(section)

                for schedule in schedules.values():
                    if schedule.timetable == timetable:
                        break
                else:
                    schedule = SelectedPeriodsSchedule(
                        timetable, term.first, term.last,
                        title=timetable.title, timezone=timetable.timezone)
                    s_chooser = INameChooser(schedules)
                    name = s_chooser.chooseName('', schedule)
                    schedules[name] = schedule

                schedule.consecutive_periods_as_one = bool(data['consecutive'])

                for tt_day in timetable.periods.templates.values():
                    if tt_day.title == data['day']:
                        day = tt_day
                        break
                else:
                    self.error(row, 6, ERROR_INVALID_DAY_ID)
                    break

                for tt_period in day.values():
                    if tt_period.title == data['period']:
                        period = tt_period
                        break
                else:
                    self.error(row, 7, ERROR_INVALID_PERIOD_ID)
                    break
                schedule.addPeriod(period)


class FlatSectionsTableImporter(ImporterBase):

    sheet_name = 'FlatSectionsTable'

    def createSection(self, data, year, term, courses):
        sc = ISectionContainer(term)
        if data['__name__'] in sc:
            section = sc[data['__name__']]
            section.title = data['title']
            section.description = data['description']
            for course in section.courses:
                section.courses.remove(course)
            for resource in section.resources:
                section.resources.remove(resource)
            for student in section.members:
                section.members.remove(student)
            for teacher in section.instructors:
                section.instructors.remove(teacher)
        else:
            section = Section(data['title'], data['description'])
            section.__name__ = data['__name__']
            sc[section.__name__] = section
        for course in courses:
            section.courses.add(course)
        return section

    def import_timetable_row(self, row, data, section, timetable, schedule):
        term = ITerm(section)
        year = ISchoolYear(term)
        if data['timetable']:
            timetables = ITimetableContainer(year)
            timetable_id = data['timetable']
            if timetable_id not in timetables:
                self.error(row, 11, ERROR_INVALID_SCHEMA_ID)
                return None, None
            else:
                timetable = timetables[timetable_id]

                schedule = SelectedPeriodsSchedule(
                    timetable, term.first, term.last,
                    title=timetable.title, timezone=timetable.timezone)
                schedule.consecutive_periods_as_one = data['consecutive']

                schedules = IScheduleContainer(section)
                s_chooser = INameChooser(schedules)
                name = s_chooser.chooseName('', schedule)
                schedules[name] = schedule

        day = None
        if data['day']:
            if timetable is None:
                self.error(row, 13, ERROR_NO_TIMETABLE_DEFINED)
                return timetable, schedule
            day_title = data['day']
            for tt_day in timetable.periods.templates.values():
                if tt_day.title == day_title:
                    day = tt_day
                    break
            if day is None:
                self.error(row, 13, ERROR_INVALID_DAY_ID)
                return timetable, schedule

        if data['period']:
            if day is None:
                self.error(row, 14, ERROR_NO_DAY_DEFINED)
                return timetable, schedule
            period = None
            period_title = data['period']
            for tt_period in day.values():
                if tt_period.title == period_title:
                    period = tt_period
            if period is None:
                self.error(row, 14, ERROR_INVALID_PERIOD_ID)
                return timetable, schedule
            schedule.addPeriod(period)
        elif day is not None:
            self.error(row, 14, ERROR_MISSING_PERIOD_ID)

        return timetable, schedule

    def import_section_links(self, prev_links, next_links):
        for row, (section, link_id) in sorted(prev_links.items()):
            term = ITerm(section)
            previous_term = getPreviousTerm(term)
            if previous_term is None:
                self.error(row, 9, ERROR_CURRENT_SECTION_FIRST_TERM)
            else:
                previous_sections = ISectionContainer(previous_term)
                if link_id in previous_sections:
                    previous_sections[link_id].next = section
                else:
                    self.error(row, 9, ERROR_INVALID_PREV_TERM_SECTION)

        for row, (section, link_id) in sorted(next_links.items()):
            term = ITerm(section)
            next_term = getNextTerm(term)
            if next_term is None:
                self.error(row, 10, ERROR_CURRENT_SECTION_LAST_TERM)
            else:
                next_sections = ISectionContainer(next_term)
                if link_id in next_sections:
                    next_sections[link_id].previous = section
                else:
                    self.error(row, 10, ERROR_INVALID_NEXT_TERM_SECTION)

    def process(self):
        sh = self.sheet
        schoolyears = ISchoolYearContainer(self.context)
        persons = self.context['persons']
        resources = self.context['resources']
        year = term = section = timetable = schedule = None
        prev_links, next_links = {}, {}

        for row in range(1, sh.nrows):
            data = {}
            data['year'] = self.getTextFromCell(sh, row, 0)
            data['courses'] = self.getTextFromCell(sh, row, 1)
            data['term'] = self.getTextFromCell(sh, row, 2)
            data['__name__'] = self.getTextFromCell(sh, row, 3)
            data['title'] = self.getTextFromCell(sh, row, 4)
            data['description'] = self.getTextFromCell(sh, row, 5)
            data['instructor'] = self.getTextFromCell(sh, row, 6)
            data['student'] = self.getTextFromCell(sh, row, 7)
            data['resource'] = self.getTextFromCell(sh, row, 8)
            data['link_prev'] = self.getTextFromCell(sh, row, 9)
            data['link_next'] = self.getTextFromCell(sh, row, 10)
            data['timetable'] = self.getTextFromCell(sh, row, 11)
            data['consecutive'] = self.getTextFromCell(sh, row, 12)
            data['day'] = self.getTextFromCell(sh, row, 13)
            data['period'] = self.getTextFromCell(sh, row, 14)

            if not [v for v in data.values() if v]:
                break
            data['consecutive'] = bool(self.getBoolFromCell(sh, row, 12))

            if data['year']:
                year_id = data['year']
                if year_id not in schoolyears:
                    self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
                    year = None
                else:
                    year = schoolyears[year_id]
                    students = self.ensure_students_group(year)
                    teachers = self.ensure_teachers_group(year)
                    courses = None
            elif year is None:
                self.error(row, 0, ERROR_MISSING_YEAR_ID)
            if year is None:
                continue

            if data['courses']:
                course_container = ICourseContainer(year)
                course_ids = [c.strip() for c in data['courses'].split(',')]
                courses = []
                for course_id in course_ids:
                    if course_id not in course_container:
                        self.error(row, 1, ERROR_INVALID_COURSE_ID)
                        courses = None
                        break
                    course = course_container[course_id]
                    courses.append(removeSecurityProxy(course))
                term = None
            elif courses is None:
                self.error(row, 1, ERROR_MISSING_COURSES)
            if courses is None:
                continue

            if data['term']:
                term_id = data['term']
                if term_id not in year:
                    self.error(row, 2, ERROR_INVALID_TERM_ID)
                    term = None
                else:
                    term = year[term_id]
                    section = None
            elif term is None:
                self.error(row, 2, ERROR_MISSING_TERM_ID)
            if term is None:
                continue

            if data['__name__']:
                if not data['title']:
                    self.error(row, 4, ERROR_MISSING_REQUIRED_TEXT)
                    data['title'] = 'Invalid, but keep parsing...'
                section = self.createSection(data, year, term, courses)
                timetable = None
            elif section is None:
                self.error(row, 3, ERROR_MISSING_REQUIRED_TEXT)
            if section is None:
                continue

            if data['instructor']:
                person_id = data['instructor']
                if person_id not in persons:
                    self.error(row, 6, ERROR_INVALID_PERSON_ID)
                else:
                    teacher = persons[person_id]
                    if teacher not in section.instructors:
                        section.instructors.add(removeSecurityProxy(teacher))
                    if teacher not in teachers.members:
                        teachers.members.add(removeSecurityProxy(teacher))

            if data['student']:
                person_id = data['student']
                if person_id not in persons:
                    self.error(row, 7, ERROR_INVALID_PERSON_ID)
                else:
                    student = persons[person_id]
                    if student not in section.members:
                        section.members.add(removeSecurityProxy(student))
                    if student not in students.members:
                        students.members.add(removeSecurityProxy(student))

            if data['resource']:
                resource_id = data['resource']
                if resource_id not in resources:
                    self.error(row, 8, ERROR_INVALID_RESOURCE_ID)
                else:
                    resource = resources[resource_id]
                    if resource not in section.resources:
                        section.resources.add(removeSecurityProxy(resource))

            if data['link_prev']:
                prev_links[row] = (section, data['link_prev'])

            if data['link_next']:
                next_links[row] = (section, data['link_next'])

            timetable, schedule = self.import_timetable_row(row, data, section,
                                                            timetable, schedule)

        self.import_section_links(prev_links, next_links)


class GroupImporter(ImporterBase):

    sheet_name = 'Groups'

    def createGroup(self, data):
        syc = ISchoolYearContainer(self.context)
        gc = IGroupContainer(syc[data['school_year']])
        if data['__name__'] in gc:
            group = gc[data['__name__']]
            group.title = data['title']
            group.description = data['description']
        else:
            group = Group(data['title'], data['description'])
            group.__name__ = data['__name__']
        return group

    def addGroup(self, group, data):
        syc = ISchoolYearContainer(self.context)
        gc = IGroupContainer(syc[data['school_year']])
        if group.__name__ is None:
            group.__name__ = SimpleNameChooser(gc).chooseName('', group)

        if group.__name__ not in gc:
            gc[group.__name__] = group

    def import_group(self, sh, row):
        num_errors = len(self.errors)
        data = {}
        data['title'] = self.getRequiredTextFromCell(sh, row, 1)
        data['__name__'] = self.getRequiredTextFromCell(sh, row+1, 1)
        data['school_year'] = self.getRequiredTextFromCell(sh, row+2, 1)
        data['description'] = self.getTextFromCell(sh, row+3, 1)
        if num_errors < len(self.errors):
            return
        if data['school_year'] not in ISchoolYearContainer(self.context):
            self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
            return

        group = self.createGroup(data)
        self.addGroup(group, data)

        row += 5
        pc = self.context['persons']
        if self.getCellValue(sh, row, 0, '') == 'Members':
            row += 1
            for row in range(row, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break
                num_errors = len(self.errors)
                username = self.getRequiredTextFromCell(sh, row, 0)
                if num_errors < len(self.errors):
                    continue
                if username not in pc:
                    self.error(row, 0, ERROR_INVALID_PERSON_ID)
                    continue
                member = pc[username]
                if member not in group.members:
                    group.members.add(removeSecurityProxy(member))

    def process(self):
        sh = self.sheet
        for row in range(0, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == 'Group Title':
                self.import_group(sh, row)


class MegaImporter(BrowserView):

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.data_provided = False
        self.errors = []
        self.success = []

    @property
    def importers(self):
        return [SchoolYearImporter,
                TermImporter,
                SchoolTimetableImporter,
                ResourceImporter,
                PersonImporter,
                TeacherImporter,
                StudentImporter,
                ContactPersonImporter,
                ContactRelationshipImporter,
                CourseImporter,
                GroupImporter,
                SectionImporter,
                FlatSectionsTableImporter,
                SectionsImporter,
                SectionEnrollmentImporter,
                SectionTimetablesImporter,
                ]

    def update(self):
        if "UPDATE_SUBMIT" not in self.request:
            return

        xlsfile = self.request.get('xlsfile', '')
        if not xlsfile:
            return
        self.data_provided = True

        wb = xlrd.open_workbook(file_contents=xlsfile.read())

        if wb is None:
            return


        sp = transaction.savepoint(optimistic=True)

        importers = self.importers

        for importer in importers:
            imp = importer(self.context, self.request)
            imp.import_data(wb)
            self.errors.extend(imp.errors)

        if self.errors:
            sp.rollback()
        else:
            self.request.response.redirect(self.nextURL())

    def nextURL(self):
        return self.request.URL

    def hasErrors(self):
        if "UPDATE_SUBMIT" not in self.request:
            return False
        return not self.data_provided or self.errors

    def errorSummary(self):
        if not self.data_provided:
            return _('No data provided')
        return _('The following errors occurred while importing:')

    def textareaErrors(self):
        errors = {}
        for sheet_name, row, col, message in self.errors:
            sheet_errors = errors.setdefault(sheet_name, {})
            sheet_errors.setdefault(message, []).append((col, row))
        error_lines = []
        for sheet_name, message_errors in sorted(errors.items()):
            if error_lines:
                error_lines.append('')
            error_lines.append(sheet_name)
            error_lines.append('-' * len(sheet_name))
            for message, cells in sorted(message_errors.items()):
                col_rows = []
                current_col, start, end = -1, 0, 0
                for col, row in sorted(cells):
                    if col != current_col or row > end + 1:
                        if current_col > -1:
                            col_rows.append((current_col, start, end))
                        current_col, start = col, row
                    end = row
                col_rows.append((current_col, start, end))
                error_lines.append('')
                error_lines.append(translate(message) + ':')
                error_cells = []
                for col, start, end in col_rows:
                    cell = chr(col + ord('A'))
                    if start == end:
                        cell += '%s' % (start + 1)
                    else:
                        cell += '%s-%s' % (start + 1, end + 1)
                    error_cells.append(cell)
                error_lines.append(', '.join(error_cells))
        return '\n'.join(error_lines)



class FlourishMegaImporter(flourish.page.Page, MegaImporter):
    __init__ = MegaImporter.__init__
    update = MegaImporter.update

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        return '%s/manage' % url

    def update(self):
        if "UPDATE_CANCEL" in self.request:
            self.request.response.redirect(self.nextURL())
            return
        return MegaImporter.update(self)
