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

import zope.interface
import zope.schema
from zope.app import container

from schoolbell.app import interfaces as sb
from schoolbell.app.overlay import ICalendarOverlayInfo
from schoolbell.calendar.interfaces import Unchanged

from schooltool import SchoolToolMessageID as _

#
#  SchoolTool domain model objects
#

# Those interfaces are imported here, since they will later actually move here.
from schoolbell.app.interfaces import IPerson, IGroup, IResource
from schoolbell.app.interfaces import \
     IPersonContainer, IGroupContainer, IResourceContainer
from schoolbell.app.interfaces import \
     ISchoolBellApplication as ISchoolToolApplication
from schoolbell.app.interfaces import IApplicationInitializationEvent
from schoolbell.app.interfaces import ApplicationInitializationEvent
from schoolbell.app.interfaces import IApplicationPreferences
from schoolbell.app.interfaces import IHaveNotes
from schoolbell.app.interfaces import IPersonPreferences


class ICourse(zope.interface.Interface):
    """Courses are similar to groups, membership is restricted to Sections."""

    title = zope.schema.TextLine(
        title=_("Title"),
        description=_("Title of the course."))

    description = zope.schema.Text(
        title=_("Description"),
        required=False,
        description=_("Description of the course."))

    sections = zope.interface.Attribute(
        """The Sections that implement this course material,
           see schoolbell.relationship.interfaces.IRelationshipProperty.""")


class ICourseContainer(container.interfaces.IContainer):
    """Container of Courses."""

    container.constraints.contains(ICourse)


class ICourseContained(ICourse, container.interfaces.IContained):
    """Courses contained in an ICourseContainer."""

    container.constraints.containers(ICourseContainer)


class ISection(IGroup):
    """Sections are groups of users in a particular meeting of a Course."""

    label = zope.schema.TextLine(
        title=_("Label"),
        required=False,
        description=_(
            """An identifier for a section, made up of instructor
            names, courses, and meeting time."""))

    title = zope.schema.TextLine(
        title=_("Code"),
        required=True,
        description=_("ID code for the section."))

    description = zope.schema.Text(
        title=_("Description"),
        required=False,
        description=_("Description of the section."))

    instructors = zope.interface.Attribute(
        """A list of Person objects in the role of instructor""")

    members = zope.interface.Attribute(
        """Students listed in the role of member""")

    courses = zope.interface.Attribute(
        """A list of courses this section is a member of.""")

    size = zope.interface.Attribute(
        """The number of member students in the section.""")

    location = zope.schema.Choice(
        title=u"Location",
        required=False,
        description=u"The resource where this section meets.",
        vocabulary="LocationResources")


class ISectionContainer(container.interfaces.IContainer):
    """A container for Sections."""

    container.constraints.contains(ISection)


class ISectionContained(ISection, container.interfaces.IContained):
    """Sections in a SectionContainer."""

    container.constraints.containers(ISectionContainer)


#
#  Miscellaneous
#

class ICalendarAndTTOverlayInfo(ICalendarOverlayInfo):

    show_timetables = zope.schema.Bool(
            title=u"Show timetables",
            description=u"""
            An option that controls whether the timetable of this calendar's
            owner is shown in the calendar views.
            """)
