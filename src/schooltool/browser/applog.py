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

from schooltool.browser import View, Template
from schooltool.browser.auth import ManagerAccess
from schooltool.common import from_locale, to_unicode


class ApplicationLogView(View):

    authorization = ManagerAccess

    template = Template('www/applog.pt')

    error = u""

    def do_GET(self, request):
        # XXX copied with some changes without unittests from the
        # ReST ApplicationLogView.

        path = request.site.applog_path
        if path is None:
            self.error = _("Application log not configured")
            return View.do_GET(self, request)

        filter = None
        page = -1
        pagesize = 30

        if 'filter' in request.args:
            filter = to_unicode(request.args['filter'][0])

        if 'page' in request.args:
            try:
                page = int(request.args['page'][0])
            except ValueError:
                self.error = _("Invalid value for 'page' parameter.")
                return View.do_GET(self, request)

        file = self.openLog(path)
        result = map(from_locale, file.readlines())
        file.close()

        if filter:
            result = [line for line in result if filter in line]

#       if page is not None:
        page, total = self.getPageInRange(page, pagesize, len(result))
        result = result[(page - 1) * pagesize:page * pagesize]

        self.filter = filter or ""
        self.page = page
        self.total = total
        self.log_contents = "".join(result)

        return View.do_GET(self, request)

    def getPageInRange(self, page, pagesize, lines):
        """A helper to cut out a page out of an array of lines."""
        # XXX copied without unittests from the ReST ApplicationLogView.
        totalpages = (lines + pagesize - 1) / pagesize
        if page < 0:
            page = totalpages + 1 + page
        return max(1, min(page, totalpages)), totalpages

    def openLog(self, filename):
        return file(filename)
