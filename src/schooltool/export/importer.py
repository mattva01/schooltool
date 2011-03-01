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

from zope.container.interfaces import INameChooser
from zope.component import queryUtility
from zope.security.proxy import removeSecurityProxy
from zope.publisher.browser import BrowserView

from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.interfaces import IDemographics
from schooltool.basicperson.demographics import DateFieldDescription
from schooltool.basicperson.person import BasicPerson
from schooltool.resource.resource import Resource
from schooltool.resource.resource import Location
from schooltool.group.group import Group
from schooltool.group.interfaces import IGroupContainer
from schooltool.term.interfaces import ITerm
from schooltool.term.term import Term
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.app import SimpleNameChooser
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer

from schooltool.course.section import Section
from schooltool.course.interfaces import ISectionContainer
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.course import Course
from schooltool.common import DateRange

from schooltool.common import format_message
from schooltool.common import SchoolToolMessage as _


ERROR_FMT = _('${sheet_name} ${column}${row} ${message}')
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
ERROR_RESOURCE_TYPE = _("must be either 'Location' or 'Resource'")
ERROR_INVALID_TERM_ID = _('is not a valid term in the given school year')
ERROR_INVALID_COURSE_ID = _('is not a valid course in the given school year')
ERROR_HAS_NO_COURSES = _('${title} has no courses in A${row}')
ERROR_INVALID_PERSON_ID = _('is not a valid username')
ERROR_INVALID_SCHEMA_ID = _('is not a valid schema in the given school year')
ERROR_INVALID_DAY_ID = _('is not a valid day id for the given schema')
ERROR_INVALID_PERIOD_ID = _('is not a valid period id for the given day')
ERROR_INVALID_RESOURCE_ID = _('is not a valid resource id')
ERROR_UNICODE_CONVERSION = _(
    "Username cannot contain non-ascii characters: ${string}")
