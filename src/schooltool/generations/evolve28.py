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
Upgrade SchoolTool to generation 28.
"""
from persistent.dict import PersistentDict
from datetime import timedelta, date

from zope.proxy import sameProxiedObjects
from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication
from zope.app.component.hooks import setSite
from zope.app.component.hooks import getSite
from zope.app.container.contained import ObjectAddedEvent
from zope.app.intid import addIntIdSubscriber
from zope.component import getUtility
from zope.app.intid.interfaces import IIntIds

from schooltool.group.group import GroupContainerContainer
from schooltool.term.term import Term
from schooltool.timetable import TimetablesAdapter
from schooltool.timetable.interfaces import ITimetableCalendarEvent
from schooltool.timetable.schema import TimetableSchemaContainerContainer
from schooltool.schoolyear.interfaces import TermOverlapError
from schooltool.schoolyear.schoolyear import SchoolYearContainer
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.course.interfaces import ISectionContainer
from schooltool.course.section import Section
from schooltool.course.section import SectionContainerContainer
from schooltool.course.course import CourseContainerContainer


def setGroupContainer(sy, groups):
    addIntIdSubscriber(sy, ObjectAddedEvent(sy))
    int_ids = getUtility(IIntIds)
    sy_id = str(int_ids.getId(sy))
    app = ISchoolToolApplication(None)
    app['schooltool.group'][sy_id] = groups


def setCourseContainer(sy, courses):
    int_ids = getUtility(IIntIds)
    sy_id = str(int_ids.getId(sy))
    app = ISchoolToolApplication(None)
    app['schooltool.course.course'][sy_id] = courses


def setSchoolTimetableContainer(sy, ttschemas):
    int_ids = getUtility(IIntIds)
    sy_id = str(int_ids.getId(sy))
    app = ISchoolToolApplication(None)
    app['schooltool.timetable.schooltt'][sy_id] = ttschemas


def setSectionContainer(term, sections):
    int_ids = getUtility(IIntIds)
    term_id = str(int_ids.getId(term))
    app = ISchoolToolApplication(None)
    app['schooltool.course.section'][term_id] = sections


def moveTimetables(section, term, new_section):
    old_timetables = TimetablesAdapter(section)
    new_timetables = TimetablesAdapter(new_section)
    for key, timetable in old_timetables.timetables.items():
        if sameProxiedObjects(timetable.term, term):
            PersistentDict.__delitem__(old_timetables.timetables, key)
            PersistentDict.__setitem__(new_timetables.timetables, key, timetable)
            timetable.__parent__ = new_timetables


def moveCalendars(section, term, new_section):
    old_calendar = ISchoolToolCalendar(section)
    new_calendar = ISchoolToolCalendar(new_section)
    for key, event in old_calendar.events.items():
        if ITimetableCalendarEvent.providedBy(event):
            if sameProxiedObjects(event.activity.timetable.term, term):
                new_calendar.events[key] = event
                del old_calendar.events[key]
                event.__parent__ = new_calendar
        elif event.dtstart.date() in term:
            # XXX don't do recurren events
            new_calendar.events[key] = event
            del old_calendar.events[key]
            event.__parent__ = new_calendar


def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name, None)
    old_site = getSite()
    try:
        for app in findObjectsProviding(root, ISchoolToolApplication):
            setSite(app)
            # Evolve terms
            for term in app['terms'].values():
                # Wake'em up
                term._p_activate()
                term._first = term.__dict__['first']
                term._last = term.__dict__['last']
                del term.__dict__['first']
                del term.__dict__['last']

            app['schooltool.group'] = GroupContainerContainer()
            syc = app['schooltool.schoolyear'] = SchoolYearContainer()

            terms = sorted(app['terms'].values(), key=lambda t: t.first)
            if not terms:
                today = date.today()
                terms = [Term(today - timedelta(60), today + timedelta(60))]

            sy = SchoolYear("", terms[0].first, terms[-1].last)
            sy.title = "%s-%s" % (sy.first.strftime("%Y"), sy.last.strftime("%Y"))
            syc._SampleContainer__data[sy.title] = sy
            sy.__parent__ = syc
            sy.__name__ = sy.title
            syc._active_id = sy.__name__

            # put terms into relevant school years
            for term in terms:
                term.__parent__ = None
                try:
                    sy[term.__name__] = term
                    previous_term = term
                except TermOverlapError:
                    term.first = previous_term.last + timedelta(1)
                    try:
                        sy[term.__name__] = term
                        previous_term = term
                    except TermOverlapError:
                        # if it still does not fit - skip it
                        del terms[term.__name__]
            del app._SampleContainer__data['terms']
            terms = sorted(sy.values(), key=lambda t: t.first)
            for term in terms:
                addIntIdSubscriber(term, ObjectAddedEvent(term))

            # move groups container into every school year fixing membership relationships
            setGroupContainer(sy, app['groups'])
            del app._SampleContainer__data['groups']

            # copy courses container into every school year
            app['schooltool.course.course'] = CourseContainerContainer()
            setCourseContainer(sy, app['courses'])
            del app._SampleContainer__data['courses']

            # copy timetable schemas into every school year
            app['schooltool.timetable.schooltt'] = TimetableSchemaContainerContainer()
            setSchoolTimetableContainer(sy, app['ttschemas'])
            del app._SampleContainer__data['ttschemas']

            # go through sections, copy sections into all the terms the
            # section was scheduled for, or only into the terms in the
            # last school year if it was not scheduled yet
            app['schooltool.course.section'] = SectionContainerContainer()
            sections = app['sections']
            del app._SampleContainer__data['sections']
            setSectionContainer(terms[0], sections)
            for name, section in sections.items():
                for term in terms[1:]:
                    sc = ISectionContainer(term)
                    new_section = Section(section.title, section.description)
                    for member in section.members:
                        new_section.members.add(member)
                    for instructor in section.instructors:
                        new_section.instructors.add(instructor)
                    for course in section.courses:
                        new_section.courses.add(course)
                    for resource in section.resources:
                        new_section.resources.add(resource)
                    sc[name] = new_section
                    moveTimetables(section, term, new_section)
                    moveCalendars(section, term, new_section)
    finally:
        setSite(old_site)

