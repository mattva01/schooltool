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
SchoolTool authorization policies.

View authorization policy is a callable that takes a context and a request and
returns True iff access is granted.

Example:

    from schooltool.rest import View, Template
    from schooltool.rest.auth import PublicAccess

    class SomeView(View):
        template = Template('some.pt')
        authorization = PublicAccess

$Id: __init__.py 525 2004-01-02 20:21:50Z alga $
"""

from schooltool.component import getRelatedObjects, getPath
from schooltool.uris import URIGroup
from schooltool.interfaces import ILocation, IApplicationObject
from schooltool.interfaces import ViewPermission, ModifyPermission
from schooltool.interfaces import AddPermission, IACLOwner

__metaclass__ = type


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


def PublicAccess(context, request):
    """Allows read-only access for anyone, changes for managers only."""
    if request.method in ('GET', 'HEAD'):
        return True
    else:
        return isManager(request.authenticated_user)

PublicAccess = staticmethod(PublicAccess)


def PrivateAccess(context, request):
    """Allows access for the owner of the object only."""
    owner = getOwner(context)
    if owner is not None and owner is request.authenticated_user:
        return True
    return isManager(request.authenticated_user)

PrivateAccess = staticmethod(PrivateAccess)


def TeacherAccess(context, request):
    """Allows read-only access for everyone, modifictions for teachers,
    deletion for managers only.
    """
    if request.method in ('GET', 'HEAD'):
        return True
    elif request.method in ('PUT', 'POST'):
        return isTeacher(request.authenticated_user)
    else:
        return isManager(request.authenticated_user)

TeacherAccess = staticmethod(TeacherAccess)


def SystemAccess(context, request):
    """Allows access for managers only."""
    return isManager(request.authenticated_user)

SystemAccess = staticmethod(SystemAccess)


class ACLAccess:
    """Allows access for persons listed in the ACL of context."""

    def __init__(self, get=None, put=None, post=None, delete=None):
        self.permission_map = {'GET': get,
                               'HEAD': get,
                               'PUT': put,
                               'POST': post,
                               'DELETE': delete}

    def __call__(self, context, request):
        """Allows access to the owner of the object, and to the users in ACL"""
        permission = self.permission_map.get(request.method)
        return self.hasPermission(context, request, permission)

    def hasPermission(self, context, request, permission):
        """Checks whether the authenticated user has a given permission.

        Managers and the owner of context always have the permission, even
        if it is not explicitly listed in the ACL.
        """
        if isManager(request.authenticated_user):
            return True
        owner = getOwner(context)
        if owner is not None and owner is request.authenticated_user:
            return True
        if permission is not None and IACLOwner.providedBy(context):
            if context.acl.allows(request.authenticated_user, permission):
                return True
        return False


class CalendarACLAccessClass(ACLAccess):

    def __init__(self):
        ACLAccess.__init__(self, get=ViewPermission)

    def __call__(self, context, request):
        if request.method == 'PUT':
            return (self.hasPermission(context, request, AddPermission)
                    or self.hasPermission(context, request, ModifyPermission))
        else:
            return ACLAccess.__call__(self, context, request)


CalendarACLAccess = CalendarACLAccessClass()

