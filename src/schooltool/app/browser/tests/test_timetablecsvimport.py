#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Unit tests for schooltool.app.browser.timetablecsvimport
"""
import unittest
import doctest
import datetime
import transaction

from zope.app.testing import setup as zope_setup
from zope.interface import Interface
from zope.component import provideAdapter, provideUtility, provideHandler
from zope.component.hooks import getSite, setSite
from zope.i18n import translate
from zope.intid import IntIds
from zope.intid import addIntIdSubscriber
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.location.interfaces import ILocation

from schooltool.app.browser.timetablecsvimport import TimetableCSVImporter
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.person import BasicPerson
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.course import CourseInit
from schooltool.course.course import Course
from schooltool.course.course import getCourseContainer
from schooltool.course.course import getCourseContainerForApp
from schooltool.course.section import SectionInit
from schooltool.course.section import getSectionContainer
from schooltool.course.section import getTermForSection
from schooltool.course.section import getTermForSectionContainer
from schooltool.course.interfaces import ISectionContainer
from schooltool.course.browser.section import SectionNameChooser
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.schoolyear.schoolyear import getSchoolYearContainer
from schooltool.relationship.tests import setUpRelationships
from schooltool.term.interfaces import ITerm
from schooltool.term.term import Term
from schooltool.term.term import getTermContainer
from schooltool.term.term import getSchoolYearForTerm
from schooltool.term.term import listTerms
from schooltool.testing import registry as testing_registry
from schooltool.testing.setup import setUpSchoolToolSite
from schooltool.testing.stubs import KeyReferenceStub
from schooltool.timetable.interfaces import IScheduleContainer
from schooltool.timetable.app import getTimetableContainer
from schooltool.timetable.app import getScheduleContainer
from schooltool.timetable.app import TimetableStartUp
from schooltool.timetable.interfaces import ITimetableContainer
from schooltool.timetable.daytemplates import CalendarDayTemplates
from schooltool.timetable.daytemplates import WeekDayTemplates
from schooltool.timetable.daytemplates import DayTemplate
from schooltool.timetable.daytemplates import TimeSlot
from schooltool.timetable.schedule import Period
from schooltool.timetable.timetable import Timetable
from schooltool.timetable.browser.tests.test_ttwizard import print_day_templates


def print_schedule(schedule):
    print "Schedule '%s'" % schedule.title
    print 'Periods (%s)' % schedule.periods.__class__.__name__
    print_day_templates(schedule.timetable.periods.templates,
                        filter=lambda p: schedule.hasPeriod(p))


def setUpYear():
    app = ISchoolToolApplication(None)
    syc = ISchoolYearContainer(app)
    syc['2010-2011'] = SchoolYear(u'2010-2011',
                                  datetime.date(2010, 9, 1),
                                  datetime.date(2011, 5, 30))
    syc['2010-2011'][u'fall'] = Term(u'Fall',
                                     datetime.date(2010, 9, 1),
                                     datetime.date(2010, 11, 30))
    syc['2010-2011'][u'winter'] = Term(u'Winter',
                                       datetime.date(2010, 12, 1),
                                       datetime.date(2011, 2, 28))
    syc['2010-2011'][u'spring'] = Term(u'Spring',
                                       datetime.date(2011, 3, 1),
                                       datetime.date(2011, 5, 30))


def setUpPersons(names):
    app = ISchoolToolApplication(None)
    persons = app['persons']
    for name in names:
        parts = name.split(' ')
        first = parts[0]
        last = ' '.join(parts[1:])
        username = parts[-1].lower()
        persons[username] = BasicPerson(username, first, last)


def setUpCourses(names):
    app = ISchoolToolApplication(None)
    CourseInit(app)()
    SectionInit(app)()
    courses = ICourseContainer(app)
    for name in names:
        courses[name.lower()] = Course(title=name)


def addTimetableDays(tt, days, periods):
    for day_id, day_title in days:
        p_days = tt.periods.templates
        day = p_days[day_id] = DayTemplate(day_title)
        for period in periods:
            day[period.lower()] = Period(title=period)

        t_days = tt.time_slots.templates
        day = t_days[day_id] = DayTemplate(day_title)
        for n, period in enumerate(periods):
            time = datetime.time(8+n, 0)
            duration = datetime.timedelta(0, 3300)
            day[period.lower()] = TimeSlot(time, duration)


def setUpTimetables():
    app = ISchoolToolApplication(None)
    TimetableStartUp(app)()
    syc = ISchoolYearContainer(app)
    sy = syc.getActiveSchoolYear()
    timetables = ITimetableContainer(sy)
    timetables[u'rotating'] = tt_rot = Timetable(
        sy.first, sy.last, title=u"Rotating")

    tt_rot.periods = CalendarDayTemplates()
    tt_rot.periods.initTemplates()
    tt_rot.time_slots = CalendarDayTemplates()
    tt_rot.time_slots.initTemplates()
    addTimetableDays(
        tt_rot,
        [('1', 'Day 1'), ('2', 'Day 2'), ('3', 'Day 3')],
        ['A', 'B', 'C'])

    timetables[u'weekly'] = tt_week = Timetable(
        sy.first, sy.last, title=u"Weekly")

    tt_week.periods = WeekDayTemplates()
    tt_week.periods.initTemplates()
    tt_week.time_slots = WeekDayTemplates()
    tt_week.time_slots.initTemplates()

    dows = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday']
    week_days = [(tt_week.periods.getWeekDayKey(n), title)
                 for n, title in enumerate(dows)]

    addTimetableDays(
        tt_week,
        week_days,
        ['A', 'B', 'C'])


person_names = (
'John Black',
'Pete Cook',
'Daniel Lewis',
'Alan Burton',
'Heinrich Lorch',
'Andreas Guzman',
)

course_names = ('Math', 'Philosophy', 'Literature')

simple_csv = """
"Fall","Spring"
""
"philosophy","lorch"
"rotating"
"Day 1","A"
"Day 1","B"
"Day 3","C"
"***"
"cook"
"lewis"
""
"literature","guzman"
"rotating"
"Day 1","B"
"Day 2","C"
"weekly"
"Monday","A"
"***"
"black"
"cook"
""
"math","burton"
"***"
"lewis"
""
""".strip()


def doctest_TimetableCSVImporter():
    """
        >>> setUpYear()
        >>> setUpPersons(person_names)
        >>> setUpCourses(course_names)
        >>> setUpTimetables()

        >>> app = ISchoolToolApplication(None)
        >>> syc = ISchoolYearContainer(app)
        >>> schoolyear = syc.getActiveSchoolYear()

        >>> importer = TimetableCSVImporter(schoolyear)

        >>> def tryImport(csv):
        ...    result = importer.importFromCSV(csv)
        ...    if not result:
        ...        print importer.errors

        >>> tryImport(simple_csv)

        >>> def sectionName(term, section):
        ...    return '%s in %s' % (
        ...        translate(section.label), term.title)

        >>> for term in listTerms(schoolyear):
        ...    sections = ISectionContainer(term)
        ...    for s_name in sorted(sections):
        ...        print '*' * 50
        ...        section = sections[s_name]
        ...        print sectionName(term, section)
        ...        s_next = section.next
        ...        if s_next is not None:
        ...            n_term = ITerm(s_next)
        ...            print '  next:', sectionName(n_term, s_next)
        ...        print '  students:'
        ...        for member in sorted(section.members, key=lambda m:m.__name__):
        ...            print '   ', member.title
        ...        schedules = IScheduleContainer(section)
        ...        for key in sorted(schedules):
        ...            print_schedule(schedules[key])
        **************************************************
        Lorch, Heinrich -- Philosophy (1) in Fall
          next: Lorch, Heinrich -- Philosophy (1) in Winter
          students:
            Cook, Pete
            Lewis, Daniel
        Schedule 'Rotating'
        Periods (list)
        +-------+-------+-------+
        | Day 1 | Day 2 | Day 3 |
        +-------+-------+-------+
        | A     |       |       |
        | B     |       |       |
        |       |       | C     |
        +-------+-------+-------+
        **************************************************
        Guzman, Andreas -- Literature (2) in Fall
          next: Guzman, Andreas -- Literature (2) in Winter
          students:
            Black, John
            Cook, Pete
        Schedule 'Rotating'
        Periods (list)
        +-------+-------+-------+
        | Day 1 | Day 2 | Day 3 |
        +-------+-------+-------+
        |       |       |       |
        | B     |       |       |
        |       | C     |       |
        +-------+-------+-------+
        Schedule 'Weekly'
        Periods (list)
        +--------+---------+-----------+----------+--------+----------+--------+
        | Monday | Tuesday | Wednesday | Thursday | Friday | Saturday | Sunday |
        +--------+---------+-----------+----------+--------+----------+--------+
        | A      |         |           |          |        |          |        |
        |        |         |           |          |        |          |        |
        |        |         |           |          |        |          |        |
        +--------+---------+-----------+----------+--------+----------+--------+
        **************************************************
        Burton, Alan -- Math (3) in Fall
          next: Burton, Alan -- Math (3) in Winter
          students:
            Lewis, Daniel
        **************************************************
        Lorch, Heinrich -- Philosophy (1) in Winter
          next: Lorch, Heinrich -- Philosophy (1) in Spring
          students:
            Cook, Pete
            Lewis, Daniel
        Schedule 'Rotating'
        Periods (list)
        +-------+-------+-------+
        | Day 1 | Day 2 | Day 3 |
        +-------+-------+-------+
        | A     |       |       |
        | B     |       |       |
        |       |       | C     |
        +-------+-------+-------+
        **************************************************
        Guzman, Andreas -- Literature (2) in Winter
          next: Guzman, Andreas -- Literature (2) in Spring
          students:
            Black, John
            Cook, Pete
        Schedule 'Rotating'
        Periods (list)
        +-------+-------+-------+
        | Day 1 | Day 2 | Day 3 |
        +-------+-------+-------+
        |       |       |       |
        | B     |       |       |
        |       | C     |       |
        +-------+-------+-------+
        Schedule 'Weekly'
        Periods (list)
        +--------+---------+-----------+----------+--------+----------+--------+
        | Monday | Tuesday | Wednesday | Thursday | Friday | Saturday | Sunday |
        +--------+---------+-----------+----------+--------+----------+--------+
        | A      |         |           |          |        |          |        |
        |        |         |           |          |        |          |        |
        |        |         |           |          |        |          |        |
        +--------+---------+-----------+----------+--------+----------+--------+
        **************************************************
        Burton, Alan -- Math (3) in Winter
          next: Burton, Alan -- Math (3) in Spring
          students:
            Lewis, Daniel
        **************************************************
        Lorch, Heinrich -- Philosophy (1) in Spring
          students:
            Cook, Pete
            Lewis, Daniel
        Schedule 'Rotating'
        Periods (list)
        +-------+-------+-------+
        | Day 1 | Day 2 | Day 3 |
        +-------+-------+-------+
        | A     |       |       |
        | B     |       |       |
        |       |       | C     |
        +-------+-------+-------+
        **************************************************
        Guzman, Andreas -- Literature (2) in Spring
          students:
            Black, John
            Cook, Pete
        Schedule 'Rotating'
        Periods (list)
        +-------+-------+-------+
        | Day 1 | Day 2 | Day 3 |
        +-------+-------+-------+
        |       |       |       |
        | B     |       |       |
        |       | C     |       |
        +-------+-------+-------+
        Schedule 'Weekly'
        Periods (list)
        +--------+---------+-----------+----------+--------+----------+--------+
        | Monday | Tuesday | Wednesday | Thursday | Friday | Saturday | Sunday |
        +--------+---------+-----------+----------+--------+----------+--------+
        | A      |         |           |          |        |          |        |
        |        |         |           |          |        |          |        |
        |        |         |           |          |        |          |        |
        +--------+---------+-----------+----------+--------+----------+--------+
        **************************************************
        Burton, Alan -- Math (3) in Spring
          students:
            Lewis, Daniel


    """


def setUpIntIds():
    provideAdapter(KeyReferenceStub)
    provideHandler(addIntIdSubscriber,
                   [ILocation, IObjectAddedEvent])
    provideUtility(IntIds(), IIntIds)


    testing_registry.setupTimetablesComponents()

def docSetUp(test=None):
    zope_setup.placefulSetUp()
    zope_setup.setUpAnnotations()
    zope_setup.setUpTraversal()
    test.globs['app'] = setUpSchoolToolSite()
    setUpRelationships()

    provideAdapter(getSchoolYearContainer)
    provideAdapter(getTermContainer, (Interface,))
    provideAdapter(getSchoolYearForTerm)
    provideAdapter(getCourseContainer)
    provideAdapter(getCourseContainerForApp)
    provideAdapter(getSectionContainer)
    provideAdapter(getTermForSection)
    provideAdapter(getTermForSectionContainer)
    provideAdapter(getTimetableContainer)
    provideAdapter(getScheduleContainer)
    setUpIntIds()

    provideAdapter(SectionNameChooser, (ISectionContainer,))

    transaction.begin()


def docTearDown(test=None):
    transaction.abort()
    zope_setup.placefulTearDown()
    setSite()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(
        setUp=docSetUp, tearDown=docTearDown,
        optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
