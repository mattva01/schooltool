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
Implementation of relationships for IAnnotatable objects.

Relationships are represented as collections of links.  A link defines one
half of a relationship.  The storage of links on an object is determined by
an IRelationshipLinks adapter.  There is a default adapter registered for
all IAnnotatable objects that uses Zope 3 annotations.
"""

from zope.app.annotation.interfaces import IAnnotations
from schooltool.relationship.relationship import LinkSet


def getRelationshipLinks(context):
    """Adapt an IAnnotatable object to IRelationshipLinks."""
    annotations = IAnnotations(context)
    key = 'schooltool.relationship.RelationshipLinks'
    try:
        return annotations[key]
    except KeyError:
        annotations[key] = LinkSet()
        annotations[key].__parent__ = context
        annotations[key].__name__ = "relationships"
        return annotations[key]
