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
from zope.deferredimport.deferredmodule import deprecated

deprecated('This class has moved to schooltool.app.app. '
           'The reference will be gone in 0.15',
           SchoolToolApplication='schooltool.app.app:SchoolToolApplication',
           ApplicationPreferences='schooltool.app.app:ApplicationPreferences')

deprecated('This specific class has been deprecated. Use '
           '`schooltool.app.overlay.CalendarOverlayInfo` and the '
           '`IShowTimetables` instead. '
           'The reference will be gone in 0.15',
           CalendarAndTTOverlayInfo='schooltool.app.overlay:CalendarOverlayInfo')

deprecated('This class has moved to schooltool.person.person. '
           'The reference will be gone in 0.15',
           PersonContainer='schooltool.person.person:PersonContainer',
           Person='schooltool.person.person:Person',
           PersonPreferences='schooltool.person.preference:PersonPreferences')

deprecated('This class has moved to schooltool.group.group. '
           'The reference will be gone in 0.15',
           GroupContainer='schooltool.group.group:GroupContainer',
           Group='schooltool.group.group:Group')

deprecated('This class has moved to schooltool.resource.resource. '
           'The reference will be gone in 0.15',
           ResourceContainer='schooltool.resource.resource:ResourceContainer',
           Resource='schooltool.resource.resource:Resource')

deprecated('This class has moved to schooltool.course.course. '
           'The reference will be gone in 0.15',
           CourseContainer='schooltool.course.course:CourseContainer',
           Course='schooltool.course.course:CourseContainer')

deprecated('This class has moved to schooltool.course.section. '
           'The reference will be gone in 0.15',
           SectionContainer="schooltool.course.section:SectionContainer",
           Section="schooltool.course.section:Section")

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
