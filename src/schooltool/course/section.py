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
from zope.interface import implements

from schooltool.relationship import RelationshipProperty
from schooltool.app import membership
from schooltool.app.relationships import URIInstruction
from schooltool.app.relationships import URISection
from schooltool.app.app import InitBase
from schooltool.group.interfaces import IBaseGroup as IGroup
from schooltool.person.interfaces import IPerson

from schooltool.common import SchoolToolMessage as _
from schooltool.app import relationships
from schooltool.course import interfaces, booking
from schooltool.securitypolicy.crowds import Crowd, AggregateCrowd
from schooltool.course.interfaces import ISection
from schooltool.app.security import ConfigurableCrowd
from schooltool.relationship.relationship import getRelatedObjects
from schooltool.course.interfaces import ILearner, IInstructor


class Section(Persistent, contained.Contained):

    zope.interface.implements(interfaces.ISectionContained,
                              IAttributeAnnotatable)

    _location = None

    def __init__(self, title="Section", description=None, schedule=None):
        self.title = title
        self.description = description

    @property
    def label(self):
        instructors = " ".join([i.title for i in self.instructors])
        msg = _('${instructors} -- ${section_title}',
                mapping={'instructors': instructors, 'section_title': self.title})
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


class SectionInit(InitBase):

    def __call__(self):
        self.app['sections'] = SectionContainer()


class InstructorsCrowd(Crowd):
    """Crowd of instructors of a section."""
    def contains(self, principal):
        return IPerson(principal, None) in ISection(self.context).instructors


class PersonInstructorsCrowd(Crowd):
    """Crowd of instructors of a person."""

    def _getSections(self, ob):
        return [section for section in getRelatedObjects(ob, membership.URIGroup)
                if ISection.providedBy(section)]

    def contains(self, principal):
        user = IPerson(principal, None)
        person = IPerson(self.context)
        # First check the the sections a pupil is in directly
        for section in self._getSections(person):
            if user in section.instructors:
                return True
        # Now check the section membership via groups
        for group in person.groups:
            for section in self._getSections(group):
                if user in section.instructors:
                    return True
        return False


class LearnersCrowd(Crowd):
    """Crowd of learners of a section.

    At the moment only direct members of a section are considered as
    learners.
    """
    adapts(ISection)
    def contains(self, principal):
        return IPerson(principal, None) in self.context.members


class SectionCalendarSettingCrowd(ConfigurableCrowd):
    adapts(ISection)
    setting_key = 'everyone_can_view_section_info'


class SectionCalendarViewers(AggregateCrowd):
    """Crowd of those who can see the section calendar."""
    adapts(ISection)

    def crowdFactories(self):
        return [InstructorsCrowd, LearnersCrowd, SectionCalendarSettingCrowd]


class PersonLearnerAdapter(object):
    implements(ILearner)
    adapts(IPerson)

    def __init__(self, person):
        self.person = person

    def _getSections(self, ob):
        return [section for section in getRelatedObjects(ob, membership.URIGroup)
                if ISection.providedBy(section)]

    def sections(self):
        # First check the the sections a pupil is in directly
        for section in self._getSections(self.person):
            yield section
        # Now check the section membership via groups
        for group in self.person.groups:
            for section in self._getSections(group):
                yield section


class PersonInstructorAdapter(object):
    implements(IInstructor)
    adapts(IPerson)

    def __init__(self, person):
        self.person = person

    def sections(self):
        return getRelatedObjects(self.person, URISection,
                                 rel_type=URIInstruction)
