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

# XXX should schooltool.browser depend on schooltool.views?
from schooltool.views import View, Template
from schooltool.interfaces import IApplication, AuthenticationError

__metaclass__ = type


class LoginPage(View):

    __used_for__ = IApplication

    template = Template("www/login.pt")
    authorization = lambda self, ctx, rq: True # XXX

    def do_POST(self, request):
        request.setHeader('Content-Type', 'text/html')
        try:
            user = request.site.authenticate(self.context,
                                             request.args['username'][0],
                                             request.args['password'][0])

            return 'OK'
        except AuthenticationError:
            return 'Wrong'

