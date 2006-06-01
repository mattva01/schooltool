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
Section implementation

$Id$
"""
from persistent import Persistent
import zope.interface

from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.container import btree, contained
from zope.component import adapts

from schooltool.relationship import RelationshipProperty
from schooltool.app import membership
from schooltool.app.cal import Calendar
from schooltool.group.interfaces import IGroup
from schooltool.person.interfaces import IPerson
from schooltool.resource.interfaces import IResource

from schooltool import SchoolToolMessage as _
from schooltool.app import relationships
from schooltool.course import interfaces, booking
from schooltool.securitypolicy.crowds import Crowd, AggregateCrowd
from schooltool.course.interfaces import ISection
from schooltool.person.interfaces import IPerson
from schooltool.app.security import CalendarParentCrowd



class Section(Persistent, contained.Contained):

    zope.interface.implements(interfaces.ISectionContained,
                              IAttributeAnnotatable)

    _location = None

    def __init__(self, title="Section", description=None, schedule=None):
        self.title = title
        self.description = description
        self.calendar = Calendar(self)

    @property
    def label(self):
        instructors = " ".join([i.title for i in self.instructors])
        courses = " ".join([c.title for c in self.courses])
        msg = _('${instructors} -- ${courses}',
                mapping={'instructors': instructors, 'courses': courses})
        return msg

    @property
    def size(self):
        size = 0
        for member in self.members:
            if IPerson.providedBy(member):
                size = size + 1
            elif IGroup.providedBy(member):
                size = size + len(member.members)
        return size

    instructors = RelationshipProperty(relationships.URIInstruction,
                                       relationships.URISection,
                                       relationships.URIInstructor)

    courses = RelationshipProperty(relationships.URICourseSections,
                                   relationships.URISectionOfCourse,
                                   relationships.URICourse)

    members = RelationshipProperty(membership.URIMembership,
                                   membership.URIGroup,
                                   membership.URIMember)

    resources = RelationshipProperty(booking.URISectionBooking,
                                     booking.URISection,
                                     booking.URIResource)


class SectionContainer(btree.BTreeContainer):
    """Container of Sections."""

    zope.interface.implements(interfaces.ISectionContainer,
                              IAttributeAnnotatable)


def addSectionContainerToApplication(event):
    event.object['sections'] = SectionContainer()


class InstructorsCrowd(Crowd):
    """Crowd of instructors of a section."""
    adapts(ISection)
    def contains(self, principal):
        return IPerson(principal, None) in self.context.instructors


class LearnersCrowd(Crowd):
    """Crowd of learners of a section.

    At the moment only direct members of a section are considered as
    learners.
    """
    adapts(ISection)
    def contains(self, principal):
        return IPerson(principal, None) in self.context.members


class SectionCalendarSettingCrowd(CalendarParentCrowd):
    adapts(ISection)
    setting_key = 'everyone_can_view_section_info'


class SectionCalendarViewers(AggregateCrowd):
    """Crowd of those who can see the section calendar."""
    adapts(ISection)

    def crowdFactories(self):
        return [InstructorsCrowd, LearnersCrowd, SectionCalendarSettingCrowd]
