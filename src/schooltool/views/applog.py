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
View for the SchoolTool application log.

$Id$
"""

from schooltool.views import View, textErrorPage
from schooltool.views.auth import SystemAccess
from schooltool.translation import ugettext as _

__metaclass__ = type


class ApplicationLogView(View):
    """View for the application log."""

    authorization = SystemAccess

    def do_GET(self, request):
        request.setHeader('Content-Type', 'text/plain')
        path = request.site.applog_path
        if path is not None:
            return self.file_contents(path)
        else:
            return textErrorPage(request, _("Application log not configured"))

    def file_contents(self, name):
        f = open(name)
        try:
            return f.read()
        finally:
            f.close()

