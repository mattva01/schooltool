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
SchoolTool web application authorization policies.

View authorization policy is a callable that takes a context and a request and
returns True iff access is granted.

Example:

    from schooltool.browser import View, Template
    from schooltool.browser.auth import PublicAccess

    class SomeView(View):
        template = Template('some.pt')
        authorization = PublicAccess

$Id$
"""

from schooltool.rest.auth import isManager, isTeacher
from schooltool.rest.auth import PrivateAccess      # reexport

__metaclass__ = type


def PublicAccess(context, request):
    """Allows access for anyone."""
    return True

PublicAccess = staticmethod(PublicAccess)


def AuthenticatedAccess(context, request):
    """Allows access for authenticated users only."""
    return request.authenticated_user is not None

AuthenticatedAccess = staticmethod(AuthenticatedAccess)


def ManagerAccess(context, request):
    """Allows access for managers only."""
    return isManager(request.authenticated_user)

ManagerAccess = staticmethod(ManagerAccess)


def TeacherAccess(context, request):
    """Allows access for managers and teachers only."""
    return isTeacher(request.authenticated_user)

TeacherAccess = staticmethod(TeacherAccess)


class ACLCalendarAccess:
    def __init__(self, permission):
        self.permission = permission
        self.__name__ = self.__class__.__name__

    def __call__(self, context, request):
        if isManager(request.authenticated_user):
            return True
        return context.acl.allows(request.authenticated_user, self.permission)
    
