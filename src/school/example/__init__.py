#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Package implementing add-ons for an example school.

$Id: views.py 265 2003-10-29 15:36:42Z mg $
"""

from zope.interface import moduleProvides, implements, classImplements
from schooltool.component import registerFacetFactory
from schooltool.facet import FacetFactory, FacetedRelationshipSchema
from schooltool.interfaces import IModuleSetup, ISpecificURI, IFacet
from schooltool.interfaces import IRelationshipValencies
from schooltool.membership import Membership
from schooltool.relationship import RelationshipSchema
from schooltool.relationship import RelationshipValenciesMixin
from schooltool.relationship import Valency

moduleProvides(IModuleSetup)

class URIParenthood(ISpecificURI):
    "http://schooltool.org/ns/example/parenthood"

class URIParent(ISpecificURI):
    "http://schooltool.org/ns/example/parenthood/parent"

class URIChild(ISpecificURI):
    "http://schooltool.org/ns/example/parenthood/child"

Parenthood = RelationshipSchema(URIParenthood,
                                parent=URIParent, child=URIChild)

class FacetMixin(RelationshipValenciesMixin):

    implements(IFacet)

    __parent__ = None
    __name__ = None
    active = False
    owner = None


class ParentFacet(FacetMixin):

    def __init__(self):
        # XXX move names etc. into Person
        fullName = ''
        primaryContact = True
        contactPhone = ''
        familialNature = ''

# Decorating Parenthood above to be a faceted schema
Parenthood = FacetedRelationshipSchema(
    Parenthood, parent=FacetFactory(ParentFacet, 'Parent'))

class PupilFacet(FacetMixin):

    valencies = Valency(Parenthood, 'child')

    def __init__(self):
        fullName = ''
        dateOfBirth = None
        sex = None


PupilMember = FacetedRelationshipSchema(
            Membership, member=FacetFactory(PupilFacet, 'Pupil'))

class PupilGroupFacet(FacetMixin):

    valencies = Valency(PupilMember, 'group')


# Teachers group, Teacher

class TeacherFacet(FacetMixin):
    """A Teacher facet"""
    pass

TeachersGroupMembership = FacetedRelationshipSchema(
    Membership, member=FacetFactory(TeacherFacet, 'Tutor'))

class TeachersGroupFacet(FacetMixin):
    """A facet for a group of teachers"""
    valencies  = Valency(TeachersGroupMembership, 'group')


# ClassTutor relationship
# Class Tutor: receives events, and logs them for viewing.

class URIClassTutor(ISpecificURI):
    "http://schooltool.org/ns/example/classtutor"
class URITutor(ISpecificURI):
    "http://schooltool.org/ns/example/classtutor/tutor"
class URIClass(ISpecificURI):
    "http://schooltool.org/ns/example/classtutor/class"

class TutorFacet(FacetMixin):
    """A facet of a tutor of a class"""

    eventTable = () # XXX

ClassTutor = RelationshipSchema(URIClassTutor, cls=URIClass, tutor=URITutor)
ClassTutor = FacetedRelationshipSchema(ClassTutor,
                                       tutor=FacetFactory(TutorFacet, 'Tutor'))

# school class:
#   has tutor valency

class SchoolClassFacet(FacetMixin):
    """A facet of a class with a tutor"""

    valencies = Valency(ClassTutor, 'cls')

# tuition class:
#   subject area

class SubjectClassFacet(FacetMixin):
    """A facet for a subject class"""
    subject = None

# year group:
#   which year

class YearGroupFacet(FacetMixin):
    """A facet for a year group"""
    year = None

# departments

class DepartmentFacet(FacetMixin):
    title = None
    pass

# RegistrationClassesGroup:
#   Sets RegistrationClass facet on Members.
#   Has Tutor valency

class RegistrationClassFacet(FacetMixin):
    pass

RegistrationGroupMembership = FacetedRelationshipSchema(
    Membership,
    member=FacetFactory(RegistrationClassFacet, 'Registration Class'))

class RegistrationClassGroupFacet(FacetMixin):
    valencies = (Valency(RegistrationGroupMembership, 'group'),
                 Valency(ClassTutor, 'cls'))


def setUp():
    """Initialize the example add-ons."""
    print "Initializing example add-ons."
    registerFacetFactory(FacetFactory(PupilGroupFacet, 'Group of Pupils'))
    registerFacetFactory(FacetFactory(SchoolClassFacet, 'Tuition Class'))
    registerFacetFactory(FacetFactory(TeachersGroupFacet, 'Group of Teachers'))
    registerFacetFactory(FacetFactory(RegistrationClassGroupFacet,
                                      'Group of Registration Classes'))

    import school.example.views
    school.example.views.setUp()

