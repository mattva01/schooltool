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
Membership relationship.

This module defines group membership as a relationship.

    >>> from schoolbell.relationship.tests import setUp, tearDown
    >>> setUp()

    >>> from schoolbell.app.membership import Membership
    >>> from schoolbell.app.app import Person, Group
    >>> jonas = Person()
    >>> petras = Person()
    >>> developers = Group()
    >>> admins = Group()
    >>> Membership(member=jonas, group=developers)
    >>> Membership(member=petras, group=developers)
    >>> Membership(member=petras, group=admins)

    >>> from sets import Set
    >>> from schoolbell.relationship import getRelatedObjects
    >>> Set(getRelatedObjects(developers, URIMember)) == Set([jonas, petras])
    True
    >>> Set(getRelatedObjects(petras, URIGroup)) == Set([admins, developers])
    True

That's all.

    >>> tearDown()

"""

from schoolbell.relationship import URIObject, RelationshipSchema


URIMembership = URIObject('http://schooltool.org/ns/membership',
                          'Membership', 'The membership relationship.')
URIGroup = URIObject('http://schooltool.org/ns/membership/group',
                     'Group', 'A role of a containing group.')
URIMember = URIObject('http://schooltool.org/ns/membership/member',
                      'Member', 'A group member role.')

Membership = RelationshipSchema(URIMembership,
                                member=URIMember,
                                group=URIGroup)
