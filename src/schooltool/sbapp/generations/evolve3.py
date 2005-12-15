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
Upgrade to generation 3.

The first incompatible change from 2 was introduced in rev .

$Id$
"""

from zope.app.annotation.interfaces import IAnnotations
from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication

from schooltool.app.interfaces import ICalendarOwner
from schooltool.relationship.annotatable import getRelationshipLinks
from schooltool.relationship.relationship import LinkSet

def setRelationshipLinks(context, linkset):
    annotations = IAnnotations(context)
    key = 'schooltool.relationship.RelationshipLinks'
    annotations[key] = linkset
    linkset.__name__ = "relationships"
    linkset.__parent__ = context

def upgradeLinkSet(relatable):
    linkSet = LinkSet()
    for link in getRelationshipLinks(relatable)._links:
        linkSet.add(link)
    setRelationshipLinks(relatable, linkSet)

def evolve(context):
    """We have changed underlying LinkSet container.

    LinkSet was replaced with BTreeContainer, LinkSet as well as
    Link became ILocations."""

    root = context.connection.root().get(ZopePublication.root_name, None)
    for calendarOwner in findObjectsProviding(root, ICalendarOwner):
        upgradeLinkSet(calendarOwner)
        upgradeLinkSet(calendarOwner.calendar)
