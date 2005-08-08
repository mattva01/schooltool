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
SchoolTool application interfaces

$Id$
"""

import datetime

from zope.interface import Interface, Attribute, implements
from zope.app.location.interfaces import ILocation
from zope.schema.interfaces import IField
from zope.schema import Field, Object, Int, Text, TextLine, List, Set, Tuple
from zope.schema import Dict, Date, Timedelta, Bool, Choice, Object
from zope.app.container.interfaces import IContainer, IContained
from zope.app.container.constraints import contains, containers

from schoolbell.app import interfaces as sb
from schoolbell.app.overlay import ICalendarOverlayInfo
from schoolbell.calendar.interfaces import Unchanged

from schooltool import SchoolToolMessageID as _

from schooltool.timetable.interfaces import ITimetabled

#
#  SchoolTool domain model objects
#


class IPerson(sb.IPerson, ITimetabled):
    """SchoolTool person object"""


class IGroup(sb.IGroup, ITimetabled):
    """SchoolTool group object"""


class IResource(sb.IResource, ITimetabled):
    """SchoolTool resource object"""


class ICourse(Interface):
    """Courses are similar to groups, membership is restricted to Sections."""

    title = TextLine(
        title=_("Title"),
        description=_("Title of the course."))

    description = Text(
        title=_("Description"),
        required=False,
        description=_("Description of the course."))

    sections = Attribute("""The Sections that implement this course material,
            see schoolbell.relationship.interfaces.IRelationshipProperty.""")


class ICourseContainer(IContainer, sb.IAdaptableToSchoolBellApplication):
    """Container of Courses."""

    contains(ICourse)


class ICourseContained(ICourse, IContained,
                       sb.IAdaptableToSchoolBellApplication):
    """Courses contained in an ICourseContainer."""

    containers(ICourseContainer)


class ISection(IGroup):
    """Sections are groups of users in a particular meeting of a Course."""

    label = TextLine(
        title=_("Label"),
        required=False,
        description=_(
            """An identifier for a section, made up of instructor
            names, courses, and meeting time."""))

    title = TextLine(
        title=_("Code"),
        required=True,
        description=_("ID code for the section."))

    description = Text(
        title=_("Description"),
        required=False,
        description=_("Description of the section."))

    instructors = Attribute(
               """A list of Person objects in the role of instructor""")

    members = Attribute("""Students listed in the role of member""")

    courses = Attribute("""A list of courses this section is a member of.""")

    size = Attribute("""The number of member students in the section.""")

    location = Choice(title=u"Location",
                      required=False,
                      description=u"The resource where this section meets.",
                      vocabulary="LocationResources")


class ISectionContainer(IContainer):
    """A container for Sections."""

    contains(ISection)


class ISectionContained(ISection, IContained,
                       sb.IAdaptableToSchoolBellApplication):
    """Sections in a SectionContainer."""

    containers(ISectionContainer)


class IPersonContainer(sb.IPersonContainer):
    """SchoolTool's person container"""

    contains(IPerson)


class IGroupContainer(sb.IGroupContainer):
    """SchoolTool's group container contains Groups and subclasses."""

    contains(IGroup, ICourse, ISection)


class IResourceContainer(sb.IResourceContainer):
    """SchoolTool's resource container"""

    contains(IResource)


#
#  Miscellaneous
#


class IPersonPreferences(sb.IPersonPreferences):

    cal_periods = Bool(
        title=_("Show periods"),
        description=_("Show period names in daily view"))


class ICalendarAndTTOverlayInfo(ICalendarOverlayInfo):

    show_timetables = Bool(
            title=u"Show timetables",
            description=u"""
            An option that controls whether the timetable of this calendar's
            owner is shown in the calendar views.
            """)


#
#  Main application
#

class ISchoolToolApplication(sb.ISchoolBellApplication, ITimetabled):
    """The main SchoolTool application object

    The application is a read-only container with the following items:

        'persons' - IPersonContainer
        'groups' - IGroupContainer
        'resources' - IResourceContainer
        'terms' - ITermContainer
        'ttschemas' - ITimetableSchemaContainer

    """

    calendar = Object(
            title=u"School calendar",
            schema=sb.ISchoolBellCalendar)


class IApplicationPreferences(sb.IApplicationPreferences):
    """ScholTool ApplicationPreferences."""

