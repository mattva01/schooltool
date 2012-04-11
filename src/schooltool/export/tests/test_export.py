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
Tests for SchoolTool XLS export views.
"""
import unittest
import doctest
from datetime import date, time

from schooltool.basicperson.interfaces import IDemographics
from schooltool.basicperson.person import BasicPerson
from schooltool.person.person import Person
from schooltool.export.export import MegaExporter, merge_date_ranges
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.testing import format_table
from schooltool.term.term import Term
from schooltool.common import DateRange
from schooltool.contact.contact import Contact, ContactPersonInfo
from schooltool.contact.interfaces import IContact, IContactable
from schooltool.contact.interfaces import IContactContainer
from schooltool.course.course import Course
from schooltool.course.section import Section
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.interfaces import ISectionContainer
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.schoolyear.testing import provideStubUtility
from schooltool.schoolyear.testing import provideStubAdapter
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.export.ftesting import export_functional_layer
from schooltool.resource.resource import Location, Equipment
from schooltool.schoolyear.testing import setUp
from schooltool.schoolyear.testing import tearDown
from schooltool.timetable.interfaces import IScheduleContainer
from schooltool.timetable.interfaces import ITimetableContainer
from schooltool.timetable.timetable import SelectedPeriodsSchedule
from schooltool.timetable.tests.test_timetable import TimetableForTests


def setUpSchool(app):
    sy = ISchoolYearContainer(app)['2005'] = SchoolYear('2005',
                                                        date(2005, 1, 1),
                                                        date(2005, 1, 30))

    term = sy['spring'] = Term('Spring', date(2005, 1, 1),
                                         date(2005, 1, 30))
    term.addWeekdays(0, 1, 2, 3, 4)

    pc = app['persons']
    teacher = pc['teacher'] = BasicPerson("teacher", "Mister", "T")
    s1 = pc['john'] = BasicPerson("john", "John", "Peterson")
    s2 = pc['pete'] = BasicPerson("pete", "Pete", "Johnson")

    contacts = IContactContainer(app)
    contact = Contact()
    contact.__name__ = 'pete_parent'
    contact.prefix = 'Ms.'
    contact.first_name = 'Susan'
    contact.middle_name = 'T.'
    contact.last_name = 'Johnson'
    contact.suffix = 'Jr.'
    contact.address_line_1 = '1 First St.'
    contact.address_line_2 = 'Apt. 1'
    contact.city = 'NY'
    contact.state = 'NY'
    contact.country = 'USA'
    contact.postal_code = '00000'
    contact.email = 'davejohnson@gmail.com'
    contact.home_phone = '000-0000'
    contact.work_phone = '111-1111'
    contact.mobile_phone = '222-2222'
    contact.language = 'English'
    contacts['pete_parent'] = contact

    info = ContactPersonInfo()
    info.__parent__ = s2
    info.relationship = 'parent'
    IContactable(s2).contacts.add(contact, info)

    info = ContactPersonInfo()
    info.__parent__ = s2
    info.relationship = 'parent'
    IContactable(s2).contacts.add(IContact(teacher), info)

    d1 = IDemographics(s1)
    d1['ID'] = "112323"
    d1['ethnicity'] = u'Asian'
    d1['language'] = "English"
    d1['placeofbirth'] = "Humptington"
    d1['citizenship'] = "US"
    d2 = IDemographics(s2)
    d2['ID'] = "333655"
    d2['ethnicity'] = u'White'
    d2['language'] = "Brittish"
    d2['placeofbirth'] = "Providence"
    d2['citizenship'] = "UK"

    course = ICourseContainer(sy)['c1'] = Course("History")


def doctest_format_school_years():
    """
        >>> app = ISchoolToolApplication(None)
        >>> setUpSchool(app)
        >>> exporter = MegaExporter(app, None)
        >>> for row in exporter.format_school_years(): print row
        [Header('ID'), Header('Title'), Header('Start'), Header('End')]
        [Text(u'2005'), Text('2005'), Date(datetime.date(2005, 1, 1)), Date(datetime.date(2005, 1, 30))]
    """


def doctest_format_terms():
    """
        >>> app = ISchoolToolApplication(None)
        >>> setUpSchool(app)
        >>> exporter = MegaExporter(app, None)
        >>> for row in exporter.format_terms(): print row
        [Header('SchoolYear'), Header('ID'), Header('Title'), Header('Start'), Header('End')]
        [Text(u'2005'), Text(u'spring'), Text('Spring'), Date(datetime.date(2005, 1, 1)), Date(datetime.date(2005, 1, 30))]
        []
        [Header('Weekends')]
        [Text('Monday'), Text('Tuesday'), Text('Wednesday'), Text('Thursday'), Text('Friday'), Text('Saturday'), Text('Sunday')]
        [Text(''), Text(''), Text(''), Text(''), Text(''), Text('X'), Text('X')]

    Let's add some holdays:

        >>> term = ISchoolYearContainer(app)['2005']['spring']
        >>> for day in DateRange(date(2005, 1, 10), date(2005, 1, 17)):
        ...     if term.isSchoolday(day): term.remove(day)

        >>> for row in exporter.format_terms(): print row
        [Header('SchoolYear'), Header('ID'), Header('Title'), Header('Start'), Header('End')]
        [Text(u'2005'), Text(u'spring'), Text('Spring'), Date(datetime.date(2005, 1, 1)), Date(datetime.date(2005, 1, 30))]
        []
        [Header('Holidays')]
        [Date(datetime.date(2005, 1, 10)), Date(datetime.date(2005, 1, 14))]
        [Date(datetime.date(2005, 1, 17)), Date(datetime.date(2005, 1, 17))]
        []
        [Header('Weekends')]
        [Text('Monday'), Text('Tuesday'), Text('Wednesday'), Text('Thursday'), Text('Friday'), Text('Saturday'), Text('Sunday')]
        [Text(''), Text(''), Text(''), Text(''), Text(''), Text('X'), Text('X')]

    And a working weekend:

        >>> for day in DateRange(date(2005, 1, 8), date(2005, 1, 9)):
        ...     term.add(day)

        >>> for row in exporter.format_terms(): print row
        [Header('SchoolYear'), Header('ID'), Header('Title'), Header('Start'), Header('End')]
        [Text(u'2005'), Text(u'spring'), Text('Spring'), Date(datetime.date(2005, 1, 1)), Date(datetime.date(2005, 1, 30))]
        []
        [Header('Holidays')]
        [Date(datetime.date(2005, 1, 10)), Date(datetime.date(2005, 1, 14))]
        [Date(datetime.date(2005, 1, 17)), Date(datetime.date(2005, 1, 17))]
        []
        [Header('Weekends')]
        [Text('Monday'), Text('Tuesday'), Text('Wednesday'), Text('Thursday'), Text('Friday'), Text('Saturday'), Text('Sunday')]
        [Text(''), Text(''), Text(''), Text(''), Text(''), Text('X'), Text('X')]
        []
        [Header('Working weekends')]
        [Date(datetime.date(2005, 1, 8))]
        [Date(datetime.date(2005, 1, 9))]
    """


def doctest_format_courses():
    """
        >>> app = ISchoolToolApplication(None)
        >>> setUpSchool(app)
        >>> exporter = MegaExporter(app, None)
        >>> for row in exporter.format_courses(): print row
        [Header('School Year'), Header('ID'), Header('Title'), Header('Description'), Header('Local ID'), Header('Government ID'), Header('Credits')]
        [Text(u'2005'), Text(u'c1'), Text('History'), Text(None), Text(None), Text(None), Text(None)]
    """


def doctest_format_persons():
    """
        >>> app = ISchoolToolApplication(None)
        >>> setUpSchool(app)
        >>> exporter = MegaExporter(app, None)
        >>> from pprint import pprint
        >>> for row in exporter.format_persons(): pprint(row)
        [Header('User Name'),
         Header('Prefix'),
         Header('First Name'),
         Header('Middle Name'),
         Header('Last Name'),
         Header('Suffix'),
         Header('Preferred Name'),
         Header('Birth Date'),
         Header('Gender'),
         Header('Password'),
         Header(u'ID'),
         Header(u'Ethnicity'),
         Header(u'Language'),
         Header(u'Place of birth'),
         Header(u'Citizenship')]
        [Text(u'john'),
         Text(None),
         Text('John'),
         Text(None),
         Text('Peterson'),
         Text(None),
         Text(None),
         Date(None),
         Text(None),
         Text(None),
         Text('112323'),
         Text(u'Asian'),
         Text('English'),
         Text('Humptington'),
         Text('US')]
        [Text(u'manager'),
         Text(None),
         Text('SchoolTool'),
         Text(None),
         Text('Administrator'),
         Text(None),
         Text(None),
         Date(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None)]
        [Text(u'pete'),
         Text(None),
         Text('Pete'),
         Text(None),
         Text('Johnson'),
         Text(None),
         Text(None),
         Date(None),
         Text(None),
         Text(None),
         Text('333655'),
         Text(u'White'),
         Text('Brittish'),
         Text('Providence'),
         Text('UK')]
        [Text(u'teacher'),
         Text(None),
         Text('Mister'),
         Text(None),
         Text('T'),
         Text(None),
         Text(None),
         Date(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None)]
    """


def doctest_format_contact_persons():
    """
        >>> app = ISchoolToolApplication(None)
        >>> setUpSchool(app)
        >>> exporter = MegaExporter(app, None)
        >>> from pprint import pprint
        >>> for row in exporter.format_contact_persons(): pprint(row)
        [Header('ID'),
         Header('Prefix'),
         Header('First Name'),
         Header('Middle Name'),
         Header('Last Name'),
         Header('Suffix'),
         Header('Address line 1'),
         Header('Address line 2'),
         Header('City'),
         Header('State'),
         Header('Country'),
         Header('Postal code'),
         Header('Home phone'),
         Header('Work phone'),
         Header('Mobile phone'),
         Header('Email'),
         Header('Language')]
        [Text('john'),
         Text(''),
         Text(''),
         Text(''),
         Text(''),
         Text(''),
         Text(None),
         Text(None),
         Date(None),
         Date(None),
         Date(None),
         Date(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None)]
        [Text('manager'),
         Text(''),
         Text(''),
         Text(''),
         Text(''),
         Text(''),
         Text(None),
         Text(None),
         Date(None),
         Date(None),
         Date(None),
         Date(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None)]
        [Text('pete'),
         Text(''),
         Text(''),
         Text(''),
         Text(''),
         Text(''),
         Text(None),
         Text(None),
         Date(None),
         Date(None),
         Date(None),
         Date(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None)]
        [Text(u'pete_parent'),
         Text('Ms.'),
         Text('Susan'),
         Text('T.'),
         Text('Johnson'),
         Text('Jr.'),
         Text('1 First St.'),
         Text('Apt. 1'),
         Date('NY'),
         Date('NY'),
         Date('USA'),
         Date('00000'),
         Text('000-0000'),
         Text('111-1111'),
         Text('222-2222'),
         Text('davejohnson@gmail.com'),
         Text('English')]
        [Text('teacher'),
         Text(''),
         Text(''),
         Text(''),
         Text(''),
         Text(''),
         Text(None),
         Text(None),
         Date(None),
         Date(None),
         Date(None),
         Date(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None),
         Text(None)]
    """


def doctest_format_contact_relationships():
    """
        >>> app = ISchoolToolApplication(None)
        >>> setUpSchool(app)
        >>> exporter = MegaExporter(app, None)
        >>> from pprint import pprint
        >>> for row in exporter.format_contact_relationships(): pprint(row)
        [Header('Person ID'), Header('Contact ID'), Header('Relationship')]
        [Text('pete'), Text(u'pete_parent'), Text('parent')]
        [Text('pete'), Text('teacher'), Text('parent')]
    """


class Cell(object):
    def __init__(self, data, style):
        self.data, self.style = data, style


class WorkSheetStub(object):

    def __init__(self):
        self.table = {}

    def write(self, row, col, data, style):
        self.table[row, col] = Cell(data, style)

    def write_merge(self, row1, row2, col1, col2, data, style):
        self.table[row1, col1] = Cell(data, style)

    def format(self):
        dim1 = max([key[0] for key in self.table.keys()]) + 1
        dim2 = max([key[1] for key in self.table.keys()]) + 1

        table = []
        for x in range(dim1):
            l = []
            for y in range(dim2):
                l.append(self.table.get((x, y), Cell("", None)).data)
            table.append(l)
        return format_table(table)


def doctest_MegaExporter_export_section():
    """

        >>> app = ISchoolToolApplication(None)
        >>> sy = ISchoolYearContainer(app)['2005'] = SchoolYear('2005',
        ...                                                     date(2005, 1, 1),
        ...                                                     date(2005, 1, 30))

        >>> term = sy['spring'] = Term('Spring', date(2005, 1, 1),
        ...                                      date(2005, 1, 30))

        >>> pc = app['persons']
        >>> teacher = pc['teacher'] = Person("Mister T")
        >>> s1 = pc['john'] = Person("John")
        >>> s2 = pc['pete'] = Person("Pete")

        >>> course = ICourseContainer(sy)['c1'] = Course("History")
        >>> section = ISectionContainer(term)['s1'] = Section()
        >>> section.courses.add(course)
        >>> section.instructors.add(teacher)
        >>> section.members.add(s1)
        >>> section.members.add(s2)

        >>> exporter = MegaExporter(None, None)
        >>> ws = WorkSheetStub()
        >>> offset = 0
        >>> len = exporter.format_section(section, ws, offset)

        >>> print ws.format()
        +---------------+---------+
        | Section Title | Section |
        | ID            | s1      |
        | Description   |         |
        |               |         |
        | Courses       |         |
        | c1            |         |
        |               |         |
        | Students      |         |
        | John          |         |
        | Pete          |         |
        |               |         |
        | Instructors   |         |
        | Mister T      |         |
        +---------------+---------+

    """


def doctest_MegaExporter_export_flat_section():
    """

        >>> app = ISchoolToolApplication(None)
        >>> sy = SchoolYear('2005', date(2005, 1, 1), date(2005, 12, 31))
        >>> ISchoolYearContainer(app)['2005'] = sy

        >>> term1 = sy['term1'] = Term('Term 1', date(2005, 1, 1),
        ...                                      date(2005, 4, 30))
        >>> term2 = sy['term2'] = Term('Term 2', date(2005, 5, 1),
        ...                                      date(2005, 8, 31))
        >>> term3 = sy['term3'] = Term('Term 3', date(2005, 9, 1),
        ...                                      date(2005, 12, 31))

        >>> pc = app['persons']
        >>> teacher = pc['teacher'] = Person("Mister T")
        >>> s1 = pc['john'] = Person("John")
        >>> s2 = pc['pete'] = Person("Pete")

        >>> course = ICourseContainer(sy)['c1'] = Course("History")

        >>> sc1 = ISectionContainer(term1)
        >>> section1 = sc1['s1'] = Section('Section 1', 'Section 1 Desc')
        >>> section1.courses.add(course)
        >>> section1.instructors.add(teacher)
        >>> section1.members.add(s1)
        >>> section1.members.add(s2)

        >>> rc = app['resources']
        >>> r1 = rc['eq1'] = Equipment()
        >>> r2 = rc['loc1'] = Location()
        >>> section1.resources.add(r1)
        >>> section1.resources.add(r2)

        >>> timetable = TimetableForTests(sy.first, sy.last, title='test')
        >>> ITimetableContainer(sy)['test'] = timetable
        >>> periods = [chr(ord('A')+x) for x in range(24)]
        >>> time_slots = [time(x, 00) for x in range(24)]
        >>> timetable.setUp(periods=periods, time_slots=time_slots)
        >>> schedule = SelectedPeriodsSchedule(timetable,
        ...                                    term1.first, term1.last,
        ...                                    title=timetable.title,
        ...                                    timezone=timetable.timezone)
        >>> schedule.consecutive_periods_as_one = True
        >>> schedules = IScheduleContainer(section1)
        >>> schedules['1'] = schedule
        >>> day = timetable.periods.templates['default']
        >>> schedule.addPeriod(day['1'])
        >>> schedule.addPeriod(day['2'])
        >>> schedule.addPeriod(day['4'])

        >>> sc2 = ISectionContainer(term2)
        >>> section2 = sc2['s2'] = Section('Section 2', 'Section 2 Desc')
        >>> section2.previous = section1
        >>> section2.courses.add(course)
        >>> section2.instructors.add(teacher)
        >>> section2.members.add(s1)
        >>> section2.resources.add(r1)

        >>> sc3 = ISectionContainer(term3)
        >>> section3 = sc3['s3'] = Section('Section 3', 'Section 3 Desc')
        >>> section3.previous = section2
        >>> section3.courses.add(course)
        >>> section3.instructors.add(teacher)
        >>> section3.members.add(s1)
        >>> section3.resources.add(r1)

        >>> exporter = MegaExporter(None, None)
        >>> ws = WorkSheetStub()
        >>> len = exporter.format_flat_section(section1, ws, 0)
        >>> print ws.format()
        +-+-+-+----+-----------+----------------+----------+------+------+-+----+------+-----+-------+---+
        | | | | s1 | Section 1 | Section 1 Desc | Mister T | John | eq1  | | s2 | test | yes | Day 1 | A |
        | | | |    |           |                |          | Pete | loc1 | |    |      |     | Day 1 | B |
        | | | |    |           |                |          |      |      | |    |      |     | Day 1 | D |
        +-+-+-+----+-----------+----------------+----------+------+------+-+----+------+-----+-------+---+

        >>> ws = WorkSheetStub()
        >>> len = exporter.format_flat_section(section2, ws, 0)
        >>> print ws.format()
        +-+-+-+----+-----------+----------------+----------+------+-----+----+----+
        | | | | s2 | Section 2 | Section 2 Desc | Mister T | John | eq1 | s1 | s3 |
        +-+-+-+----+-----------+----------------+----------+------+-----+----+----+

        >>> ws = WorkSheetStub()
        >>> len = exporter.format_flat_section(section3, ws, 0)
        >>> print ws.format()
        +-+-+-+----+-----------+----------------+----------+------+-----+----+
        | | | | s3 | Section 3 | Section 3 Desc | Mister T | John | eq1 | s2 |
        +-+-+-+----+-----------+----------------+----------+------+-----+----+

    """


def doctest_MegaExporter_holidays():
    """

        >>> app = ISchoolToolApplication(None)
        >>> sy = ISchoolYearContainer(app)['2005'] = SchoolYear('2005',
        ...                                                     date(2005, 1, 1),
        ...                                                     date(2006, 1, 1))

        >>> term = sy['spring'] = Term("Spring", date(2005, 1, 1), date(2006, 1, 1))
        >>> term.addWeekdays(0, 1, 2, 3, 4, 5, 6)
        >>> exporter = MegaExporter(app, None)
        >>> exporter.calculate_holidays_and_weekdays()
        [[], [], []]

        >>> term.removeWeekdays(0, 1, 2, 3, 4, 5, 6)
        >>> exporter.calculate_holidays_and_weekdays()
        [[], [0, 1, 2, 3, 4, 5, 6], []]

        >>> term.addWeekdays(0, 1, 2, 3, 4)
        >>> exporter.calculate_holidays_and_weekdays()
        [[], [5, 6], []]

        >>> term.add(date(2005, 1, 1))
        >>> term.add(date(2005, 1, 2))
        >>> exporter.calculate_holidays_and_weekdays()
        [[], [5, 6], [datetime.date(2005, 1, 1), datetime.date(2005, 1, 2)]]

        >>> for day in DateRange(date(2005, 12, 18), date(2006, 1, 1)):
        ...     if term.isSchoolday(day): term.remove(day)
        >>> exporter.calculate_holidays_and_weekdays()
        [[(datetime.date(2005, 12, 19), datetime.date(2005, 12, 23)),
          (datetime.date(2005, 12, 26), datetime.date(2005, 12, 30))],
         [5, 6],
         [datetime.date(2005, 1, 1), datetime.date(2005, 1, 2)]]

    """


def doctest_MegaExporter_merge_ranges():
    """

        >>> merge_date_ranges([])
        []

        >>> merge_date_ranges([date(2005, 12, 19)])
        [(datetime.date(2005, 12, 19), datetime.date(2005, 12, 19))]

        >>> merge_date_ranges([date(2005, 12, 19), date(2005, 12, 20)])
        [(datetime.date(2005, 12, 19), datetime.date(2005, 12, 20))]

        >>> merge_date_ranges([date(2005, 12, 19), date(2005, 12, 21)])
        [(datetime.date(2005, 12, 19), datetime.date(2005, 12, 19)),
         (datetime.date(2005, 12, 21), datetime.date(2005, 12, 21))]

        >>> dates = [date(2005, 12, 19),
        ...          date(2005, 12, 20),
        ...          date(2005, 12, 21),
        ...          date(2005, 12, 22),
        ...          date(2005, 12, 23),
        ...          date(2005, 12, 26),
        ...          date(2005, 12, 27),
        ...          date(2005, 12, 28),
        ...          date(2005, 12, 29),
        ...          date(2005, 12, 30)]

        >>> merge_date_ranges(dates)
        [(datetime.date(2005, 12, 19), datetime.date(2005, 12, 23)),
         (datetime.date(2005, 12, 26), datetime.date(2005, 12, 30))]

    """


def test_suite():
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_NDIFF)
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 extraglobs={'provideAdapter': provideStubAdapter,
                                             'provideUtility': provideStubUtility},
                                 setUp=setUp, tearDown=tearDown)
    suite.layer = export_functional_layer
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
