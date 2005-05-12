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
Relationship URIs and utilities for schooltool

$Id$

"""

import sets

from schoolbell.relationship import URIObject, RelationshipSchema
from schoolbell.relationship import getRelatedObjects
from schoolbell.relationship.interfaces import IBeforeRelationshipEvent
from schoolbell.relationship.interfaces import InvalidRelationship
from schooltool.interfaces import ISection, ICourse

#
# The Instruction relationship
#

URIInstruction = URIObject('http://schooltool.org/ns/instruction',
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
