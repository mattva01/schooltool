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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Relationship maintenance.

Zope 3 content management operations (Delete, Cut, Copy, Paste) do not work
well with relationships unless you register event subscribers that perform
the necessary relationship maintenance.

This module contains event subscribers for IObjectRemovedEvent (and, soon,
others) that update relationships on these changes.
"""

from zope.container.contained import getProxiedObject
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent.interfaces import IObjectCopiedEvent

from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.relationship.relationship import unrelateAll


def unrelateOnDeletion(event):
    """Remove all relationships when an object is deleted."""
    if not IObjectRemovedEvent.providedBy(event):
        return
    linkset = IRelationshipLinks(event.object, None)
    if linkset is not None:
        # event.object may be a ContainedProxy
        unrelateAll(getProxiedObject(event.object))


def unrelateOnCopy(event):
    """Remove all relationships when an object is copied."""
    if not IObjectCopiedEvent.providedBy(event):
        return
    # event.object may be a ContainedProxy
    obj = getProxiedObject(event.object)
    linkset = IRelationshipLinks(obj, None)
    if linkset is not None:
        links_to_remove = []
        for link in linkset:
            other_linkset = IRelationshipLinks(link.target)
            try:
                other_linkset.find(link.role, obj, link.my_role, link.rel_type)
            except ValueError:
                # The corresponding other link was not copied, so we have a
                # degenerate one-sided relationship.  Let's remove it
                # altogether.  It would not difficult to have a different
                # function, cloneRelationshipsOnCopy, that would create
                # a corresponding link in other_linkset.
                links_to_remove.append(link)
        for link in links_to_remove:
            linkset.remove(link)

