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
Web-application views for the application log.

$Id$
"""

import urllib

from schooltool.browser import View, Template
from schooltool.browser.auth import ManagerAccess
from schooltool.common import to_unicode
from schooltool.rest import absoluteURL
from schooltool.rest.applog import ApplicationLogQuery
from schooltool.translation import ugettext as _
from schooltool.browser import ToplevelBreadcrumbsMixin


class ApplicationLogView(View, ToplevelBreadcrumbsMixin):

    authorization = ManagerAccess

    template = Template('www/applog.pt')

    error = u""

    pagesize = 25

    def do_GET(self, request):
        path = request.site.applog_path
        if path is None:
            self.error = _("Application log not configured")
            return View.do_GET(self, request)

        # TODO: rewrite this view to use widgets
        self.filter_str = None
        if 'filter' in request.args:
            try:
                self.filter_str = to_unicode(request.args['filter'][0])
            except UnicodeError:
                pass

        if 'page' in request.args:
            try:
                page = int(request.args['page'][0])
            except ValueError:
                self.error = _("Invalid value for 'page' parameter.")
                return View.do_GET(self, request)
        else:
            # Note: the ReSTive view returns the last page rather than
            #       the first by default, but that would look very
            #       unnatural on the HTML view.
            page = 1

        if 'prev_filter' in request.args and self.filter_str is not None:
            prev_filter_str = None
            try:
                prev_filter_str = to_unicode(request.args['prev_filter'][0])
            except UnicodeError:
                pass
            if prev_filter_str != self.filter_str:
                page = 1

        applog = self.openLog(path)
        self.query = ApplicationLogQuery(applog, filter_str=self.filter_str,
                                         page=page, pagesize=self.pagesize)
        return View.do_GET(self, request)

    def pageURL(self, page):
        url = absoluteURL(self.request, self.context, 'applog')
        url += '?page=%d' % page
        if self.filter_str:
            url += '&filter=%s' % urllib.quote(self.filter_str)
        return url

    def openLog(self, filename):
        """Open the log file (a hook for unit tests)."""
        return open(filename)

