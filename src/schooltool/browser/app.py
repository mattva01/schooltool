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
Web-application views for the schooltool.app objects.

$Id$
"""

import datetime
import re
from schooltool.browser import View, Template, StaticFile
from schooltool.browser import notFoundPage
from schooltool.browser import absoluteURL
from schooltool.browser.auth import PublicAccess, AuthenticatedAccess
from schooltool.browser.auth import ManagerAccess, globalTicketService
from schooltool.browser.model import PersonView, GroupView, ResourceView
from schooltool.component import getPath
from schooltool.interfaces import IApplication, IApplicationObjectContainer
from schooltool.interfaces import IPerson, AuthenticationError
from schooltool.translation import ugettext as _

__metaclass__ = type


# Time limit for session expiration
session_time_limit = datetime.timedelta(hours=5)


# Person username / group __name__ validation
# XXX Perhaps this constraint is a bit too strict.
valid_name = re.compile("^[a-zA-Z0-9.,'()]+$")


class RootView(View):
    """View for the web application root.

    Presents a login page.  Redirects to a person's information page after
    a successful login.

    Sublocations found at / are

        schooltool.css      the stylesheet
        logout              logout page (accessing it logs you out)
        start               a person's start page
        persons/id          person information pages
        groups/id           group information pages

    """

    __used_for__ = IApplication

    authorization = PublicAccess

    template = Template("www/login.pt")

    error = False
    username = ''

    def do_POST(self, request):
        username = request.args['username'][0]
        password = request.args['password'][0]
        try:
            request.authenticate(username, password)
        except AuthenticationError:
            self.error = True
            self.username = username
            return self.do_GET(request)
        else:
            ticket = globalTicketService.newTicket((username, password),
                                                   session_time_limit)
            request.addCookie('auth', ticket)
            if 'url' in request.args:
                url = request.args['url'][0]
            else:
                url = '/start'
            return self.redirect(url, request)

    def _traverse(self, name, request):
        if name == 'persons':
            return PersonContainerView(self.context['persons'])
        elif name == 'groups':
            return GroupContainerView(self.context['groups'])
        elif name == 'resources':
            return ResourceContainerView(self.context['resources'])
        elif name == 'schooltool.css':
            return StaticFile('www/schooltool.css', 'text/css')
        elif name == 'logo.png':
            return StaticFile('www/logo.png', 'image/png')
        elif name == 'logout':
            return LogoutView(self.context)
        elif name == 'start':
            return StartView(request.authenticated_user)
        raise KeyError(name)


class LogoutView(View):
    """View for /logout.

    Accessing this URL causes the authenticated user to be logged out and
    redirected back to the login page.
    """

    __used_for__ = IApplication

    authorization = PublicAccess

    def do_GET(self, request):
        auth_cookie = request.getCookie('auth')
        globalTicketService.expire(auth_cookie)
        return self.redirect('/', request)


class StartView(View):
    """Start page (/start).

    This is where the user is redirected after logging in.  The start page
    displays common actions.
    """

    __used_for__ = IPerson

    authorization = AuthenticatedAccess

    template = Template("www/start.pt")

    def person_url(self):
        return absoluteURL(self.request, self.context)


class PersonAddView(View):
    """A view for adding persons."""

    __used_for__ = IApplicationObjectContainer

    authorization = ManagerAccess

    template = Template('www/person_add.pt')

    prev_username = ''
    error = None

    def do_POST(self, request):
        username = request.args['username'][0]
        password = request.args['password'][0]
        verify_password = request.args['verify_password'][0]

        if not valid_name.match(username):
            self.error = _('Invalid username')
            return self.do_GET(request)

        self.prev_username = username
        if password != verify_password:
            self.error = _('Passwords do not match')
            return self.do_GET(request)

        # XXX Do we really want to allow empty passwords?
        # XXX Should we care about Unicode vs. UTF-8 passwords?
        #     (see http://issues.schooltool.org/issue96)

        person = self.context.new(username, title=username)
        person.setPassword(password)

        # We could say 'Person created', but we want consistency
        # (AKA wart-compatibility).
        request.appLog(_("Object created: %s") % getPath(person))
        url = absoluteURL(request, person) + '/edit.html'
        return self.redirect(url, request)


class ObjectAddView(View):
    """A view for adding a new object (usually a group or a resource).

    The object should have a view named 'edit.html'.
    """

    __used_for__ = IApplicationObjectContainer

    authorization = ManagerAccess

    template = Template('www/object_add.pt')

    error = u""

    title = _("Add object") # should be overridden by subclasses

    def do_POST(self, request):
        name = request.args['name'][0]

        if not valid_name.match(name):
            self.error = _("Invalid name")
            return self.do_GET(request)

        obj = self.context.new(name, title=name)
        request.appLog(_("Object created: %s") % getPath(obj))

        url = absoluteURL(request, obj) + '/edit.html'
        return self.redirect(url, request)


class GroupAddView(ObjectAddView):

    title = _("Add group")


class ResourceAddView(ObjectAddView):

    title = _("Add resource")
    # XXX The user will be redirected to the nonexistent edit.html.


class ObjectContainerView(View):
    """View for an ApplicationObjectContainer.

    Accessing this location returns a 404 Not Found response.

    Traversing 'add.html' returns an instance of add_view on the container,
    traversing with an object's id returns an instance of obj_view on
    the object.
    """

    __used_for__ = IApplicationObjectContainer

    authorization = PublicAccess

    do_GET = staticmethod(notFoundPage)

    # Must be overridden by actual subclasses.
    add_view = None     # The add view class
    obj_view = None     # The object view class

    def _traverse(self, name, request):
        if name == 'add.html':
            return self.add_view(self.context)
        else:
            return self.obj_view(self.context[name])


class PersonContainerView(ObjectContainerView):

    add_view = PersonAddView
    obj_view = PersonView


class GroupContainerView(ObjectContainerView):

    add_view = GroupAddView
    obj_view = GroupView


class ResourceContainerView(ObjectContainerView):

    add_view = ResourceAddView
    obj_view = ResourceView
