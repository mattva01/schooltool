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
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import ICompositeTimetableProvider
from schooltool.relationship import RelationshipSchema
from schooltool.relationship import RelationshipValenciesMixin
from schooltool.relationship import Valency
from schooltool.uris import URITeaching, URITeacher, URITaught
from schooltool.facet import FacetMixin, FacetFactory, membersGetFacet
from schooltool.component import registerFacetFactory
from schooltool.translation import ugettext as _

__metaclass__ = type

moduleProvides(IModuleSetup)


Teaching = RelationshipSchema(URITeaching,
                              teacher=URITeacher, taught=URITaught)


class TeacherFacet(FacetMixin, RelationshipValenciesMixin):
    """Facet for a teacher."""

    implements(ICompositeTimetableProvider)

    valencies = Valency(Teaching, 'teacher')
    timetableSource = ((URITaught, False), )


class SubjectGroupFacet(FacetMixin, RelationshipValenciesMixin):
    """Facet for a group that is taught by a teacher.

    These groups are called "sections" in US schools.
    """

    valencies = Valency(Teaching, 'taught')


class TeacherGroupFacet(FacetMixin, RelationshipValenciesMixin):
    """Facet for a group of teachers."""

    membersGetFacet(TeacherFacet, facet_name='teacher')


def setUp():
    """See IModuleSetup"""
    registerFacetFactory(FacetFactory(SubjectGroupFacet,
        name='subject_group', title=_('Subject Group')))
    registerFacetFactory(FacetFactory(TeacherGroupFacet,
        name='teacher_group', title=_('Teacher Group')))
