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
SchoolTool security infrastructure
"""

import urllib

from persistent import Persistent
from zope.component import getUtility, queryUtility
from zope.component import getNextUtility
from zope.container.contained import Contained
from zope.location.interfaces import ILocation
from zope.authentication.interfaces import IAuthentication, ILoginPassword
from zope.authentication.interfaces import IAuthenticatedGroup, IEveryoneGroup
from zope.session.interfaces import ISession
from zope.interface import implements
from schooltool.group.interfaces import IGroupContainer
from zope.security.interfaces import IGroupAwarePrincipal
from zope.security.checker import ProxyFactory
from zope.publisher.browser import FileUpload
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.component.interfaces import ISite
from zope.site import LocalSiteManager
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.traversing.api import traverse

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolAuthentication
from schooltool.app.interfaces import IAsset
from schooltool.person.interfaces import IPerson
from schooltool.app.interfaces import ISchoolToolAuthenticationPlugin
from schooltool.app.interfaces import ICalendarParentCrowd
from schooltool.securitypolicy.interfaces import ICrowdDescription
from schooltool.securitypolicy.crowds import Crowd, Description
from schooltool.securitypolicy.crowds import ManagerGroupCrowd
# XXX: move ConfigurableCrowd here
from schooltool.securitypolicy.crowds import ConfigurableCrowd, ParentCrowd

from schooltool.common import SchoolToolMessage as _


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


class PersonContainerAuthenticationPlugin(object):
    implements(ISchoolToolAuthenticationPlugin)

    person_prefix = "sb.person."
    group_prefix = "sb.group."
    session_name = "schooltool.auth"

    def authenticate(self, request):
        """Identify a principal for request.

        Retrieves the username and password from the session.
        """
        session = ISession(request)[self.session_name]
        if 'username' in session and 'password' in session:
            if self._checkHashedPassword(session['username'], session['password']):
                self.restorePOSTData(request)
                return self.getPrincipal('sb.person.' + session['username'])

        # Try HTTP basic too
        creds = ILoginPassword(request, None)
        if creds:
            login = creds.getLogin()
            if self._checkPlainTextPassword(login, creds.getPassword()):
                return self.getPrincipal('sb.person.' + login)

    def _checkPlainTextPassword(self, username, password):
        app = ISchoolToolApplication(None)
        if username in app['persons']:
            person = app['persons'][username]
            return person.checkPassword(password)

    def _checkHashedPassword(self, username, password):
        app = ISchoolToolApplication(None)
        if username in app['persons']:
            person = app['persons'][username]
            return (person._hashed_password is not None
                    and password == person._hashed_password)

    def unauthenticatedPrincipal(self):
        """Return the unauthenticated principal, if one is defined."""
        return None

    def storePOSTData(self, request):
        session = ISession(request)[self.session_name]
        method = request.get('REQUEST_METHOD')
        if method == 'POST':
            i = 0
            while 'form%s' % i in session:
                i += 1
            form_id = 'form%s' % i
            picklable_form = request.form.copy()
            for k, v in request.form.items():
                if isinstance(v, FileUpload):
                    del picklable_form[k]
            session[form_id] = picklable_form
            return form_id

    def restorePOSTData(self, request):
        form = getattr(request, "form", None)
        if form:
            form_id = request.form.get('post_form')
            if form_id:
                session = ISession(request)[self.session_name]
                form = session.get(form_id, None)
                if form is not None:
                    request.form = form
                    del session[form_id]

    def unauthorized(self, id, request):
        """Signal an authorization failure."""
        app = ISchoolToolApplication(None)
        app_url = absoluteURL(app, request)
        query_string = request.getHeader('QUERY_STRING')
        post_form_id = self.storePOSTData(request)

        if query_string:
            query_string = "?%s" % query_string
            if post_form_id:
                query_string += "&post_form=%s" % post_form_id
        else:
            query_string = ""
            if post_form_id:
                query_string += "?post_form=%s" % post_form_id

        full_url = "%s%s" % (str(request.URL), query_string)
        request.response.redirect("%s/auth/@@login.html?forbidden=yes&nexturl=%s"
                                  % (app_url, urllib.quote(full_url)))

    def getPrincipal(self, id):
        """Get principal meta-data.

        Returns principals for groups and persons.
        """
        app = ISchoolToolApplication(None)
        if id.startswith(self.person_prefix):
            username = id[len(self.person_prefix):]
            if username in app['persons']:
                person = app['persons'][username]
                principal = Principal(id, person.title,
                                      person=ProxyFactory(person))
                for group in person.groups:
                    group_principal_id = self.group_prefix + group.__name__
                    principal.groups.append(group_principal_id)
                authenticated = queryUtility(IAuthenticatedGroup)
                if authenticated:
                    principal.groups.append(authenticated.id)
                everyone = queryUtility(IEveryoneGroup)
                if everyone:
                    principal.groups.append(everyone.id)
                return principal
        return None

    def setCredentials(self, request, username, password):
        # avoid circular imports
        from schooltool.person.person import hash_password
        if not self._checkPlainTextPassword(username, password):
            raise ValueError('bad credentials')
        session = ISession(request)[self.session_name]
        session['username'] = username
        session['password'] = hash_password(password)

    def clearCredentials(self, request):
        session = ISession(request)[self.session_name]
        try:
            del session['password']
            del session['username']
        except KeyError:
            pass


class SchoolToolAuthenticationUtility(Persistent, Contained):
    """A local SchoolTool authentication utility.

    This utility serves principals for groups and persons in the
    nearest SchoolToolApplication instance.

    It authenticates the requests containing usernames and passwords
    in the session.
    """

    implements(ISchoolToolAuthentication, ILocation)

    @property
    def authPlugin(self):
        return getUtility(ISchoolToolAuthenticationPlugin)

    def authenticate(self, request):
        return self.authPlugin.authenticate(request)

    def unauthorized(self, id, request):
        if not IBrowserRequest.providedBy(request) or request.method == 'PUT':
            next = getNextUtility(self, IAuthentication)
            return next.unauthorized(id, request)
        if str(request.URL).endswith('.ics'):
            # Special case: testing shows that Mozilla Calendar does not send
            # the Authorization header unless challenged.  It is pointless
            # to redirect an iCalendar client to an HTML login form.
            next = getNextUtility(self, IAuthentication)
            return next.unauthorized(id, request)
        return self.authPlugin.unauthorized(id, request)

    def unauthenticatedPrincipal(self):
        """Return the unauthenticated principal, if one is defined."""
        return self.authPlugin.unauthenticatedPrincipal()

    def getPrincipal(self, id):
        """Get principal meta-data.

        Returns principals for groups and persons.
        """
        principal = self.authPlugin.getPrincipal(id)
        if not principal:
            next = getNextUtility(self, IAuthentication)
            principal = next.getPrincipal(id)

        return principal

    def setCredentials(self, request, username, password):
        self.authPlugin.setCredentials(request, username, password)

    def clearCredentials(self, request):
        self.authPlugin.clearCredentials(request)

    # See ILogout
    logout = clearCredentials


def setUpLocalAuth(site, auth=None):
    """Set up local authentication for SchoolTool.

    Creates a site management folder in a site and sets up local
    authentication.
    """

    if auth is None:
        auth = SchoolToolAuthenticationUtility()

    if not ISite.providedBy(site):
        site.setSiteManager(LocalSiteManager(site))

    # go to the site management folder
    default = traverse(site, '++etc++site/default')
    # if we already have the auth utility registered, we're done
    if 'SchoolToolAuth' in default:
        return
    # otherwise add it and register it
    default['SchoolToolAuth'] = auth
    manager = site.getSiteManager()
    manager.registerUtility(auth, IAuthentication)


def authSetUpSubscriber(app, event):
    """Set up local authentication for newly added SchoolTool apps.

    This is a handler for IObjectAddedEvent.
    """
    setUpLocalAuth(app)


CalendarViewersCrowd = ParentCrowd(
    ICalendarParentCrowd, 'schooltool.view')


CalendarEditorsCrowd = ParentCrowd(
    ICalendarParentCrowd, 'schooltool.edit')


class LeaderCrowd(Crowd):
    """A crowd that contains leaders of an object."""

    title = _(u'Leaders')
    description = _(u'Assigned leaders.')

    def contains(self, principal):
        assert IAsset.providedBy(self.context)
        person = IPerson(principal, None)
        return person in self.context.leaders


class GroupCrowdDescription(Description):
    implements(ICrowdDescription)

    group = None

    def __init__(self, crowd, action, group):
        self.crowd, self.action, self.group = crowd, action, group

    @property
    def user_group(self):
        if self.crowd.group is None:
            return None
        return self.getGroup(self.crowd.group)

    def getGroup(self, group_principal_id):
        prefix = PersonContainerAuthenticationPlugin.group_prefix
        if not group_principal_id.startswith(prefix):
            return None
        groups = IGroupContainer(ISchoolToolApplication(None), None)
        if groups is None:
            return None
        group_id = group_principal_id[len(prefix):]
        return groups.get(group_id, None)

    @property
    def title(self):
        group = self.user_group
        if group is None:
            return ''
        return group.title

    @property
    def description(self):
        group = self.user_group
        if group is None:
            return ''
        return _(u'${group} group.',
                 mapping={'group': group.title})


class ManagersCrowdDescription(GroupCrowdDescription):

    @property
    def user_group(self):
        return self.getGroup(ManagerGroupCrowd.group)

    @property
    def description(self):
        group = self.user_group
        if group is None:
            return ''
        return _(u'${group} group and the super user.',
                 mapping={'group': group.title})

