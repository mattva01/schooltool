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
Teaching relationship.

$Id$
"""
from zope.interface import moduleProvides, implements
from schooltool.interfaces import ISpecificURI, IModuleSetup, IFacet
from schooltool.relationship import RelationshipSchema
from schooltool.relationship import RelationshipValenciesMixin
from schooltool.relationship import Valency
from schooltool.component import registerFacetFactory
from schooltool.facet import FacetFactory

moduleProvides(IModuleSetup)


class URITeaching(ISpecificURI):
    """http://schooltool.org/ns/teaching"""


class URITeacher(ISpecificURI):
    """http://schooltool.org/ns/teaching/teacher"""


class URITaught(ISpecificURI):
    """http://schooltool.org/ns/teaching/taught"""


Teaching = RelationshipSchema(URITeaching,
                              teacher=URITeacher, taught=URITaught)


class SubjectGroupFacet(RelationshipValenciesMixin):
    """Facet for a group that is taught by a teacher."""

    implements(IFacet)

    __parent__ = None
    __name__ = None
    active = False
    owner = None
    valencies = Valency(Teaching, 'taught')


def setUp():
    registerFacetFactory(FacetFactory(SubjectGroupFacet, 'Subject Group'))
