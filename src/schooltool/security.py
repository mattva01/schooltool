#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Security policy.

This is a centralised place for code that decides whether a certain
user can perform some action on some object(s).

TODO: Not all logic related security policy is moved to this module
yet.

$Id$
"""
from zope.interface import Interface, implements
from zope.app.traversing.api import getPath
from schooltool.component import getRelatedObjects
from schooltool.uris import URIGroup
from schooltool.interfaces import ILocation, IApplicationObject
from schooltool.interfaces import ModifyPermission
from schooltool.interfaces import AddPermission


__metaclass__ = type


class ISecurityPolicy(Interface):
    """A single class that does security decisions"""

    def canBook(person, resource):
        """Can the current user book a resource on behalf of a person?"""

    def canModifyBooking(person, resource):
        """Can the current user modify a booking event on a resource
        on behalf of a person?
        """


class SecurityPolicy:

    implements(ISecurityPolicy)

    def __init__(self, user):
        self.user = user

    def canBook(self, person, resource):
        """Can the current user book a resource on behalf of a person?"""
        if isManager(self.user):
            return True
        if isTeacher(self.user):
            return person.calendar.acl.allows(self.user, AddPermission)
        if (person.calendar.acl.allows(self.user, AddPermission) and
            resource.calendar.acl.allows(self.user, AddPermission)):
            return True
        return False

    def canModifyBooking(self, person, resource):
        """Can the current user modify a booking event on a resource
        on behalf of a person?
        """
        if isManager(self.user):
            return True
        if isTeacher(self.user):
            return person.calendar.acl.allows(self.user, ModifyPermission)
        if (person.calendar.acl.allows(self.user, ModifyPermission) and
            resource.calendar.acl.allows(self.user, ModifyPermission)):
            return True
        return False


def isManager(user):
    """Return True iff user is a manager."""
    if user is None:
        return False
    for group in getRelatedObjects(user, URIGroup):
        if getPath(group) == '/groups/managers':
            return True
    return False


def isTeacher(user):
    """Return True iff user is a teacher or a manager."""
    if user is None:
        return False
    for group in getRelatedObjects(user, URIGroup):
        if getPath(group) in ('/groups/managers', '/groups/teachers'):
            return True
    return False


def getOwner(obj):
    """Returns the owner of an object."""
    owner = obj
    while owner is not None and not IApplicationObject.providedBy(owner):
        if not ILocation.providedBy(owner):
            return None
        owner = owner.__parent__
    return owner
