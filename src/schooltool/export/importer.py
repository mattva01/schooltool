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

from zope.app.container.interfaces import INameChooser
from zope.component import queryUtility
from zope.security.proxy import removeSecurityProxy
from zope.publisher.browser import BrowserView

from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.interfaces import IDemographics
from schooltool.basicperson.demographics import DateFieldDescription
from schooltool.resource.resource import Resource
from schooltool.resource.resource import Location
from schooltool.group.group import Group
from schooltool.group.interfaces import IGroupContainer
from schooltool.timetable import TimetableActivity
from schooltool.timetable import SchooldaySlot
from schooltool.timetable import SchooldayTemplate
from schooltool.timetable.browser import parse_time_range
from schooltool.timetable.interfaces import ITimetableCalendarEvent
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable.interfaces import ITimetableSchemaContainer
from schooltool.timetable.interfaces import ITimetableModelFactory
from schooltool.timetable.schema import TimetableSchema
from schooltool.timetable.schema import TimetableSchemaDay
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
from schooltool.common import SchoolToolMessage as _


no_date = object()

class ImporterBase(object):

    def __init__(self, context, request):
        self.context, self.request = context, request
        self.errors = []

    def error(self, col, row, message):
        self.errors.append("%s %s%s %s" % (self.sheet_name,
                                           chr(col + ord('A')),
                                           row,
                                           message))

    def getDateFromCell(self, sheet, row, col, default=no_date):
        try:
            dt = xlrd.xldate_as_tuple(sheet.cell_value(rowx=row, colx=col), self.wb.datemode)
        except:
            if default is not no_date:
                return default
            else:
                self.error(col, row + 1, "has no date in it!")
                return datetime.datetime.utcnow().date()
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
        sy = SchoolYear(data['title'], data['first'], data['last'])
        sy.__name__ = data['__name__']
        return sy

    def addSchoolYear(self, sy, data):
        syc = ISchoolYearContainer(self.context)
        if sy.__name__ is None:
            sy.__name__ = SimpleNameChooser(syc).chooseName('', sy)
        syc[sy.__name__] = sy

    def process(self):
        sh = self.sheet
        for row in range(1, sh.nrows):
            data = {}
            data['title'] = sh.cell_value(rowx=row, colx=0)
            data['__name__'] = sh.cell_value(rowx=row, colx=1)
            data['first'] = self.getDateFromCell(sh, row, 2)
            data['last'] = self.getDateFromCell(sh, row, 3)
            sy = self.createSchoolYear(data)
            self.addSchoolYear(sy, data)


