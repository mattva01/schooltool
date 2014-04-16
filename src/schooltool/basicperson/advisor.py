#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
BasicPerson advisor relationship.
"""
from schooltool.relationship.relationship import RelationshipSchema
from schooltool.relationship.uri import URIObject
from schooltool.relationship.temporal import TemporalURIObject
from schooltool.relationship.temporal import ACTIVE, INACTIVE
from schooltool.app.states import StateStartUpBase

from schooltool.common import SchoolToolMessage as _


URIAdvising = TemporalURIObject('http://schooltool.org/ns/advising',
                                'Advising', 'The advising relationship.')
URIStudent = URIObject('http://schooltool.org/ns/advising/student',
                       'Student', 'An advising relationship student role.')
URIAdvisor = URIObject('http://schooltool.org/ns/advising/advisor',
                       'Advisor', 'An advising relationship advisor role.')

Advising = RelationshipSchema(URIAdvising,
                              advisor=URIAdvisor,
                              student=URIStudent)



class AdvisorStatesStartUp(StateStartUpBase):

    states_name = 'person-advisors'
    states_title = _('Advisors')

    def populate(self, states):
        super(AdvisorStatesStartUp, self).populate(states)
        states.add(_('Advising'), ACTIVE, 'a')
        states.add(_('Removed'), INACTIVE, 'i')
        states.add(_('Added in error'), INACTIVE, 'e')
