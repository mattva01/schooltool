#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
Resource booking for sections.
"""

from schooltool.relationship.uri import URIObject
from schooltool.relationship.relationship import RelationshipSchema


URISectionBooking = URIObject('http://schooltool.org/ns/sectionbooking',
                              'Section booking',
                              'The section booking relationship.')
URISection = URIObject('http://schooltool.org/ns/sectionbooking/section',
                       'Section', 'A role of a section.')
URIResource = URIObject('http://schooltool.org/ns/sectionbooking/resource',
                        'Resource', 'The role of a booked resource.')


SectionBooking = RelationshipSchema(URISectionBooking,
                                    section=URISection,
                                    resource=URIResource)
