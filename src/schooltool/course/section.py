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
import rwproperty
import zope.interface

from zope.event import notify
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.container.interfaces import IObjectRemovedEvent, INameChooser
from zope.app.container import btree, contained
from zope.component import adapts
from zope.interface import implements
from zope.proxy import sameProxiedObjects
from zope.security.proxy import removeSecurityProxy

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
from schooltool.schoolyear.subscriber import EventAdapterSubscriber
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.schoolyear.interfaces import ISubscriber
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.securitypolicy.crowds import Crowd, AggregateCrowd
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.interfaces import ISection
from schooltool.app.security import ConfigurableCrowd
from schooltool.relationship.relationship import getRelatedObjects
from schooltool.course.interfaces import ILearner, IInstructor
from schooltool.term.term import getNextTerm


class InvalidSectionLinkException(Exception):
    pass


class SectionBeforeLinkingEvent(object):
    def __init__(self, first, second):
        self.first = first
        self.second = second


class Section(Persistent, contained.Contained):

    zope.interface.implements(interfaces.ISectionContained,
                              IAttributeAnnotatable)

    _location = None

    _previous = None
    _next = None

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

    def _unlinkRangeTo(self, other):
        """Unlink sections between self and the other in self.linked_sections."""
        linked = self.linked_sections
        if other not in linked or self is other:
            return
        idx_first, idx_last = sorted([linked.index(self), linked.index(other)])
        linked[idx_first]._next = None
        for section in linked[idx_first+1:idx_last]:
            section._previous = None
            section._next = None
        linked[idx_last]._previous = None

    @rwproperty.getproperty
    def previous(self):
        return self._previous

    @rwproperty.setproperty
    def previous(self, new):
        new = removeSecurityProxy(new)
        if new is self._previous:
            return
        if new is self:
            raise InvalidSectionLinkException(
                _('Cannot assign section as previous to itself'))

        notify(SectionBeforeLinkingEvent(new, self))

        if new is not None:
            self._unlinkRangeTo(new)

        old_prev = self._previous
        self._previous = None
        if old_prev is not None:
            old_prev.next = None
        self._previous = new

        if new is not None:
            new.next = self

    @rwproperty.getproperty
    def next(self):
        return self._next

    @rwproperty.setproperty
    def next(self, new):
        new = removeSecurityProxy(new)
        if new is self._next:
            return
        if new is self:
            raise InvalidSectionLinkException(
                _('Cannot assign section as next to itself'))

        notify(SectionBeforeLinkingEvent(self, new))

        if new is not None:
            self._unlinkRangeTo(new)

        old_next = self._next
        self._next = None
        if old_next is not None:
            old_next.previous = None
        self._next = new

        if new is not None:
            new.previous = self

    @property
    def linked_sections(self):
        sections = [self]

        pit = self.previous
        while pit:
            sections.insert(0, pit)
            pit = pit.previous

        nit = self.next
        while nit:
            sections.append(nit)
            nit = nit.next

        return sections


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


from zope.app.intid.interfaces import IIntIds
from zope.component import getUtility
from zope.component import adapter
from zope.interface import implementer
from schooltool.course.interfaces import ISectionContainer
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.term.interfaces import ITerm

@adapter(ITerm)
@implementer(ISectionContainer)
def getSectionContainer(term):
    int_ids = getUtility(IIntIds)
    term_id = str(int_ids.getId(term))
    app = ISchoolToolApplication(None)
    sc = app['schooltool.course.section'].get(term_id, None)
    if sc is None:
        sc = app['schooltool.course.section'][term_id] = SectionContainer()
    return sc


@adapter(ISectionContainer)
@implementer(ISchoolYear)
def getSchoolYearForSectionContainer(section_container):
    return ISchoolYear(ITerm(section_container))


@adapter(ISection)
@implementer(ISchoolYear)
def getSchoolYearForSection(section):
    return ISchoolYear(ITerm(section.__parent__))


@adapter(ISectionContainer)
@implementer(ITerm)
def getTermForSectionContainer(section_container):
    container_id = int(section_container.__name__)
    int_ids = getUtility(IIntIds)
    container = int_ids.getObject(container_id)
    return container


