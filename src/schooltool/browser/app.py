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

from schooltool.browser import View, Template, StaticFile
from schooltool.browser import absoluteURL
from schooltool.browser.model import PersonView, GroupView
from schooltool.interfaces import IApplication
from schooltool.interfaces import IApplicationObjectContainer
from schooltool.interfaces import AuthenticationError

__metaclass__ = type


class RootView(View):
    """View for the web application root.

    Presents a login page.  Redirects to a person's information page after
    a successful login.
    """

    __used_for__ = IApplication

    template = Template("www/login.pt")

    error = False
    username = ''

    def do_POST(self, request):
        username = request.args['username'][0]
        password = request.args['password'][0]
        try:
            user = request.site.authenticate(self.context, username, password)
        except AuthenticationError:
            self.error = True
            self.username = username
            return self.do_GET(request)
        else:
            return self.redirect(absoluteURL(request, user), request)

    def _traverse(self, name, request):
        if name == 'persons':
            return PersonContainerView(self.context['persons'])
        if name == 'groups':
            return GroupContainerView(self.context['groups'])
        elif name == 'schooltool.css':
            return StaticFile('www/schooltool.css', 'text/css')
        raise KeyError(name)


class PersonContainerView(View):

    __used_for__ = IApplicationObjectContainer

    def _traverse(self, name, request):
        return PersonView(self.context[name])


class GroupContainerView(View):

    __used_for__ = IApplicationObjectContainer

    def _traverse(self, name, request):
        return GroupView(self.context[name])

