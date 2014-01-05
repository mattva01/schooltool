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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Relationship URIs and utilities for schooltool
"""

from schooltool.course.interfaces import ICourse, ISection
from schooltool.person.interfaces import IPerson
from schooltool.group.interfaces import IGroup
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.membership import URIMembership, URIMember, URIGroup
from schooltool.relationship import URIObject, RelationshipSchema
from schooltool.relationship.temporal import TemporalURIObject
from schooltool.relationship.interfaces import IBeforeRelationshipEvent
from schooltool.relationship.interfaces import IRelationshipAddedEvent
from schooltool.relationship.interfaces import IRelationshipRemovedEvent
from schooltool.relationship.interfaces import InvalidRelationship


#
# The Instruction relationship
#

URIInstruction = TemporalURIObject('http://schooltool.org/ns/instruction',
                                   'Instruction', 'The instruction relationship.')
URISection = URIObject('http://schooltool.org/ns/instruction/section',
                       'Section', 'A role of a containing section.')
URIInstructor = URIObject('http://schooltool.org/ns/instruction/instructor',
                          'Instructor', 'A section instructor role.')

Instruction = RelationshipSchema(URIInstruction,
                                 instructor=URIInstructor,
                                 section=URISection)


def enforceInstructionConstraints(event):
    """Enforce instruction constraints (IBeforeRelationshipEvent subscriber).
    """
    if not IBeforeRelationshipEvent.providedBy(event):
        return
    if event.rel_type != URIInstruction:
        return
    if ((event.role1, event.role2) != (URIInstructor, URISection) and
        (event.role1, event.role2) != (URISection, URIInstructor)):
        raise InvalidRelationship('Instruction must have one instructor'
                                  ' and one section.')
    if not ISection.providedBy(event[URISection]):
        raise InvalidRelationship('Sections must provide ISection.')


def updateInstructorCalendars(event):
    """Add section's calendar to instructors overlaid calendars."""

    if event.rel_type != URIInstruction:
        return

    person = event[URIInstructor]
    section = event[URISection]
    calendar = ISchoolToolCalendar(section)
    if IRelationshipAddedEvent.providedBy(event):
        if calendar not in person.overlaid_calendars:
            person.overlaid_calendars.add(calendar)
    elif IRelationshipRemovedEvent.providedBy(event):
        if calendar in person.overlaid_calendars:
            person.overlaid_calendars.remove(calendar)


#
# The CourseSection relationship
#


URICourseSections = URIObject('http://schooltool.org/ns/coursesections',
                          'Course Sections',
                          'The sections that implement a course.')

URICourse = URIObject('http://schooltool.org/ns/coursesections/course',
                      'Course', 'A section that implements a course.')

# TODO it seems to me like this should be the same as URISection but because
# the URIs for roles have, so far, included the ../ns/RELATIONSHIP/.. that the
# role participates in I'm creating a seperate role URI.

URISectionOfCourse = URIObject(
                      'http://schooltool.org/ns/coursesections/section',
                      'Section', 'A course of study.')

def enforceCourseSectionConstraint(event):
    """Each CourseSections relationship requires one ICourse and one ISection
    """
    if not IBeforeRelationshipEvent.providedBy(event):
        return
    if event.rel_type != URICourseSections:
        return
    if ((event.role1, event.role2) != (URICourse, URISectionOfCourse) and
        (event.role1, event.role2) != (URISectionOfCourse, URIInstructor)):
        raise InvalidRelationship('CourseSections must have one course'
                                  ' and one section.')
    if not ISection.providedBy(event[URISectionOfCourse]):
        raise InvalidRelationship('Sections must provide ISection.')
    if not ICourse.providedBy(event[URICourse]):
        raise InvalidRelationship('Course must provide ICourse.')


CourseSections = RelationshipSchema(URICourseSections,
                                    course=URICourse,
                                    section=URISectionOfCourse)

#
# Additional handling of the section membership relationship to add sections
# to members' (students') overlay portlets automatically.  In Group membership
# relationships users must manually add the calendar to the portlet (see
# schooltool.app.membership).
#

def updateStudentCalendars(event):
    """Add section's calendar to students overlaid calendars."""

    if event.rel_type != URIMembership:
        return

    section = event[URIGroup]

    # Only continue if we're working with Sections rather than generic groups
    if not ISection.providedBy(section):
        return

    member = event[URIMember]

    calendar = ISchoolToolCalendar(section)
    if IRelationshipAddedEvent.providedBy(event):
        if IPerson.providedBy(member) and \
                calendar not in member.overlaid_calendars:
            member.overlaid_calendars.add(calendar)

        elif IGroup.providedBy(member):
            for person in member.members:
                # we don't handle nested groups any more so there
                # shouldn't be more than one layer of groups
                if IPerson.providedBy(person) and \
                       calendar not in person.overlaid_calendars:
                    person.overlaid_calendars.add(calendar)

    elif IRelationshipRemovedEvent.providedBy(event):
        if IPerson.providedBy(member):
            if calendar in member.overlaid_calendars:
                for group in member.groups:
                    if group in section.members:
                        return
                member.overlaid_calendars.remove(calendar)

        elif IGroup.providedBy(member):
            for person in member.members:
                if IPerson.providedBy(person):
                    if calendar in person.overlaid_calendars:
                        if person not in section.members:
                            person.overlaid_calendars.remove(calendar)


#
# The leadership relationship
#

URILeadership = TemporalURIObject('http://schooltool.org/ns/leadership',
                                  'Leadership', 'The leadership relationship.')
URILeader = URIObject('http://schooltool.org/ns/leadership/leader',
                      'Leader', 'A role of a leader of an asset.')
URIAsset = URIObject('http://schooltool.org/ns/leadership/asset',
                     'Asset', 'An asset of a leader.')

Leadership = RelationshipSchema(URILeadership,
                                leader=URILeader,
                                asset=URIAsset)