@adapter(ISection)
@implementer(ITerm)
def getTermForSection(section):
    return ITerm(section.__parent__)


@adapter(ISectionContainer)
@implementer(ICourseContainer)
def getCourseContainerForSectionContainer(section_container):
    return ICourseContainer(ISchoolYear(section_container))


@adapter(ISection)
@implementer(ICourseContainer)
def getCourseContainerForSection(section):
    return ICourseContainer(ISchoolYear(section))


class SectionContainerContainer(btree.BTreeContainer):
    """Container of Section containers."""

    zope.interface.implements(interfaces.ISectionContainerContainer)


class SectionContainer(btree.BTreeContainer):
    """Container of Sections."""

    zope.interface.implements(interfaces.ISectionContainer,
                              IAttributeAnnotatable)


class SectionInit(InitBase):

    def __call__(self):
        self.app['schooltool.course.section'] = SectionContainerContainer()


class InstructorsCrowd(Crowd):
    """Crowd of instructors of a section."""

    title = _(u'Instructors')
    description = _(u'Instructors of the section.')

    def contains(self, principal):
        return IPerson(principal, None) in ISection(self.context).instructors


class PersonInstructorsCrowd(Crowd):
    """Crowd of instructors of a person."""

    title = _(u'Instructors')
    description = _(u'Instructors of a person in any of his sections.')

    def _getSections(self, ob):
        return [section for section in getRelatedObjects(ob, membership.URIGroup)
                if ISection.providedBy(section)]

    def contains(self, principal):
        user = IPerson(principal, None)
        person = IPerson(self.context)
        for section in self._getSections(person):
            if user in section.instructors:
                return True
        return False


class LearnersCrowd(Crowd):
    """Crowd of learners of a section.

    At the moment only direct members of a section are considered as
    learners.
    """
    adapts(ISection)

    title = _(u'Learners')
    description = _(u'Students of the section.')

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


class PersonInstructorAdapter(object):
    implements(IInstructor)
    adapts(IPerson)

    def __init__(self, person):
        self.person = person

    def sections(self):
        return getRelatedObjects(self.person, URISection,
                                 rel_type=URIInstruction)


class RemoveSectionsWhenTermIsDeleted(ObjectEventAdapterSubscriber):
    adapts(IObjectRemovedEvent, ITerm)

    def __call__(self):
        section_container = ISectionContainer(self.object)
        for section_id in list(section_container.keys()):
            del section_container[section_id]


class UnlinkSectionWhenDeleted(ObjectEventAdapterSubscriber):
    adapts(IObjectRemovedEvent, ISection)

    def __call__(self):
        self.object.previous = None
        self.object.next = None


class SectionLinkContinuinityValidationSubscriber(EventAdapterSubscriber):
    adapts(SectionBeforeLinkingEvent)
    implements(ISubscriber)

    def __call__(self):
        if (self.event.first is None or
            self.event.second is None):
            return # unlinking sections

        first_term = ITerm(self.event.first)
        second_term = ITerm(self.event.second)
        if sameProxiedObjects(first_term, second_term):
            raise InvalidSectionLinkException(
                _("Cannot link sections in same term"))

        if not sameProxiedObjects(ISchoolYear(first_term),
                                  ISchoolYear(second_term)):
            raise InvalidSectionLinkException(
                _("Cannot link sections in different school years"))

        if not sameProxiedObjects(getNextTerm(first_term), second_term):
            raise InvalidSectionLinkException(
                _("Sections must be in consecutive terms"))


def copySection(section, target_term):
    """Create a copy of a section in a desired term."""
    section_copy = Section(section.title, section.description)
    sections = ISectionContainer(target_term)
    name = section.__name__
    if name in sections:
        name = INameChooser(sections).chooseName(name, section_copy)
    sections[name] = section_copy
    for course in section.courses:
        section_copy.courses.add(course)
    for instructor in section.instructors:
        section_copy.instructors.add(instructor)
    for member in section.members:
        section_copy.members.add(member)
    return section_copy