ERROR_WEEKLY_DAY_ID = _('is not a valid weekday number (0-6)')


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
        full_message = format_message(
            ERROR_FMT,
            {'sheet_name': self.sheet_name,
             'column': chr(col + ord('A')),
             'row': row + 1,
             'message': message}
            )
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
            if isinstance(value, str):
                try:
                    value = unicode(value)
                except UnicodeError:
                    self.error(row, col, ERROR_NOT_UNICODE_OR_ASCII)
                    valid = False
            elif not isinstance(value, unicode):
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
        try:
            dt = xlrd.xldate_as_tuple(sheet.cell_value(rowx=row, colx=col), self.wb.datemode)
        except:
            if default is not no_date:
                return default
            else:
                self.error(row, col, ERROR_NO_DATE)
                return None
        return datetime.datetime(*dt).date()

    @property
    def sheet(self):
        if self.sheet_name not in self.wb.sheet_names():
            return
        return self.wb.sheet_by_name(self.sheet_name)

    def import_data(self, wb):
        self.wb = wb
        if self.sheet:
            return self.process()


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


    def setUpSchemaDays(self, timetable, days):
        # XXX: temporary isolation of timetable imports
        from schooltool.timetable.schema import TimetableSchemaDay

        for day in days:
            day_id = day['id']
            timetable[day_id] = TimetableSchemaDay(day['periods'],
                                                   day['homeroom_periods'])

    def createSchoolTimetable(self, data):
        # XXX: temporary isolation of timetable imports
        from schooltool.timetable.interfaces import ITimetableModelFactory
        from schooltool.timetable import SchooldayTemplate
        from schooltool.timetable.schema import TimetableSchema
        from schooltool.timetable import SchooldaySlot

        title = data['title']
        factory = queryUtility(ITimetableModelFactory, data['model'])
        day_ids = [day['id'] for day in data['days']]

        template_dict = {}

        for template in data['templates']:
            used = template['id']

            # parse SchoolDayPeriods
            day = SchooldayTemplate()
            for tstart, duration in template['periods']:
                slot = SchooldaySlot(tstart, duration)
                day.add(slot)

            if used == 'default':
                template_dict[None] = day
            elif used in day_ids:
                template_dict[used] = day
            else:
                try:
                    template_dict[self.dows.index(used)] = day
                except ValueError:
                    self.errors.append("Unrecognised day id %s" % used)

        model = factory(day_ids, template_dict)

        # create and set up the timetable
        timetable = TimetableSchema(day_ids, title=title, model=model)
        self.setUpSchemaDays(timetable, data['days'])
        timetable.__name__ = data['__name__']
        return timetable

    def addSchoolTimetable(self, school_timetable, data):
        # XXX: temporary isolation of timetable imports
        from schooltool.timetable.interfaces import ITimetableSchemaContainer

        syc = ISchoolYearContainer(self.context)
        sy = syc[data['school_year']]
        sc = ITimetableSchemaContainer(sy)
        if school_timetable.__name__ is None:
            school_timetable.__name__ = SimpleNameChooser(sc).chooseName('', school_timetable)

        if school_timetable.__name__ not in sc:
            sc[school_timetable.__name__] = school_timetable

    def getWeeklyDayId(self, sh, row, col):
        if sh.cell_value(rowx=row, colx=col) == 'default':
            day_id = 'default'
        else:
            day_id, found, valid = self.getIntFoundValid(sh, row, col)
            if valid and day_id not in range(7):
                self.error(row, col, ERROR_WEEKLY_DAY_ID)
        return day_id

    def import_school_timetable(self, sh, row):
        # XXX: temporary isolation of timetable imports
        from schooltool.timetable.interfaces import ITimetableModelFactory
        from schooltool.common import parse_time_range

        num_errors = len(self.errors)
        data = {}
        data['title'] = self.getRequiredTextFromCell(sh, row, 1)
        data['__name__'] = self.getRequiredTextFromCell(sh, row+1, 1)
        data['school_year'] = self.getRequiredTextFromCell(sh, row+2, 1)
        data['model'] = self.getRequiredTextFromCell(sh, row+3, 1)
        if num_errors < len(self.errors):
            return

        num_errors = len(self.errors)
        if data['school_year'] not in ISchoolYearContainer(self.context):
            self.error(row + 2, 1, ERROR_INVALID_SCHOOL_YEAR)
        if queryUtility(ITimetableModelFactory, data['model']) is None:
            self.error(row + 3, 1, ERROR_TIMETABLE_MODEL)
        if num_errors < len(self.errors):
            return

        num_errors = len(self.errors)
        row += 5
        if self.getCellValue(sh, row, 0, '') == 'Day Templates':
            data['templates'] = []
            row += 1
            for row in range(row, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break

                if data['model'] == 'WeeklyTimetableModel':
                    day_id = self.getWeeklyDayId(sh, row, 0)
                else:
                    day_id = self.getRequiredTextFromCell(sh, row, 0)

                if day_id in [day['id'] for day in data['templates']]:
                    self.error(row, 0, ERROR_DUPLICATE_DAY_ID)

                periods = []
                for col in range(1, sh.ncols):
                    cell = sh.cell_value(rowx=row, colx=col)
                    if cell == '':
                        break
                    try:
                        time_range = parse_time_range(cell)
                    except:
                        self.error(row, col, ERROR_TIME_RANGE)
                        continue
                    periods.append(time_range)
                data['templates'].append({'id': day_id, 'periods': periods})
        else:
            self.errors.append(format_message(
                ERROR_HAS_NO_DAY_TEMPLATES,
                mapping={'title': data['title'], 'row': row + 1}
                ))
        if num_errors < len(self.errors):
            return

        row += 1
        if self.getCellValue(sh, row, 0, '') == 'Days':
            data['days'] = []
            homeroom_start = sh.ncols
            for col in range(2, sh.ncols):
                if sh.cell_value(rowx=row, colx=col) == 'Homeroom periods':
                    homeroom_start = col
                    break
            row += 1
            for row in range(row, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break

                if data['model'] == 'WeeklyTimetableModel':
                    day_id = self.getWeeklyDayId(sh, row, 0)
                else:
                    day_id = self.getRequiredTextFromCell(sh, row, 0)

                if day_id in [day['id'] for day in data['days']]:
                    self.error(row, 0, ERROR_DUPLICATE_DAY_ID)
                if day_id not in [day['id'] for day in data['templates']]:
                    self.error(row, 0, ERROR_UNKNOWN_DAY_ID)

                periods = []
                for col in range(1, homeroom_start):
                    cell = sh.cell_value(rowx=row, colx=col)
                    if cell == '':
                        break
                    if cell in periods:
                        self.error(row, col, ERROR_DUPLICATE_PERIOD)
                    else:
                        periods.append(cell)
                homeroom_periods = []
                for col in range(homeroom_start, sh.ncols):
                    cell = sh.cell_value(rowx=row, colx=col)
                    if cell == '':
                        break
                    if cell in homeroom_periods:
                        self.error(row, col, ERROR_DUPLICATE_HOMEROOM_PERIOD)
                    else:
                        homeroom_periods.append(cell)
                data['days'].append({'id': day_id,
                                     'periods': periods,
                                     'homeroom_periods': homeroom_periods})
        else:
            self.errors.append(format_message(
                ERROR_HAS_NO_DAYS,
                mapping={'title': data['title'], 'row': row + 1}
                ))

        if not self.errors:
            school_timetable = self.createSchoolTimetable(data)
            self.addSchoolTimetable(school_timetable, data)

    def process(self):
        sh = self.sheet
        for row in range(0, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == 'School Timetable':
                self.import_school_timetable(sh, row)


class ResourceImporter(ImporterBase):

    sheet_name = 'Resources'

    def createResource(self, data):
        res_types = {'Location': Location,
                     'Resource': Resource}
        res_factory = res_types[data['type']]
        resource = res_factory(data['title'])
        resource.__name__ = data['__name__']
        return resource

    def addResource(self, resource, data):
        rc = self.context['resources']
        if resource.__name__ in rc:
            resource = rc[resource.__name__]
            resource.title = data['title']
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
            if num_errors < len(self.errors):
                continue
            if data['type'] not in ['Location', 'Resource']:
                self.error(row, 1, ERROR_RESOURCE_TYPE)
                continue
            resource = self.createResource(data)
            self.addResource(resource, data)


class PersonImporter(ImporterBase):

    sheet_name = 'Persons'

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
        app = ISchoolToolApplication(None)
        fields = IDemographicsFields(app)
        for row in range(1, sh.nrows):
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
            data['password'] = self.getTextFromCell(sh, row, 9)

            # XXX: this has to be fixed
            # XXX: SchoolTool should handle UTF-8
            try:
                data['__name__'].encode('ascii')
            except UnicodeEncodeError:
                self.error(
                    row, 0,
                    format_message(
                        ERROR_UNICODE_CONVERSION,
                        mapping={'string': data['__name__']})
                    )

            if num_errors == len(self.errors):
                person = self.createPerson(data)
            else:
                person = BasicPerson('name', 'first_name', 'last_name')

            demographics = IDemographics(person)
            for n, field in enumerate(fields.values()):
                if isinstance(field, DateFieldDescription):
                    value = self.getDateFromCell(sh, row, n + 10, default=None)
                else:
                    value = self.getTextFromCell(sh, row, n + 10)
                if value == '':
                    value = None
                demographics[field.name] = value

            if num_errors == len(self.errors):
                self.addPerson(person, data)


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
            if num_errors < len(self.errors):
                continue
            if data['school_year'] not in ISchoolYearContainer(self.context):
                self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
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

    def import_timetable(self, sh, row, section):
        # XXX: temporary isolation of timetable imports
        from schooltool.timetable.interfaces import ITimetableSchemaContainer
        from schooltool.timetable.interfaces import ITimetables
        from schooltool.timetable import TimetableActivity
        from schooltool.timetable.interfaces import ITimetableCalendarEvent

        schemas = ITimetableSchemaContainer(ISchoolYear(section))
        schema_id = self.getRequiredTextFromCell(sh, row, 1)
        if schema_id not in schemas:
            self.error(row, 0, ERROR_INVALID_SCHEMA_ID)
            return
        schema = schemas[schema_id]
        timetable = schema.createTimetable(ITerm(section))
        timetables = ITimetables(section).timetables
        timetables[schema_id] = timetable

        row += 1
        course = list(section.courses)[0]
        rc = self.context['resources']
        resources = {}
        for row in range(row + 1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            num_errors = len(self.errors)
            day_id = self.getRequiredTextFromCell(sh, row, 0)
            period_id = self.getRequiredTextFromCell(sh, row, 1)
            resource_id = self.getTextFromCell(sh, row, 2)
            if num_errors < len(self.errors):
                continue

            if day_id not in schema.day_ids:
                self.error(row, 0, ERROR_INVALID_DAY_ID)
            elif period_id not in schema[day_id].periods:
                self.error(row, 1, ERROR_INVALID_PERIOD_ID)
            if resource_id and resource_id not in rc:
                self.error(row, 2, ERROR_INVALID_RESOURCE_ID)
            if num_errors < len(self.errors):
                continue

            resources[day_id, period_id] = resource_id
            act = TimetableActivity(title=course.title, owner=section)
            timetable[day_id].add(period_id, act)

        for event in ISchoolToolCalendar(section):
            if ITimetableCalendarEvent.providedBy(event):
                resource_id = resources[event.day_id, event.period_id]
                resource = rc[resource_id]
                event.bookResource(removeSecurityProxy(resource))

    def import_timetables(self, sh, row, section):
        for row in range(row, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == 'School Timetable':
                self.import_timetable(sh, row, section)
            if sh.cell_value(rowx=row, colx=0) == '':
                break
        return row

    def import_section(self, sh, row, year, term):
        data = {}
        data['title'] = self.getRequiredTextFromCell(sh, row, 1)
        data['__name__'] = self.getRequiredTextFromCell(sh, row+1, 1)
        data['description'] = self.getTextFromCell(sh, row+2, 1)

        section = self.createSection(data, year, term)
        self.addSection(section, data, year, term)
        courses = ICourseContainer(section)

        row += 4
        if sh.cell_value(rowx=row, colx=0) == 'Courses':
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
        else:
            self.errors.append(format_message(
                ERROR_HAS_NO_COURSES,
                mapping={'title': data['title'], 'row': row + 1}
                ))
            return

        persons = self.context['persons']
        if sh.cell_value(rowx=row, colx=0) == 'Students':
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
            row += 1

        if sh.cell_value(rowx=row, colx=0) == 'Instructors':
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
            row += 1

        if sh.cell_value(rowx=row, colx=0) == 'School Timetable':
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
            if sheet_name.startswith('Section'):
                self.sheet_names.append(sheet_name)
        if self.sheet_names:
            self.process()


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
        if sh.cell_value(rowx=row, colx=0) == 'Members':
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
        self.errors = []
        self.success = []

    def getWorkbook(self):
        xlsfile = self.request.get('xlsfile', '')
        if xlsfile:
            xlsfile = xlsfile.read()

        if not xlsfile:
            self.errors.append(_('No data provided'))
            return

        book = xlrd.open_workbook(file_contents=xlsfile)
        return book

    def update(self):
        if "UPDATE_SUBMIT" not in self.request:
            return

        wb = self.getWorkbook()

        sp = transaction.savepoint(optimistic=True)

        importers = [SchoolYearImporter,
                     TermImporter,
                     SchoolTimetableImporter,
                     ResourceImporter,
                     PersonImporter,
                     CourseImporter,
                     SectionImporter,
                     GroupImporter]

        for importer in importers:
            imp = importer(self.context, self.request)
            imp.import_data(wb)
            self.errors.extend(imp.errors)

        if self.errors:
            sp.rollback()

    def displayErrors(self):
        return self.errors[:25]

