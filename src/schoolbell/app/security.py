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
from zope.interface import implements, directlyProvides
from zope.app import zapi
from zope.app.security.interfaces import IAuthentication
from zope.app.container.contained import Contained
from zope.app.location.interfaces import ILocation
from zope.security.interfaces import IGroupAwarePrincipal
from zope.app.component.localservice import getNextService
from schoolbell.app.app import getSchoolBellApplication
from zope.app.session.interfaces import ISession

class Principal(Contained):
    implements(IGroupAwarePrincipal)
    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.description = ""
        self.groups = []


class SchoolBellAuthenticationUtility(Persistent):
    """A local SchoolBell authentication utility.

    This utility serves principals for groups and persons in the
    nearest SchoolBellApplication instance.

    It authenticates the requests containing usernames and passwords
    in the session.
    """

    implements(IAuthentication, ILocation)

    person_prefix = "sb.person."
    group_prefix = "sb.group."
    session_name = "schoolbell.auth"

    def authenticate(self, request):
        """Identify a principal for request.

        Retrieves the username and password from the session.
        """
        app = getSchoolBellApplication(self)
        session = ISession(request)[self.session_name]
        if 'username' in session and 'password' in session:
            person = app['persons'][session['username']]
            if person.checkPassword(session['password']):
                return self.getPrincipal('sb.person.' + session['username'])

    def unauthenticatedPrincipal(self):
        """Return the unauthenticated principal, if one is defined."""
        return None

    def unauthorized(self, id, request):
        """Signal an authorization failure."""
        raise NotImplemented
        request.redirect("login.html") #XXX

    def getPrincipal(self, id):
        """Get principal meta-data.

        Returns principals for groups and persons.
        """
        app = getSchoolBellApplication(self)
        if id.startswith(self.person_prefix):
            username = id[len(self.person_prefix):]
            if username in app['persons']:
                person = app['persons'][username]
                principal = Principal(id, person.title)
                for group in person.groups:
                    group_principal_id = self.group_prefix + group.__name__
                    principal.groups.append(group_principal_id)
                return principal

        if id.startswith(self.group_prefix):
            group_name = id[len(self.group_prefix):]
            if group_name in app['groups']:
                group = app['groups'][group_name]
                # Group membership is not supported in SB, so we don't bother
                # filling in principal.groups.
                return Principal(id, group.title)

        next = getNextService(self, 'Utilities')
        return next.getUtility(IAuthentication).getPrincipal(id)
