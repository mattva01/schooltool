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
Tests for SchoolTool excel export views.
"""
import unittest
from datetime import date

from zope.testing import doctest

from schooltool.basicperson.interfaces import IDemographics
from schooltool.basicperson.person import BasicPerson
from schooltool.person.person import Person
from schooltool.export.export import MegaExporter, merge_date_ranges
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.testing import format_table
from schooltool.term.term import Term
from schooltool.common import DateRange
from schooltool.course.course import Course
from schooltool.course.section import Section
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.interfaces import ISectionContainer
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.schoolyear.testing import provideStubUtility
from schooltool.schoolyear.testing import provideStubAdapter
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.export.ftesting import export_functional_layer
from schooltool.schoolyear.testing import setUp
from schooltool.schoolyear.testing import tearDown


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
        [Header('School Year'), Header('ID'), Header('Title'), Header('Description')]
        [Text(u'2005'), Text(u'c1'), Text('History'), Date(None)]

    """


def doctest_format_persons():
    """

        >>> app = ISchoolToolApplication(None)
        >>> setUpSchool(app)
        >>> exporter = MegaExporter(app, None)
        >>> from zope.testing.doctestunit import pprint
        >>> for row in exporter.format_persons(): pprint(row)
        [Header('User Name'),
         Header('First Name'),
         Header('Last Name'),
         Header('Email'),
         Header('Phone'),
         Header('Birth Date'),
         Header('Gender'),
         Header('Password'),
         Header('ID'),
         Header('Ethnicity'),
         Header('Language'),
         Header('Place of birth'),
         Header('Citizenship')]
        [Text(u'john'),
         Text('John'),
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
         Text('SchoolTool'),
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
         Text('Pete'),
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
         Text('Mister'),
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
        +-------------+---------+
        | Section*    | Section |
        | ID          | s1      |
        | School Year | 2005    |
        | Term        | spring  |
        | Description |         |
        |             |         |
        | Courses     |         |
        | c1          |         |
        |             |         |
        | Students    |         |
        | John        |         |
        | Pete        |         |
        |             |         |
        | Instructors |         |
        | Mister T    |         |
        |             |         |
        +-------------+---------+

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
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 extraglobs={'provideAdapter': provideStubAdapter,
                                             'provideUtility': provideStubUtility},
                                 setUp=setUp, tearDown=tearDown)
    suite.layer = export_functional_layer
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
