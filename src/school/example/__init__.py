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
from schooltool.interfaces import IModuleSetup, ISpecificURI, IFacet
from schooltool.interfaces import IValencyConfigurable
from schooltool.relationship import RelationshipSchema
from schooltool.relationship import Valency
from schooltool.facet import FacetFactory, FacetedRelationshipSchema
from schooltool.component import registerFacetFactory


moduleProvides(IModuleSetup)

class URIParenthood(ISpecificURI):
    "http://schooltool.org/ns/example/parenthood"

class URIParent(ISpecificURI):
    "http://schooltool.org/ns/example/parenthood/parent"

class URIChild(ISpecificURI):
    "http://schooltool.org/ns/example/parenthood/child"

Parent = RelationshipSchema(URIParenthood, parent=URIParent, child=URIChild)

class FacetMixin:
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

# Decorating Parent above to be a faceted schema
Parent = FacetedRelationshipSchema(
            Parent, parent=FacetFactory(ParentFacet, 'Parent'))

class PupilFacet(FacetMixin):

    def __init__(self):
        fullName =''
        dateOfBirth = None
        sex = None

    # has Parenthood valency


PupilMember = FacetedRelationshipSchema(
            Membership, member=FacetFactory(PupilFacet, 'Pupil'))

class PupilGroupFacet(FacetMixin):

    implements(IValencyConfigurable)

    valencies = Valency(PupilMember, 'group')


# Teachers group
# Teacher
# ClassTutor relationship
# Class Tutor: receives events, and logs them for viewing.
# school class:
#   has tutor valency
# tuition class:
#   subject area
# year group:
#   which year
# departments
# RegistrationClassesGroup:
#   Sets RegistrationClass facet on Members.
#   Has Tutor valency


# views for
#   PupilFacet
#   ParentFacet
#   ClassTutor

def setUp():
    """Initialize the example add-ons."""
    print "Initializing example add-ons."
    registerFacetFactory(FacetFactory(PupilGroupFacet, 'Group of Pupils'))
