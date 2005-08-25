#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
SchoolTool Application

$Id$
"""

##############################################################################
# BBB: Make sure the old data object references are still there.
from zope.deprecation import deprecated

from schooltool.app.app import SchoolToolApplication
from schooltool.app.app import ApplicationPreferences
deprecated(('SchoolToolApplication', 'ApplicationPreferences'),
           'This class has moved to schooltool.app.app. '
           'The reference will be gone in 0.15')

from schooltool.app.overlay import \
     CalendarOverlayInfo #as CalendarAndTTOverlayInfo
class CalendarAndTTOverlayInfo(CalendarOverlayInfo):
    def __new__(*args, **kw):
        #import pdb; pdb.set_trace()
        return CalendarOverlayInfo.__new__(*args, **kw)

deprecated(('CalendarAndTTOverlayInfo',),
           'This specific class has been deprecated. Use '
           '`schooltool.app.overlay.CalendarOverlayInfo` and the '
           '`IShowTimetables` instead. '
           'The reference will be gone in 0.15')

from schooltool.person.person import PersonContainer, Person
from schooltool.person.preference import PersonPreferences
from schooltool.person.details import PersonDetails
deprecated(('PersonContainer', 'Person', 'PersonPreferences', 'PersonDetails'),
           'This class has moved to schooltool.person.person. '
           'The reference will be gone in 0.15')

from schooltool.group.group import GroupContainer, Group
deprecated(('GroupContainer', 'Group'),
           'This class has moved to schooltool.group.group. '
           'The reference will be gone in 0.15')

from schooltool.resource.resource import ResourceContainer, Resource
deprecated(('ResourceContainer', 'Resource'),
           'This class has moved to schooltool.resource.resource. '
           'The reference will be gone in 0.15')

from schooltool.course.course import CourseContainer, Course
deprecated(('CourseContainer', 'Course'),
           'This class has moved to schooltool.course.course. '
           'The reference will be gone in 0.15')

from schooltool.course.section import SectionContainer, Section
deprecated(('SectionContainer', 'Section'),
           'This class has moved to schooltool.course.section. '
           'The reference will be gone in 0.15')

##############################################################################


def registerTestSetup():
    from zope.interface import classImplements
    from schooltool.testing import registry

    def haveCalendar():
        from schooltool.app.app import SchoolToolApplication
        from schooltool.app.interfaces import IHaveCalendar
        if not IHaveCalendar.implementedBy(SchoolToolApplication):
            classImplements(SchoolToolApplication, IHaveCalendar)
    registry.register('CalendarComponents', haveCalendar)

    def haveTimetables():
        from schooltool.timetable.interfaces import IHaveTimetables

        from schooltool.person.person import Person
        if not IHaveTimetables.implementedBy(Person):
            classImplements(Person, IHaveTimetables)

        from schooltool.group.group import Group
        if not IHaveTimetables.implementedBy(Group):
            classImplements(Group, IHaveTimetables)

        from schooltool.resource.resource import Resource
        if not IHaveTimetables.implementedBy(Resource):
            classImplements(Resource, IHaveTimetables)

        from schooltool.app.app import SchoolToolApplication
        if not IHaveTimetables.implementedBy(SchoolToolApplication):
            classImplements(SchoolToolApplication, IHaveTimetables)
    registry.register('TimetablesComponents', haveTimetables)

registerTestSetup()
del registerTestSetup
