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
from zope.app import zapi
from zope.app.component import getNextUtility
from zope.app.component.interfaces import ISite
from zope.app.component.interfaces.registration import ActiveStatus
from zope.app.component.site import LocalSiteManager
from zope.app.component.site import UtilityRegistration
from zope.app.container.contained import Contained
from zope.app.container.interfaces import IObjectAddedEvent
from zope.app.location.interfaces import ILocation
from zope.app.security.interfaces import IAuthentication, ILoginPassword
from zope.app.security.interfaces import IAuthenticatedGroup, IEveryoneGroup
from zope.app.session.interfaces import ISession
from zope.app.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.component.servicenames import Utilities
from zope.interface import implements, directlyProvides, directlyProvidedBy
from zope.security.interfaces import IGroupAwarePrincipal
from zope.security.checker import ProxyFactory
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.app.security.interfaces import IUnauthenticatedGroup

from schoolbell.app.app import getSchoolBellApplication
from schoolbell.app.interfaces import ISchoolBellApplication
from schoolbell.app.interfaces import ISchoolBellAuthentication
from schoolbell.app.interfaces import IPerson, IGroup


class Principal(Contained):
    implements(IGroupAwarePrincipal)

    def __init__(self, id, title, person=None):
        self.id = id
        self.title = title
        self.description = ""
        self.groups = []
        self._person = person

    def __conform__(self, interface):
        if interface is IPerson:
            return self._person


class SchoolBellAuthenticationUtility(Persistent, Contained):
    """A local SchoolBell authentication utility.

    This utility serves principals for groups and persons in the
    nearest SchoolBellApplication instance.

    It authenticates the requests containing usernames and passwords
    in the session.
    """

    implements(ISchoolBellAuthentication, ILocation)

    person_prefix = "sb.person."
    group_prefix = "sb.group."
    session_name = "schoolbell.auth"

    def authenticate(self, request):
        """Identify a principal for request.

        Retrieves the username and password from the session.
        """
        session = ISession(request)[self.session_name]
        if 'username' in session and 'password' in session:
            if self._checkPassword(session['username'], session['password']):
                return self.getPrincipal('sb.person.' + session['username'])

        # Try HTTP basic too
        creds = ILoginPassword(request, None)
        if creds:
            login = creds.getLogin()
            if self._checkPassword(login, creds.getPassword()):
                return self.getPrincipal('sb.person.' + login)

    def _checkPassword(self, username, password):
        app = getSchoolBellApplication()
        if username in app['persons']:
            person = app['persons'][username]
            return person.checkPassword(password)

    def unauthenticatedPrincipal(self):
        """Return the unauthenticated principal, if one is defined."""
        return None

    def unauthorized(self, id, request):
        """Signal an authorization failure."""
        if not IBrowserRequest.providedBy(request) or request.method == 'PUT':
            next = getNextUtility(self, IAuthentication)
            return next.unauthorized(id, request)
        if str(request.URL).endswith('.ics'):
            # Special case: testing shows that Mozilla Calendar does not send
            # the Authorization header unless challenged.  It is pointless
            # to redirect an iCalendar client to an HTML login form.
            next = getNextUtility(self, IAuthentication)
            return next.unauthorized(id, request)
        app = getSchoolBellApplication()
        url = zapi.absoluteURL(app, request)
        request.response.redirect("%s/@@login.html?forbidden=yes&nexturl=%s"
                                  % (url, request.URL))

    def getPrincipal(self, id):
        """Get principal meta-data.

        Returns principals for groups and persons.
        """
        app = getSchoolBellApplication()
        if id.startswith(self.person_prefix):
            username = id[len(self.person_prefix):]
            if username in app['persons']:
                person = app['persons'][username]
                principal = Principal(id, person.title,
                                      person=ProxyFactory(person))
                for group in person.groups:
                    group_principal_id = self.group_prefix + group.__name__
                    principal.groups.append(group_principal_id)
                authenticated = zapi.queryUtility(IAuthenticatedGroup)
                if authenticated:
                    principal.groups.append(authenticated.id)
                everyone = zapi.queryUtility(IEveryoneGroup)
                if everyone:
                    principal.groups.append(everyone.id)
                return principal

        if id.startswith(self.group_prefix):
            group_name = id[len(self.group_prefix):]
            if group_name in app['groups']:
                group = app['groups'][group_name]
                # Group membership is not supported in SB, so we don't bother
                # filling in principal.groups.
                return Principal(id, group.title)

        next = getNextUtility(self, IAuthentication)
        return next.getPrincipal(id)

    def setCredentials(self, request, username, password):
        if not self._checkPassword(username, password):
            raise ValueError('bad credentials')
        session = ISession(request)[self.session_name]
        session['username'] = username
        session['password'] = password

    def clearCredentials(self, request):
        session = ISession(request)[self.session_name]
        try:
            del session['password']
            del session['username']
        except KeyError:
            pass

    # See ILogout
    logout = clearCredentials


