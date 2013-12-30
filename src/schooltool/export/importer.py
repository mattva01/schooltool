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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool simple import views.
"""
import xlrd
import datetime
import urllib
import transaction
from decimal import Decimal, InvalidOperation

import zope.file.upload
import zope.file.file
import zope.schema
import zope.lifecycleevent
import z3c.form.button, z3c.form.field
from zope.interface import implements, Interface
from zope.cachedescriptors.property import Lazy
from zope.container.contained import containedEvent
from zope.container.interfaces import INameChooser
from zope.component import queryMultiAdapter
from zope.event import notify
from zope.i18n import translate
from zope.security.proxy import removeSecurityProxy
from zope.publisher.browser import BrowserView
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.person.interfaces import IPerson
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.interfaces import IDemographics
from schooltool.basicperson.demographics import DateFieldDescription
from schooltool.basicperson.demographics import BoolFieldDescription
from schooltool.basicperson.demographics import IntFieldDescription
from schooltool.basicperson.person import BasicPerson
from schooltool.contact.contact import Contact, ContactPersonInfo
from schooltool.contact.interfaces import IContact, IContactContainer
from schooltool.contact.interfaces import IContactPersonInfo, IContactable
from schooltool.contact.contact import getAppContactStates
from schooltool.export.interfaces import IImporterTask, IImportFile
from schooltool.resource.resource import Resource
from schooltool.resource.resource import Location
from schooltool.resource.resource import Equipment
from schooltool.group.group import Group
from schooltool.group.interfaces import IGroupContainer
from schooltool.term.interfaces import ITerm
from schooltool.term.term import Term, getNextTerm, getPreviousTerm
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import IRelationshipStateContainer
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
from schooltool.task.interfaces import IRemoteTask
from schooltool.task.progress import Timer
from schooltool.task.tasks import RemoteTask
from schooltool.task.state import TaskWriteState, TaskReadState
from schooltool.task.tasks import get_message_by_id, query_message
from schooltool.task.tasks import TaskScheduledNotification
from schooltool.task.progress import TaskProgress
from schooltool.report.interfaces import IReportTask
from schooltool.report.report import AbstractReportTask
from schooltool.report.report import NoReportException
from schooltool.report.report import ReportFile, ReportProgressMessage
from schooltool.report.report import GeneratedReportMessage
from schooltool.report.report import OnReportGenerated
from schooltool.report.browser.report import RequestRemoteReportDialog
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


ERROR_NOT_XLS = _('SchoolTool cannot read this file. Is it a .xls formatted spreadsheet?')
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
ERROR_HAS_NO_DAYS = _("has no days")
ERROR_HAS_NO_DAY_TEMPLATES = _("has no day templates")
ERROR_TIME_RANGE = _("is not a valid time range")
ERROR_TIMETABLE_MODEL = _("is not a valid timetable model")
ERROR_DUPLICATE_DAY_ID = _("is the same day id as another in this timetable")
ERROR_UNKNOWN_DAY_ID = _("is not defined in the 'Day Templates' section")
ERROR_DUPLICATE_PERIOD = _("is the same period id as another in this day")
ERROR_DUPLICATE_HOMEROOM_PERIOD = _("is the same homeroom period id as another in this day")
ERROR_RESOURCE_TYPE = _("must be either 'Location', 'Equipment' or 'Resource'")
ERROR_INVALID_TERM_ID = _('is not a valid term in the given school year')
ERROR_INVALID_COURSE_ID = _('is not a valid course in the given school year')
ERROR_HAS_NO_COURSES = _('has no courses')
ERROR_INVALID_PERSON_ID = _('is not a valid username')
ERROR_INVALID_SCHEMA_ID = _('is not a valid timetable in the given school year')
ERROR_INVALID_DAY_ID = _('is not a valid day id for the given timetable')
ERROR_INVALID_PERIOD_ID = _('is not a valid period id for the given day')
ERROR_INVALID_CONTACT_ID = _('is not a valid username or contact id')
ERROR_UNWANTED_CONTACT_DATA = _('must be empty when ID is a user id')
ERROR_INVALID_RESOURCE_ID = _('is not a valid resource id')
ERROR_UNICODE_CONVERSION = _("Username cannot contain non-ascii characters")
ERROR_RELATIONSHIP_CODE = _("is not a valid relationship code")
ERROR_NOT_BOOLEAN = _("must be either TRUE, FALSE, YES or NO (upper, lower and mixed case are all valid)")
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
ERROR_INVALID_RESOURCE_ID_LIST = _("has an invalid resource id")
ERROR_INVALID_COURSE_ID_LIST = _("has an invalid course id for the given school year")
ERROR_END_TERM_BEFORE_START = _('end term cannot be before start term')
ERROR_TERM_SECTION_ID = _('is not a valid section id in the specified term')
ERROR_INCONSISTENT_SCHOOL_YEAR = _('school years must be consistent within this table')


no_date = object()
no_data = object()


def normalized_progress(*args):
    pmin = 0.0
    pmax = 1.0
    n = len(args)
    while n > 0:
        pmin = pmin + pmax * args[n-2]
        pmax = pmax * args[n-1]
        n -= 2
    return min(float(pmin) / float(pmax), 1.0)


class ImporterBase(object):

    title = _("Import")

    def __init__(self, context, request,
                 progress_callback=None):
        self.context, self.request = context, request
        self.errors = []
        self.progress_callback = progress_callback

    def progress(self, *args):
        progress = normalized_progress(*args)
        if self.progress_callback is not None:
            self.progress_callback(progress)

    def isEmptyRow(self, sheet, row, num_cols=30):
        # We'll pick 30 as an arbitrary number of columns to test so that we
        # don't need the caller to specify the number.  When a new column is
        # added to a sheet, the needed change in calling this method would
        # likely be overlooked.  It's not that expensive anyway to test all 30.
        for col in range(num_cols):
            try:
                if sheet.cell_value(rowx=row, colx=col):
                    return False
            except IndexError:
                break
        return True

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
        if (isinstance(value, (str, unicode)) and
            not value.strip()):
            found = False
            value = default
        if found:
            try:
                value = int(value)
            except (TypeError, ValueError):
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    pass
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
                value = default
        return value, found, valid

    def iterRelationships(self, sheet, row, startcol):
        col = startcol - 2
        while True:
            col += 2
            raw_date = None
            try:
                raw_date = sheet.cell_value(rowx=row, colx=col)
            except IndexError:
                raw_date = None
            if not raw_date:
                break

            try:
                date_tuple = xlrd.xldate_as_tuple(raw_date, self.wb.datemode)
                date = datetime.datetime(*date_tuple).date()
            except ValueError:
                self.error(row, col, ERROR_NO_DATE)
                continue

            code_text = sheet.cell_value(rowx=row, colx=col+1)
            try:
                code_text = unicode(code_text)
            except UnicodeError:
                self.error(row, col, ERROR_NOT_UNICODE_OR_ASCII)

            yield date, code_text

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
        if not value:
            self.error(row, col, ERROR_MISSING_REQUIRED_TEXT)
            return None
        return self.getBoolFromCell(sheet, row, col)

    def getIdFromCell(self, sheet, row, col, default=u''):
        value, found, valid = self.getTextFoundValid(sheet, row, col, default)
        return value.strip()

    def getRequiredIdFromCell(self, sheet, row, col):
        value, found, valid = self.getTextFoundValid(sheet, row, col)
        if valid and not value:
            self.error(row, col, ERROR_MISSING_REQUIRED_TEXT)
        return value.strip()

    def getIdsFromCell(self, sheet, row, col):
        value, found, valid = self.getTextFoundValid(sheet, row, col)
        if not value:
            return []
        return [p.strip() for p in value.split(',') if p.strip()]

    def getRequiredIdsFromCell(self, sheet, row, col):
        value, found = self.getCellAndFound(sheet, row, col)
        if not value:
            self.error(row, col, ERROR_MISSING_REQUIRED_TEXT)
            return []
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

    def createSection(self, data, term, courses):
        sc = ISectionContainer(term)
        if data['__name__'] in sc:
            section = sc[data['__name__']]
            section.title = data['title']
            section.description = data['description']
            for course in list(section.courses):
                section.courses.remove(removeSecurityProxy(course))
            for resource in list(section.resources):
                section.resources.remove(removeSecurityProxy(resource))
            for student in list(section.members):
                section.members.all().unrelate(removeSecurityProxy(student))
            for teacher in list(section.instructors):
                section.instructors.all().unrelate(removeSecurityProxy(teacher))
        else:
            section = Section(data['title'], data['description'])
            section.__name__ = data['__name__']
            sc[section.__name__] = section
        for course in courses:
            section.courses.add(removeSecurityProxy(course))
        return section

    def updateRelationships(self, relationship, target, app_states, codes):
        target = removeSecurityProxy(target)
        existing = relationship.state(target)
        if existing is not None:
            for date, _m, _c in list(existing):
                if date not in codes:
                    del existing[date]
        for rel_date, rel_code in codes.items():
            rel_meaning = app_states.states.get(rel_code).active
            relationship.on(rel_date).relate(
                target, meaning=rel_meaning, code=rel_code)


class SchoolYearImporter(ImporterBase):

    title = _("School Years")

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
        nrows = sh.nrows
        for row in range(1, nrows):
            num_errors = len(self.errors)
            data = {}
            data['__name__'] = self.getRequiredIdFromCell(sh, row, 0)
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
            self.progress(row, nrows)


class TermImporter(ImporterBase):

    title = _("Terms")

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
        nrows = sh.nrows
        for row in range(1, nrows):
            if self.isEmptyRow(sh, row):
                break

            num_errors = len(self.errors)
            data = {}
            data['school_year'] = self.getRequiredIdFromCell(sh, row, 0)
            data['__name__'] = self.getRequiredIdFromCell(sh, row, 1)
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

            self.progress(row, nrows)

        row += 1
        if self.getCellValue(sh, row, 0, '') == 'Holidays':
            for row in range(row + 1, nrows):
                if self.isEmptyRow(sh, row):
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
                self.progress(row, nrows)

        row += 1
        if self.getCellValue(sh, row, 0, '') == 'Weekends':
            row += 2
            for col in range(7):
                try:
                    sh.cell_value(rowx=row, colx=col)
                except IndexError:
                    continue
                if sh.cell_value(rowx=row, colx=col) != '':
                    for sy in ISchoolYearContainer(self.context).values():
                        for term in sy.values():
                            term.removeWeekdays(col)
            self.progress(row, nrows)


class SchoolTimetableImporter(ImporterBase):

    title = _("School Timetables")

    sheet_name = 'School Timetables'

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

        for n, entry in enumerate(data['periods']):
            day_title = entry['id']
            day = DayTemplate(day_title)
            key = unicode(n)
            timetable.periods.templates[key] = day
            p_chooser = INameChooser(day)
            for period_entry in entry['periods']:
                period = Period(title=period_entry['title'],
                                activity_type=period_entry['activity'] or None)
                p_name = p_chooser.chooseName('', period)
                day[p_name] = period

        for n, entry in enumerate(data['time_slots']):
            day_title = entry['id']
            day = DayTemplate(day_title)
            key = unicode(n)
            timetable.time_slots.templates[key] = day
            ts_chooser = INameChooser(day)
            for ts_entry in entry['time_slots']:
                time_slot = TimeSlot(
                    ts_entry['starts'], ts_entry['duration'],
                    activity_type=ts_entry['activity'] or None)
                ts_name = ts_chooser.chooseName('', time_slot)
                day[ts_name] = time_slot

    def import_school_timetable(self, sh, row):
        num_errors = len(self.errors)
        data = {}
        data['title'] = self.getRequiredTextFromCell(sh, row, 1)
        data['__name__'] = self.getRequiredIdFromCell(sh, row+1, 1)
        data['school_year'] = self.getRequiredIdFromCell(sh, row+2, 1)
        data['period_templates'] = self.getRequiredIdFromCell(sh, row+3, 1)
        data['time_templates'] = self.getRequiredIdFromCell(sh, row+4, 1)
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
                if self.isEmptyRow(sh, row):
                    break

                day_id = self.getRequiredIdFromCell(sh, row, 0)

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
            self.error(row, 0, ERROR_HAS_NO_DAYS)

        row += 1
        if self.getCellValue(sh, row, 0, '').lower() == 'time schedule':
            data['time_slots'] = []
            row += 1

            while row < sh.nrows:
                if self.isEmptyRow(sh, row):
                    break

                day_id = self.getRequiredIdFromCell(sh, row, 0)

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
                data['time_slots'].append({
                        'id': day_id,
                        'time_slots': time_slots
                        })
                row += 2
        else:
            self.error(row, 0, ERROR_HAS_NO_DAY_TEMPLATES)
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

    title = _("Resources")

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
            if self.isEmptyRow(sh, row):
                continue
            num_errors = len(self.errors)
            data = {}
            data['__name__'] = self.getRequiredIdFromCell(sh, row, 0)
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

    title = _("Persons")

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
        return person

    def process(self):
        sh = self.sheet
        nrows = sh.nrows

        fields = IDemographicsFields(ISchoolToolApplication(None))
        if self.group_name:
            num_errors = len(self.errors)
            year_id = self.getRequiredIdFromCell(sh, 0, 1)
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

        for row in range(first_row, nrows):
            if self.isEmptyRow(sh, row):
                continue

            num_errors = len(self.errors)
            data = {}
            data['__name__'] = self.getRequiredIdFromCell(sh, row, 0)
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
                # /me wraps head in tinfoil for protection:
                if field.required:
                    if isinstance(field, DateFieldDescription):
                        value = self.getDateFromCell(sh, row, n + 10)
                    elif isinstance(field, BoolFieldDescription):
                        value = self.getRequiredBoolFromCell(sh, row, n + 10)
                    elif isinstance(field, IntFieldDescription):
                        value = self.getRequiredIntFromCell(sh, row, n + 10)
                    else:
                        value = self.getRequiredTextFromCell(sh, row, n + 10)
                else:
                    if isinstance(field, DateFieldDescription):
                        value = self.getDateFromCell(sh, row, n + 10,
                                                     default=None)
                    elif isinstance(field, BoolFieldDescription):
                        value = self.getBoolFromCell(sh, row, n + 10)
                    elif isinstance(field, IntFieldDescription):
                        value = self.getIntFromCell(sh, row, n + 10)
                    else:
                        value = self.getTextFromCell(sh, row, n + 10)
                    if value == '':
                        value = None
                demographics[field.name] = value

            if num_errors == len(self.errors):
                person = self.addPerson(person, data)
                if group and person not in group.members:
                    group.members.add(removeSecurityProxy(person))
            self.progress(row, nrows)


class TeacherImporter(PersonImporter):

    title = _("Teachers")

    sheet_name = 'Teachers'
    group_name = 'teachers'


class StudentImporter(PersonImporter):

    title = _("Students")

    sheet_name = 'Students'
    group_name = 'students'


class ContactPersonImporter(ImporterBase):

    title = _("Contact Persons")

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
        nrows = sh.nrows
        for row in range(1, nrows):
            if self.isEmptyRow(sh, row):
                continue

            num_errors = len(self.errors)
            data = {}

            data['__name__'] = self.getRequiredIdFromCell(sh, row, 0)
            if data['__name__'] is not None:
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
            self.progress(row, nrows)


class ContactRelationshipImporter(ImporterBase):

    title = _("Contact Relationships")

    sheet_name = 'Contact Relationships'

    def process(self):
        sh = self.sheet
        app = ISchoolToolApplication(None)
        app_states = getAppContactStates()
        app_codes = list(app_states.states)
        persons = app['persons']
        contacts = IContactContainer(app)
        nrows = sh.nrows
        for row in range(1, nrows):
            if self.isEmptyRow(sh, row):
                continue

            num_errors = len(self.errors)
            data = {}

            data['__name__'] = self.getRequiredIdFromCell(sh, row, 0)
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

            relationships = {}
            for rel_date, rel_code in self.iterRelationships(sh, row, 2):
                if rel_code not in app_codes:
                    self.error(row, 2, ERROR_RELATIONSHIP_CODE)
                else:
                    relationships[rel_date] = rel_code

            if num_errors == len(self.errors):
                self.updateRelationships(
                    IContactable(person).contacts, contact, app_states, relationships)
            self.progress(row, nrows)


class CourseImporter(ImporterBase):

    title = _("Courses")

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
        nrows = sh.nrows
        for row in range(1, nrows):
            if self.isEmptyRow(sh, row):
                continue
            num_errors = len(self.errors)
            data = {}
            data['school_year'] = self.getRequiredIdFromCell(sh, row, 0)
            data['__name__'] = self.getRequiredIdFromCell(sh, row, 1)
            data['title'] = self.getRequiredTextFromCell(sh, row, 2)
            data['description'] = self.getTextFromCell(sh, row, 3)
            data['course_id'] = self.getIdFromCell(sh, row, 4)
            data['government_id'] = self.getIdFromCell(sh, row, 5)
            data['credits'] = self.getTextFromCell(sh, row, 6)
            try:
                if data['credits']:
                    data['credits'] = Decimal(data['credits'])
            except InvalidOperation:
                self.error(row, 6, ERROR_INVALID_COURSE_CREDITS)
            if num_errors < len(self.errors):
                continue
            if data['school_year'] not in ISchoolYearContainer(self.context):
                self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
                continue
            course = self.createCourse(data)
            self.addCourse(course, data)
            self.progress(row, nrows)


class SectionImporter(ImporterBase):

    title = _("Sections")

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

        timetable_id = self.getRequiredIdFromCell(sh, row, 1)
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

            if self.isEmptyRow(sh, row):
                break
            num_errors = len(self.errors)
            day_title = self.getRequiredIdFromCell(sh, row, 0)
            period_title = self.getRequiredIdFromCell(sh, row, 1)
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
            elif self.isEmptyRow(sh, row):
                break
        return row

    def import_section(self, sh, row, year, term):
        data = {}
        data['title'] = self.getRequiredTextFromCell(sh, row, 1)
        data['__name__'] = self.getRequiredIdFromCell(sh, row+1, 1)
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
                if self.isEmptyRow(sh, row):
                    break
                num_errors = len(self.errors)

                course_id = self.getRequiredIdFromCell(sh, row, 0)
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
            self.error(row, 0, ERROR_HAS_NO_COURSES)
            return

        persons = self.context['persons']
        if self.getCellValue(sh, row, 0, '') == 'Students':
            row += 1
            for row in range(row, sh.nrows):
                if self.isEmptyRow(sh, row):
                    break
                num_errors = len(self.errors)

                username = self.getRequiredIdFromCell(sh, row, 0)
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
                if self.isEmptyRow(sh, row):
                    break
                num_errors = len(self.errors)

                username = self.getRequiredIdFromCell(sh, row, 0)
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
        sheet_names = self.sheet_names
        nsheets = len(sheet_names)
        for (n, self.sheet_name) in enumerate(sheet_names):
            sheet = self.wb.sheet_by_name(self.sheet_name)

            num_errors = len(self.errors)
            year_id = self.getRequiredIdFromCell(sheet, 0, 1)
            term_id = self.getRequiredIdFromCell(sheet, 0, 3)
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

            nrows = sheet.nrows
            for row in range(2, nrows):
                if sheet.cell_value(rowx=row, colx=0) == 'Section Title':
                    self.import_section(sheet, row, year, term)
                self.progress(n, nsheets, row, nrows)

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

    title = _("Sections")

    sheet_name = 'Sections'

    def import_section_links(self, prev_links, next_links):
        for row, (section, link_id) in sorted(prev_links.items()):
            term = ITerm(section)
            previous_term = getPreviousTerm(term)
            if previous_term is None:
                self.error(row, 4, ERROR_CURRENT_SECTION_FIRST_TERM)
            else:
                previous_sections = ISectionContainer(previous_term)
                if link_id in previous_sections:
                    previous_sections[link_id].next = section
                else:
                    self.error(row, 4, ERROR_INVALID_PREV_TERM_SECTION)

        for row, (section, link_id) in sorted(next_links.items()):
            term = ITerm(section)
            next_term = getNextTerm(term)
            if next_term is None:
                self.error(row, 5, ERROR_CURRENT_SECTION_LAST_TERM)
            else:
                next_sections = ISectionContainer(next_term)
                if link_id in next_sections:
                    next_sections[link_id].previous = section
                else:
                    self.error(row, 5, ERROR_INVALID_NEXT_TERM_SECTION)

    def process(self):
        sh = self.sheet
        schoolyears = ISchoolYearContainer(self.context)
        resources = self.context['resources']
        prev_links, next_links = {}, {}

        nrows = sh.nrows
        for row in range(1, nrows):
            if self.isEmptyRow(sh, row):
                continue

            data = {}
            num_errors = len(self.errors)
            data['year'] = self.getRequiredIdFromCell(sh, row, 0)
            data['courses'] = self.getRequiredIdsFromCell(sh, row, 1)
            data['term'] = self.getRequiredIdFromCell(sh, row, 2)
            data['__name__'] = self.getRequiredIdFromCell(sh, row, 3)
            data['link_prev'] = self.getIdFromCell(sh, row, 4)
            data['link_next'] = self.getIdFromCell(sh, row, 5)
            data['title'] = self.getRequiredTextFromCell(sh, row, 6)
            data['description'] = self.getTextFromCell(sh, row, 7)
            data['resources'] = self.getIdsFromCell(sh, row, 8)
            if num_errors < len(self.errors):
                continue

            for resource_id in data['resources']:
                if resource_id not in resources:
                    self.error(row, 8, ERROR_INVALID_RESOURCE_ID_LIST)
                    break

            if data['year'] not in schoolyears:
                self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
                continue

            year = schoolyears[data['year']]
            course_container = ICourseContainer(year)

            courses = []
            for course_id in data['courses']:
                if course_id not in course_container:
                    self.error(row, 1, ERROR_INVALID_COURSE_ID_LIST)
                    break
                else:
                    course = course_container[course_id]
                    courses.append(removeSecurityProxy(course))

            if data['term'] not in year:
                self.error(row, 2, ERROR_INVALID_TERM_ID)

            if num_errors < len(self.errors):
                continue

            term = year[data['term']]
            section = self.createSection(data, term, courses)

            if data['link_prev']:
                prev_links[row] = (section, data['link_prev'])

            if data['link_next']:
                next_links[row] = (section, data['link_next'])

            for resource_id in data['resources']:
                resource = resources[resource_id]
                if resource not in section.resources:
                    section.resources.add(removeSecurityProxy(resource))

            self.progress(row, nrows)

        self.import_section_links(prev_links, next_links)


class SectionMixin(object):

    def get_sections(self, sh, row):
        schoolyears = ISchoolYearContainer(self.context)

        sections = []
        current_year_id = None
        nrows = sh.nrows
        for row in range(row + 1, nrows):
            if self.isEmptyRow(sh, row):
                break

            num_errors = len(self.errors)
            year_id = self.getRequiredIdFromCell(sh, row, 0)
            term_id = self.getRequiredIdFromCell(sh, row, 1)
            section_id = self.getRequiredIdFromCell(sh, row, 2)
            if num_errors < len(self.errors):
                continue

            if year_id not in schoolyears:
                self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
                continue
            if current_year_id is not None and year_id != current_year_id:
                self.error(row, 0, ERROR_INCONSISTENT_SCHOOL_YEAR)
                continue
            current_year_id = year_id
            year = schoolyears[year_id]

            if term_id not in year:
                self.error(row, 1, ERROR_INVALID_TERM_ID)
                continue
            term = year[term_id]
            section_container = ISectionContainer(term)

            if section_id not in section_container:
                self.error(row, 2, ERROR_TERM_SECTION_ID)
                continue
            sections.append(section_container[section_id])

            self.progress(row, nrows)

        return sections


class SectionEnrollmentImporter(ImporterBase, SectionMixin):

    title = _("Section Enrollment")

    sheet_name = 'SectionEnrollment'

    @Lazy
    def student_app_states(self):
        app = ISchoolToolApplication(None)
        container = IRelationshipStateContainer(app)
        app_states = container['section-membership']
        return app_states

    @Lazy
    def instructor_app_states(self):
        app = ISchoolToolApplication(None)
        container = IRelationshipStateContainer(app)
        app_states = container['section-instruction']
        return app_states

    def get_persons(self, sh, row, header, app_states):
        app_codes = list(app_states.states)
        persons = self.context['persons']
        for row in range(row + 1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == header:
                break
        else:
            return []

        result = []
        nrows = sh.nrows
        for row in range(row + 1, nrows):
            if self.isEmptyRow(sh, row):
                break

            person_id = self.getRequiredIdFromCell(sh, row, 0)
            if person_id is None:
                continue

            if person_id not in persons:
                self.error(row, 0, ERROR_INVALID_PERSON_ID)
                self.progress(row, nrows)
                continue

            relationships = {}
            for rel_date, rel_code in self.iterRelationships(sh, row, 2):
                if rel_code not in app_codes:
                    self.error(row, 2, ERROR_RELATIONSHIP_CODE)
                else:
                    relationships[rel_date] = rel_code

            result.append((persons[person_id], relationships))

            self.progress(row, nrows)

        return result

    def process(self):
        sh = self.sheet
        nrows = sh.nrows
        for row in range(0, nrows):
            if sh.cell_value(rowx=row, colx=0) != 'School Year':
                continue

            num_errors = len(self.errors)
            sections = self.get_sections(sh, row)

            instructors = self.get_persons(
                sh, row, 'Instructors', self.instructor_app_states)
            students = self.get_persons(
                sh, row, 'Students', self.student_app_states)
            if num_errors < len(self.errors):
                continue
            if not sections or not students:
                continue

            year = ISchoolYear(sections[0])

            students_group = self.ensure_students_group(year)
            all_student_members = students_group.members.all()
            student_states = self.student_app_states

            teachers_group = self.ensure_teachers_group(year)
            instructor_states = self.instructor_app_states
            all_teacher_members = teachers_group.members.all()

            for section in sections:
                for student, codes in students:
                    self.updateRelationships(
                        section.members, student, student_states, codes)
                    if student not in all_student_members:
                        students_group.members.add(removeSecurityProxy(student))

                for instructor, codes in instructors:
                    self.updateRelationships(
                        section.instructors, instructor, instructor_states, codes)
                    if instructor not in all_teacher_members:
                        teachers_group.members.add(removeSecurityProxy(instructor))

            self.progress(row, nrows)


class SectionTimetablesImporter(ImporterBase, SectionMixin):

    title = _("Section Timetables")

    sheet_name = 'SectionTimetables'

    def import_timetable(self, sh, row, sections):
        year = ISchoolYear(sections[0])
        timetables = ITimetableContainer(year)

        for row in range(row + 1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == 'Timetable':
                break
        else:
            return

        num_errors = len(self.errors)
        timetable_id = self.getRequiredIdFromCell(sh, row, 1)
        consecutive = self.getBoolFromCell(sh, row, 3)
        if num_errors < len(self.errors):
            return

        if timetable_id not in timetables:
            self.error(row, 3, ERROR_INVALID_SCHEMA_ID)
            return
        timetable = timetables[timetable_id]

        for row in range(row + 1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == 'Day':
                break
        else:
            return

        schedules = []
        for section in sections:
            term = ITerm(section)
            schedule = SelectedPeriodsSchedule(
                timetable, term.first, term.last,
                title=timetable.title, timezone=timetable.timezone)
            schedule.consecutive_periods_as_one = bool(consecutive)
            schedules.append(schedule)

        nrows = sh.nrows
        for row in range(row + 1, nrows):
            if self.isEmptyRow(sh, row):
                break

            day_title = self.getIdFromCell(sh, row, 0)
            period_title = self.getRequiredIdFromCell(sh, row, 1)
            if period_title is None:
                continue

            for tt_day in timetable.periods.templates.values():
                if tt_day.title == day_title:
                    day = tt_day
                    break
            else:
                self.error(row, 0, ERROR_INVALID_DAY_ID)
                continue

            for tt_period in day.values():
                if tt_period.title == period_title:
                    period = tt_period
                    break
            else:
                self.error(row, 1, ERROR_INVALID_PERIOD_ID)
                continue

            for schedule in schedules:
                schedule.addPeriod(period)

            self.progress(row, nrows)

        for index, section in enumerate(sections):
            term = ITerm(section)
            schedule_container = IScheduleContainer(section)
            schedule = schedules[index]
            s_chooser = INameChooser(schedule_container)
            name = s_chooser.chooseName('', schedule)
            schedule_container[name] = schedule

    def process(self):
        sh = self.sheet
        nrows = sh.nrows
        for row in range(0, nrows):
            if sh.cell_value(rowx=row, colx=0) != 'School Year':
                continue

            num_errors = len(self.errors)
            sections = self.get_sections(sh, row)
            if num_errors < len(self.errors):
                continue

            self.import_timetable(sh, row, sections)

            self.progress(row, nrows)


class LinkedSectionImporter(ImporterBase):

    title = _("Linked sections")

    sheet_name = 'LinkedSectionImport'

    def validateStartEndTerms(self, year, data, row, col):
        if data['start_term'] not in year:
            self.error(row, col, ERROR_INVALID_TERM_ID)
        if data['end_term'] and data['end_term'] not in year:
            self.error(row, col + 1, ERROR_INVALID_TERM_ID)
            return []
        if data['start_term'] not in year:
            return []

        start_term = year[data['start_term']]
        if data['end_term']:
            end_term = year[data['end_term']]
        else:
            end_term = start_term

        if start_term.first > end_term.first:
            self.error(row, col + 1, ERROR_END_TERM_BEFORE_START)
            return []
        return [term for term in year.values()
                if term.first >= start_term.first and
                   term.first <= end_term.first]

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

    def process(self):
        sh = self.sheet
        schoolyears = ISchoolYearContainer(self.context)
        persons = self.context['persons']
        resources = self.context['resources']

        nrows = sh.nrows
        for row in range(1, nrows):
            if self.isEmptyRow(sh, row):
                continue

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

            for person_id in data['instructors']:
                if person_id not in persons:
                    self.error(row, 6, ERROR_INVALID_PERSON_ID_LIST)
                    break

            for resource_id in data['resources']:
                if resource_id not in resources:
                    self.error(row, 8, ERROR_INVALID_RESOURCE_ID_LIST)
                    break

            if data['year'] not in schoolyears:
                self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
                continue

            year = schoolyears[data['year']]
            teachers = self.ensure_teachers_group(year)
            course_container = ICourseContainer(year)

            courses = []
            for course_id in data['courses']:
                if course_id not in course_container:
                    self.error(row, 1, ERROR_INVALID_COURSE_ID_LIST)
                    break
                else:
                    course = course_container[course_id]
                    courses.append(removeSecurityProxy(course))

            terms = self.validateStartEndTerms(year, data, row, 2)
            if num_errors < len(self.errors):
                continue

            sections = self.createSectionsByTerm(data, terms, courses)

            for person_id in data['instructors']:
                teacher = persons[person_id]
                for section in sections:
                    if teacher not in section.instructors:
                        section.instructors.add(removeSecurityProxy(teacher))
                    if teacher not in teachers.members:
                        teachers.members.add(removeSecurityProxy(teacher))

            for resource_id in data['resources']:
                resource = resources[resource_id]
                for section in sections:
                    if resource not in section.resources:
                        section.resources.add(removeSecurityProxy(resource))

            self.progress(row, nrows)


class GroupImporter(ImporterBase):

    title = _("Groups")

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

    @Lazy
    def group_app_states(self):
        app = ISchoolToolApplication(None)
        container = IRelationshipStateContainer(app)
        app_states = container['group-membership']
        return app_states

    def import_group(self, sh, row):
        num_errors = len(self.errors)
        data = {}
        data['title'] = self.getRequiredTextFromCell(sh, row, 1)
        data['__name__'] = self.getRequiredIdFromCell(sh, row+1, 1)
        data['school_year'] = self.getRequiredIdFromCell(sh, row+2, 1)
        data['description'] = self.getTextFromCell(sh, row+3, 1)
        if num_errors < len(self.errors):
            return
        if data['school_year'] not in ISchoolYearContainer(self.context):
            self.error(row+2, 1, ERROR_INVALID_SCHOOL_YEAR)
            return

        group = self.createGroup(data)
        self.addGroup(group, data)
        self.progress(row, sh.nrows)

        row += 5

        app_states = self.group_app_states
        persons = self.context['persons']
        if self.getCellValue(sh, row, 0, '') == 'Members':
            row += 1
            nrows = sh.nrows
            for row in range(row, nrows):
                if self.isEmptyRow(sh, row):
                    break
                num_errors = len(self.errors)

                username = self.getRequiredIdFromCell(sh, row, 0)
                if num_errors < len(self.errors):
                    continue
                if username not in persons:
                    self.error(row, 0, ERROR_INVALID_PERSON_ID)
                    continue
                member = persons[username]

                relationships = {}
                for rel_date, rel_code in self.iterRelationships(sh, row, 2):
                    if rel_code not in app_codes:
                        self.error(row, 2, ERROR_RELATIONSHIP_CODE)
                    else:
                        relationships[rel_date] = rel_code

                self.updateRelationships(
                    group.members, removeSecurityProxy(member),
                    app_states, relationships)

                self.progress(row, nrows)

    def process(self):
        sh = self.sheet
        for row in range(0, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == 'Group Title':
                self.import_group(sh, row)


class MegaImporter(BrowserView):

    is_xls = True

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
                SectionsImporter,
                SectionEnrollmentImporter,
                SectionTimetablesImporter,
                LinkedSectionImporter,
                ]

    def update(self):
        if "UPDATE_SUBMIT" not in self.request:
            return

        xlsfile = self.request.get('xlsfile', '')
        if not xlsfile:
            return
        self.data_provided = True

        try:
            wb = xlrd.open_workbook(file_contents=xlsfile.read())
        except (xlrd.XLRDError,):
            self.is_xls = False
            wb = None

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
        return not self.data_provided or self.errors or not self.is_xls

    def displayErrors(self):
        if not self.data_provided:
            return [self.errorSummary()]
        if not self.is_xls:
            return [ERROR_NOT_XLS]
        ERROR_FMT = _('${sheet_name} ${column}${row} ${message}')
        errors = []
        for sheet_name, row, col, message in self.errors[:25]:
            full_message = format_message(
                ERROR_FMT,
                {'sheet_name': sheet_name,
                 'column': chr(col + ord('A')),
                 'row': row + 1,
                 'message': message}
                )
            errors.append(full_message)
        return errors

    def errorSummary(self):
        if not self.data_provided:
            return _('No data provided')
        if not self.is_xls:
            return ERROR_NOT_XLS
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


def createFile(file_upload):
    file = zope.file.file.File()
    zope.file.upload.updateBlob(file, file_upload)
    file.__name__ = file_upload.filename
    return file


class FlourishRemoteMegaImporter(flourish.page.Page):

    task = None
    message_b64 = None
    form_params = None
    render_invariant = False

    def __init__(self, context, request):
        flourish.page.Page.__init__(self, context, request)
        self.errors = []
        self.success = []

    @property
    def message(self):
        if not self.message_b64:
            return None
        message = get_message_by_id(self.message_b64.decode('base64').decode('utf-8'))
        return message

    def nextURL(self):
        message = self.message
        if message is not None:
            return absoluteURL(message, self.request)
        url = absoluteURL(self.context, self.request)
        return '%s/manage' % url

    def update(self):
        self.form_params = {}

        if not self.message_b64:
            self.message_b64 = self.request.get('message_id', '')

        if ("UPDATE_CANCEL" in self.request or
            "UPDATE_DONE" in self.request):
            self.request.response.redirect(self.nextURL())
            return

        if "UPDATE_SUBMIT" in self.request:
            self.scheduleImport()
            self.request.response.redirect(self.nextURL())
            return

    @property
    def message_dialog(self):
        message = self.message
        if message is None:
            return None
        content = queryMultiAdapter(
            (message, self.request, self), name='long')
        return content

    def scheduleImport(self):
        xls_upload = self.request.get('xls_file', '')
        if not xls_upload:
            self.errors.append(_('No data provided'))
            return

        app = ISchoolToolApplication(None)
        task = ImportTask(RemoteMegaImporter, app)
        task.request_params.update(self.form_params)
        task.schedule(self.request)
        message = query_message(task)
        self.message_b64 = message.__name__.encode('utf-8').encode('base64').strip()


class ImportProgress(TaskProgress):

    def __init__(self, importers, task_id):
        self.importers = importers
        TaskProgress.__init__(self, task_id)

    def reset(self):
        TaskProgress.reset(self)
        for n, importer in enumerate(self.importers):
            self.add(str(n), title=importer.title, active=False)
        self.add('overall', title=_('Overall'), active=True)


class OldeImportProgress(Timer):

    importers = None
    value = None
    task_status = None

    def __init__(self, importers, task_id):
        self.importers = importers
        self.task_status = TaskWriteState(task_id)
        Timer.__init__(self)

    def reset(self):
        Timer.reset(self)
        self.value = {}
        for n, importer in enumerate(self.importers):
            self.value[n] = {
                'title': importer.title,
                'errors': [],
                'progress': 0.0,
                }
        self.value['overall'] = {
                'title': _('Overall'),
                'errors': [],
                'progress': 0.0,
                }
        self.tock()

    def finish(self):
        for status in self.value.values():
            status['progress'] = 1.0
        self.task_status.set_progress(self.value)
        self.last_updated = self.now

    def tick(self, importer_n, value):
        self.value[importer_n]['progress'] = value
        self.value['overall']['progress'] = normalized_progress(
            importer_n, len(self.importers), value, 1.0)

    def tock(self, *args, **kw):
        self.task_status.set_progress(self.value)


class RemoteMegaImporter(MegaImporter):

    message_title = _('import spreadsheet')

    def update(self):
        remote_task = self.request.task

        total_importers = len(self.importers)
        importers = self.importers

        progress = ImportProgress(self.importers, self.request.task_id)

        xls = remote_task.xls_file.open()
        wb = xlrd.open_workbook(file_contents=xls.read())
        xls.close()

        if wb is None:
            progress.finish('overall')
            return progress.lines

        progress('overall', active=True)
        savepoint = transaction.savepoint(optimistic=True)
        for importer_n, importer in enumerate(importers):
            importer_lid = str(importer_n)
            for lid in progress.lines:
                if lid == importer_lid:
                    progress(lid, active=True, progress=0.0)
                elif lid == 'overall':
                    progress(lid, active=True)
                else:
                    progress(lid, active=False)

            def import_progress(value):
                progress(importer_lid, progress=value, active=True)
                progress('overall', progress=normalized_progress(
                    importer_n, total_importers, value, 1.0), active=True)

            imp = importer(
                self.context, self.request,
                progress_callback=import_progress)
            imp.import_data(wb)

            for error in imp.errors:
                progress.error(importer_lid, error)
                progress.error('overall', error)
                self.errors.append(error)

            progress.finish(importer_lid)

        if progress['overall']['errors']:
            savepoint.rollback()

        progress.finish('overall')
        return progress.lines

    def __call__(self):
        return self.update()


class ImporterTask(RemoteTask):
    implements(IImporterTask)

    routing_key = "zodb.report"

    xls_file = None

    def __init__(self, xls_file):
        RemoteTask.__init__(self)
        self.xls_file = xls_file

    def execute(self, request):
        app = ISchoolToolApplication(None)
        importer = RemoteMegaImporter(app, request)
        result = importer()
        return result


class ImportFile(ReportFile):
    implements(IImportFile)

    errors = None


class ImportTask(AbstractReportTask):
    implements(IImporterTask, IReportTask)

    default_mimetype = "application/xls"
    default_filename = "import.xls"

    xls_file = None
    errors = None

    def update(self, request):
        file_upload = request['xls_file']
        self.xls_file = ImportFile()
        self.xls_file.mimeType = self.default_mimetype
        filename = file_upload.filename or self.default_filename
        self.request_params['filename'] = filename
        self.xls_file.__name__ = filename
        stream = self.xls_file.open('w')
        stream.write(file_upload.read())
        stream.close()
        AbstractReportTask.update(self, request)

    def renderReport(self, renderer, stream, *args, **kw):
        return renderer()

    def renderToFile(self, renderer, *args, **kw):
        report = self.xls_file
        try:
            stream = None
            self.renderReport(renderer, stream, *args, **kw)
        except NoReportException:
            return None
        self.updateReport(renderer, report)
        report.errors = renderer.errors
        return report


class ImportProgressMessage(ReportProgressMessage):

    group = _('Import')
    default_filename = "import.xls"


class OnImportScheduled(TaskScheduledNotification):

    view = None
    message_factory = ImportProgressMessage

    def __init__(self, task, request, view):
        super(OnImportScheduled, self).__init__(task, request)
        self.view = view

    @property
    def filename(self):
        xls_file = self.task.xls_file
        if xls_file is None:
            return None
        return xls_file.__name__

    def makeReportTitle(self):
        title = getattr(self.view, 'message_title', None)
        if not title:
            self.title = self.filename
        if not title:
            title = _(u'XLS import')
        return title

    def send(self):
        view = self.view
        view.render_invariant = True
        task = self.task
        title = self.makeReportTitle()
        msg = self.message_factory(
            title=title,
            requested_on=task.scheduled,
            filename=self.filename,
            )
        msg.send(sender=task, recipients=[self.task.creator])


class IImportForm(Interface):

    xls_file = zope.schema.Bytes(
        title=_('Photo'),
        description=_('An image file that will be converted to a JPEG no larger than 99x132 pixels (3:4 aspect ratio). Uploaded images must be JPEG or PNG files smaller than 10 MB'),
        )


class RequestImportDialog(RequestRemoteReportDialog):

    task_factory = ImportTask

    fields = z3c.form.field.Fields(IImportForm)

    @z3c.form.button.buttonAndHandler(_("Import"), name='download')
    def handle_import(self, action):
        RequestRemoteReportDialog.handleDownload.func(self, action)

    @z3c.form.button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        pass


class ImportProgressPage(flourish.page.PageBase):

    @Lazy
    def status(self):
        return TaskReadState(self.task_id)

    @property
    def progress_id(self):
        return flourish.page.sanitize_id('progress-%s' % self.context.task_id)

    @property
    def importers(self):
        if self.status.progress is None:
            return []
        result = []
        for k, progress in self.status.progress.items():
            if k == 'overall':
                continue
            result.append(progress)
        return result

    @property
    def overall(self):
        if self.status.progress is None:
            return None
        return self.status.progress['overall']

    @property
    def task_id(self):
        return self.context.task_id


class ImportProgressContent(flourish.page.Content, ImportProgressPage):
    pass


class DownloadFile(BrowserView):

    attribute = None
    inline = False

    @property
    def file_object(self):
        return getattr(self.context, self.attribute, None)

    def setUpResponse(self, data, filename):
        stored_file = self.file_object
        response = self.request.response
        if stored_file.mimeType:
            response.setHeader('Content-Type', stored_file.mimeType)
        response.setHeader('Content-Length', len(data))
        disposition = self.inline and 'inline' or 'attachment'
        if filename:
            disposition += '; filename="%s"' % filename
        response.setHeader('Content-Disposition', disposition)

    def __call__(self):
        stored_file = self.file_object
        if stored_file is None:
            return None
        filename = getattr(stored_file, '__name__', '')
        filename = urllib.quote(filename.encode('UTF-8'))
        f = stored_file.open()
        data = f.read()
        f.close()

        self.setUpResponse(data, filename)

        return data


class DownloadImportXLS(DownloadFile):

    attribute = "xls_file"
    inline = False


class ImportFinishedMessage(GeneratedReportMessage):

    group = _('Import')
    default_filename = "import.xls"


class OnImportFinished(OnReportGenerated):

    message_factory = ImportFinishedMessage


class ImportFinishedLong(flourish.page.PageBase):

    template = flourish.templates.File('templates/f_import_finished_long.pt')
    refresh_delay = 10000

    @Lazy
    def form_id(self):
        return flourish.page.obj_random_html_id(self)

    @property
    def report(self):
        return getattr(self.context, 'report', None)

    @property
    def report_generated(self):
        return bool(self.report)

    @property
    def main_recipient(self):
        person = IPerson(self.request, None)
        if self.context.recipients is None:
            return None
        recipients = sorted(self.context.recipients, key=lambda r: r.__name__)
        if person in recipients:
            return person
        for recipient in recipients:
            if flourish.canView(recipient):
                return recipient
        return None

    @Lazy
    def failure_ticket_id(self):
        sender = self.context.sender
        if (IRemoteTask.providedBy(sender) and
            sender.failed):
            return sender.__name__
        return None

    @Lazy
    def failed_task(self):
        sender = self.context.sender
        if (IRemoteTask.providedBy(sender) and
            sender.failed):
            return sender
        return None

    @Lazy
    def errors(self):
        error_lines = []
        if (self.report is None or
            not self.report.errors):
            return error_lines
        errors = {}
        for sheet_name, row, col, message in self.report.errors:
            sheet_errors = errors.setdefault(sheet_name, {})
            sheet_errors.setdefault(message, []).append((col, row))
        for sheet_name, message_errors in sorted(errors.items()):
            error_lines.append({'sheetname': sheet_name})
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
                error_cells = []
                for col, start, end in col_rows:
                    cell = chr(col + ord('A'))
                    if start == end:
                        cell += '%s' % (start + 1)
                    else:
                        cell += '%s-%s' % (start + 1, end + 1)
                    error_cells.append(cell)
                error_lines.append({
                    'message': translate(message),
                    'cells': ', '.join(error_cells),
                    })
        return error_lines


class ImportMessageShort(flourish.content.ContentProvider):

    @Lazy
    def failure_ticket_id(self):
        sender = self.context.sender
        if (IRemoteTask.providedBy(sender) and
            sender.failed):
            return sender.__name__
        return None
