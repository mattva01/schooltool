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
SchoolBell security infrastructure

$Id$
"""

from persistent import Persistent
from zope.interface import implements
from zope.app import zapi
from zope.app.security.interfaces import IAuthentication
from zope.app.container.contained import Contained
from zope.app.location.interfaces import ILocation
from zope.app.security.interfaces import IPrincipal
from zope.app.component.localservice import getNextService
from schoolbell.app.app import getSchoolBellApplication


class Principal(Contained):
    implements(IPrincipal)
    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.description = ""


class SchoolBellAuthenticationUtility(Persistent):
    implements(IAuthentication, ILocation)

    def authenticate(self, request):
        """Identify a principal for request"""

    def unauthenticatedPrincipal(self):
        """Return the unauthenticated principal, if one is defined."""
        return None

    def unauthorized(self, id, request):
        """Signal an authorization failure."""
        request.redirect("login.html") #XXX

    def getPrincipal(self, id):
        """Get principal meta-data.

        Returns principals for groups and persons.
        """
        app = getSchoolBellApplication(self)
        for person in app['persons'].values():
            if person.__name__ == id:
                principal = Principal(person.username, person.title)
                return principal

        next = getNextService(self, 'Utilities')
        return next.getUtility(IAuthentication).getPrincipal(id)