def setUpLocalAuth(site, auth=None):
    """Set up local authentication for SchoolBell.

    Creates a site management folder in a site and sets up local
    authentication.
    """

    if auth is None:
        auth = SchoolBellAuthenticationUtility()

    if not ISite.providedBy(site):
        site.setSiteManager(LocalSiteManager(site))

    default = zapi.traverse(site, '++etc++site/default')
    reg_manager = default.registrationManager

    if 'SchoolBellAuth' not in default:
        # Add and register the auth utility
        default['SchoolBellAuth'] = auth
        registration = UtilityRegistration('', IAuthentication, auth)
        reg_manager.addRegistration(registration)
        registration.status = ActiveStatus


def authSetUpSubscriber(event):
    """Set up local authentication for newly added SchoolBell apps.

    This is a handler for IObjectAddedEvent.
    """
    if IObjectAddedEvent.providedBy(event):
        if ISchoolBellApplication.providedBy(event.object):
            setUpLocalAuth(event.object)

            # Grant schoolbell.view to all authenticated users
            allusers = zapi.queryUtility(IAuthenticatedGroup)
            if allusers is not None:
                perms = IPrincipalPermissionManager(event.object)
                perms.grantPermissionToPrincipal('schoolbell.view',
                                                 allusers.id)


def personPermissionsSubscriber(event):
    """Grant default permissions to all new persons"""
    if IObjectAddedEvent.providedBy(event):
        if IPerson.providedBy(event.object):
            map = IPrincipalPermissionManager(event.object)
            principalid = 'sb.person.' + event.object.__name__
            map.grantPermissionToPrincipal('schoolbell.view', principalid)
            map.grantPermissionToPrincipal('schoolbell.edit', principalid)
            map.grantPermissionToPrincipal('schoolbell.addEvent', principalid)
            map.grantPermissionToPrincipal('schoolbell.modifyEvent',
                                           principalid)
            map.grantPermissionToPrincipal('schoolbell.viewCalendar',
                                           principalid)
            map.grantPermissionToPrincipal('schoolbell.controlAccess',
                                           principalid)


def groupPermissionsSubscriber(event):
    """Grant default permissions to all new groups"""
    if IObjectAddedEvent.providedBy(event):
        if IGroup.providedBy(event.object):
            map = IPrincipalPermissionManager(event.object)
            principalid = 'sb.group.' + event.object.__name__
            map.grantPermissionToPrincipal('schoolbell.view', principalid)
            map.grantPermissionToPrincipal('schoolbell.viewCalendar',
                                           principalid)


def applicationCalendarPermissionsSubscriber(event):
    """Set permissions on application calendar."""
    if IObjectAddedEvent.providedBy(event):
        if ISchoolBellApplication.providedBy(event.object):
            unauthenticated = zapi.queryUtility(IUnauthenticatedGroup)
            perms = IPrincipalPermissionManager(event.object.calendar)
            perms.grantPermissionToPrincipal('schoolbell.viewCalendar',
                                              unauthenticated.id)