class TermImporter(ImporterBase):

    sheet_name = 'Terms'

    def createTerm(self, data):
        term = Term(data['title'], data['first'], data['last'])
        term.__name__ = data['__name__']
        term.addWeekdays(*range(7))
        return term

    def addTerm(self, term, data):
        syc = ISchoolYearContainer(self.context)
        sy = syc[data['school_year']]
        if term.__name__ is None:
            term.__name__ = SimpleNameChooser(sy).chooseName('', term)
        sy[term.__name__] = term

    def process(self):
        sh = self.sheet

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break
            data = {}
            data['school_year'] = sh.cell_value(rowx=row, colx=0)
            data['__name__'] = sh.cell_value(rowx=row, colx=1)
            data['title'] = sh.cell_value(rowx=row, colx=2)
            data['first'] = self.getDateFromCell(sh, row, 3)
            data['last'] = self.getDateFromCell(sh, row, 4)

            term = self.createTerm(data)
            self.addTerm(term, data)

        row += 1
        if sh.cell_value(rowx=row, colx=0) == 'Holidays':
            row += 1
            for row in range(row + 1, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break
                holiday_region = DateRange(self.getDateFromCell(sh, row, 0),
                                           self.getDateFromCell(sh, row, 1))
                for day in holiday_region:
                    for sy in ISchoolYearContainer(self.context).values():
                        for term in sy.values():
                            if day in term:
                                term.remove(day)

        row += 1
        if sh.cell_value(rowx=row, colx=0) == 'Weekends':
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
        for day in days:
            day_id = day['id']
            period_ids = [period
                          for period in day['periods']]
            if len(set(period_ids)) != len(period_ids):
                self.errors.append("Duplicate periods in schema: %s" % period_ids)

            homeroom_periods = [period
                                for period in day['homeroom_periods']]

            timetable[day_id] = TimetableSchemaDay(period_ids, homeroom_periods)

    def createSchoolTimetable(self, data):
        day_ids = [day['id'] for day in data['days']]

        factory_id = data['model']
        title = data['title']

        factory = queryUtility(ITimetableModelFactory, factory_id)
        if factory is None:
            self.errors.append("Incorrect timetable model factory")

        templates = data['templates']
        template_dict = {}

        for template in templates:
            day = SchooldayTemplate()

            used = template['id']

            # parse SchoolDayPeriods
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
        if len(set(day_ids)) != len(day_ids):
            self.errors.append("Duplicate days in schema")

        timetable = TimetableSchema(day_ids, title=title, model=model)
        self.setUpSchemaDays(timetable, data['days'])
        timetable.__name__ = data['__name__']
        return timetable

    def addSchoolTimetable(self, school_timetable, data):
        syc = ISchoolYearContainer(self.context)
        sy = syc[data['school_year']]
        sc = ITimetableSchemaContainer(sy)
        if school_timetable.__name__ is None:
            school_timetable.__name__ = SimpleNameChooser(sc).chooseName('', school_timetable)

        if school_timetable.__name__ not in sc:
            sc[school_timetable.__name__] = school_timetable

    def import_school_timetable(self, sh, row):
        data = {}
        data['title'] = sh.cell_value(rowx=row, colx=1)
        data['__name__'] = sh.cell_value(rowx=row+1, colx=1)
        data['school_year'] = sh.cell_value(rowx=row+2, colx=1)
        data['model'] = sh.cell_value(rowx=row+3, colx=1)

        row += 5
        if sh.cell_value(rowx=row, colx=0) == 'Day Templates':
            data['templates'] = []
            row += 1
            for row in range(row, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break
                day_id = sh.cell_value(rowx=row, colx=0)
                periods = []
                for col in range(1, sh.ncols):
                    if sh.cell_value(rowx=row, colx=col) == '':
                        break
                    periods.append(parse_time_range(sh.cell_value(rowx=row, colx=col)))
                data['templates'].append({'id': day_id, 'periods': periods})
        else:
            self.errors.append("%s has no day templates in A%s" % (data['title'], row + 1))

        row += 1
        if sh.cell_value(rowx=row, colx=0) == 'Days':
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
                day_id = sh.cell_value(rowx=row, colx=0)
                periods = []
                for col in range(1, homeroom_start):
                    if sh.cell_value(rowx=row, colx=col) == '':
                        break
                    periods.append(sh.cell_value(rowx=row, colx=col))
                homeroom_periods = []
                for col in range(homeroom_start, sh.ncols):
                    if sh.cell_value(rowx=row, colx=col) == '':
                        break
                    homeroom_periods.append(sh.cell_value(rowx=row, colx=col))
                data['days'].append({'id': day_id,
                                     'periods': periods,
                                     'homeroom_periods': homeroom_periods})
        else:
            self.errors.append("%s has no days in A%s" % (data['title'], row + 1))

        school_timetable = self.createSchoolTimetable(data)
        self.addSchoolTimetable(school_timetable, data)

        return row

    def process(self):
        sh = self.sheet
        for row in range(0, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == 'School Timetable':
                row = self.import_school_timetable(sh, row)


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
            data = {}
            data['__name__'] = sh.cell_value(rowx=row, colx=0)
            data['type'] = sh.cell_value(rowx=row, colx=1)
            data['title'] = sh.cell_value(rowx=row, colx=2)
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
        from schooltool.basicperson.person import BasicPerson
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
            data = {}
            data['__name__'] = sh.cell_value(rowx=row, colx=0)
            data['prefix'] = sh.cell_value(rowx=row, colx=1)
            data['first_name'] = sh.cell_value(rowx=row, colx=2)
            data['middle_name'] = sh.cell_value(rowx=row, colx=3)
            data['last_name'] = sh.cell_value(rowx=row, colx=4)
            data['suffix'] = sh.cell_value(rowx=row, colx=5)
            data['preferred_name'] = sh.cell_value(rowx=row, colx=6)
            data['birth_date'] = self.getDateFromCell(sh, row, 7, default=None)
            data['gender'] = sh.cell_value(rowx=row, colx=8)
            if data['gender'] == '':
                data['gender'] = None
            data['password'] = sh.cell_value(rowx=row, colx=9)

            person = self.createPerson(data)

            demographics = IDemographics(person)
            for n, field in enumerate(fields.values()):
                if isinstance(field, DateFieldDescription):
                    value = self.getDateFromCell(sh, row, n + 10, default=None)
                else:
                    value = sh.cell_value(rowx=row, colx=n + 10)
                if value == '':
                    value = None
                demographics[field.name] = value

            self.addPerson(person, data)


class CourseImporter(ImporterBase):

    sheet_name = 'Courses'

    def createCourse(self, data):
        course = Course(data['title'], data['description'])
        course.__name__ = data['__name__']
        return course

    def addCourse(self, course, data):
        syc = ISchoolYearContainer(self.context)
        cc = ICourseContainer(syc[data['school_year']])
        if course.__name__ is None:
            course.__name__ = SimpleNameChooser(cc).chooseName('', course)
        cc[course.__name__] = course

    def process(self):
        sh = self.sheet
        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break
            data = {}
            data['school_year'] = sh.cell_value(rowx=row, colx=0)
            data['__name__'] = sh.cell_value(rowx=row, colx=1)
            data['title'] = sh.cell_value(rowx=row, colx=2)
            data['description'] = sh.cell_value(rowx=row, colx=3)
            course = self.createCourse(data)
            self.addCourse(course, data)


class SectionImporter(ImporterBase):

    sheet_name = 'Sections'

    def createSection(self, data):
        syc = ISchoolYearContainer(self.context)
        sy = syc[data['school_year']]
        term = sy[data['term']]
        sc = ISectionContainer(term)
        if data['__name__'] in sc:
            section = sc[data['__name__']]
            section.title = data['title']
            section.description = data['description']
        else:
            section = Section(data['title'], data['description'])
            section.__name__ = data['__name__']
        return section

    def addSection(self, section, data):
        syc = ISchoolYearContainer(self.context)
        sy = syc[data['school_year']]
        term = sy[data['term']]
        sc = ISectionContainer(term)
        if section.__name__ is None:
            section.__name__ = SimpleNameChooser(sc).chooseName('', section)

        if section.__name__ not in sc:
            sc[section.__name__] = section

    def import_timetable(self, sh, row, section):
        schema_id = sh.cell_value(rowx=row, colx=1)
        schema = ITimetableSchemaContainer(ISchoolYear(section))[schema_id]
        course = list(section.courses)[0]
        timetable = schema.createTimetable(ITerm(section))
        timetables = ITimetables(section).timetables
        timetables[schema_id] = timetable
        resources = {}
        for row in range(row + 1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break
            day_id = sh.cell_value(rowx=row, colx=0)
            period_id = sh.cell_value(rowx=row, colx=1)
            resources[day_id, period_id] = sh.cell_value(rowx=row, colx=2)
            act = TimetableActivity(title=course.title, owner=section)
            timetable[day_id].add(period_id, act)
        rc = self.context['resources']
        for event in ISchoolToolCalendar(section):
            if ITimetableCalendarEvent.providedBy(event):
                resource_id = resources[event.day_id, event.period_id]
                resource = rc[resource_id]
                event.bookResource(removeSecurityProxy(resource))
        return row

    def import_timetables(self, sh, row, section):
        for row in range(row, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == 'School Timetable':
                self.import_timetable(sh, row, section)
            if sh.cell_value(rowx=row, colx=0) == '':
                break
        return row

    def import_section(self, sh, row):
        data = {}
        data['title'] = sh.cell_value(rowx=row, colx=1)
        data['__name__'] = sh.cell_value(rowx=row+1, colx=1)
        data['school_year'] = sh.cell_value(rowx=row+2, colx=1)
        data['term'] = sh.cell_value(rowx=row+3, colx=1)
        data['description'] = sh.cell_value(rowx=row+4, colx=1)
        section = self.createSection(data)
        self.addSection(section, data)

        row += 6
        if sh.cell_value(rowx=row, colx=0) == 'Courses':
            row += 1
            for row in range(row, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break
                course_id = sh.cell_value(rowx=row, colx=0)
                course = ICourseContainer(section)[course_id]
                section.courses.add(removeSecurityProxy(course))
        else:
            self.errors.append("%s has no courses in A%s" % (data['title'], row + 1))

        row += 1
        pc = self.context['persons']
        if sh.cell_value(rowx=row, colx=0) == 'Students':
            row += 1
            for row in range(row, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break
                username = sh.cell_value(rowx=row, colx=0)
                member = pc[username]
                section.members.add(removeSecurityProxy(member))

        row += 1
        if sh.cell_value(rowx=row, colx=0) == 'Instructors':
            row += 1
            for row in range(row, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break
                username = sh.cell_value(rowx=row, colx=0)
                instructor = pc[username]
                section.instructors.add(removeSecurityProxy(instructor))

        row += 1
        if sh.cell_value(rowx=row, colx=0) == 'Timetables':
            row += 1
            row = self.import_timetables(sh, row, section)

        return row

    def process(self):
        sh = self.sheet
        for row in range(0, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == 'Section*':
                row = self.import_section(sh, row)


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
        data = {}
        data['title'] = sh.cell_value(rowx=row, colx=1)
        data['__name__'] = sh.cell_value(rowx=row+1, colx=1)
        data['school_year'] = sh.cell_value(rowx=row+2, colx=1)
        data['description'] = sh.cell_value(rowx=row+3, colx=1)
        group = self.createGroup(data)
        self.addGroup(group, data)

        row += 5
        pc = self.context['persons']
        if sh.cell_value(rowx=row, colx=0) == 'Members':
            row += 1
            for row in range(row, sh.nrows):
                if sh.cell_value(rowx=row, colx=0) == '':
                    break
                username = sh.cell_value(rowx=row, colx=0)
                member = pc[username]
                group.members.add(removeSecurityProxy(member))
        return row

    def process(self):
        sh = self.sheet
        for row in range(0, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == 'Group*':
                row = self.import_group(sh, row)


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
