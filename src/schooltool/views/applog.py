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
        if path is None:
            return textErrorPage(request, _("Application log not configured"))

        filter = page = pagesize = None
        if 'filter' in request.args:
            filter = request.args['filter'][0]

        if 'page' in request.args and 'pagesize' in request.args:
            try:
                page = int(request.args['page'][0])
            except ValueError:
                return textErrorPage(request,
                            _("Invalid value for 'page' parameter."))
            try:
                pagesize = int(request.args['pagesize'][0])
                if pagesize <= 0:
                    raise ValueError("page size must be positive")
            except ValueError:
                return textErrorPage(request,
                            _("Invalid value for 'pagesize' parameter."))

        file = self.openLog(path)
        result = file.readlines()
        file.close()

        if filter:
            result = [line for line in result if filter in line]

        if page is not None:
            page, total_pages = self.getPageInRange(page, pagesize, len(result))
            request.setHeader('X-Page', str(page))
            request.setHeader('X-Total-Pages', str(total_pages))
            result = result[(page - 1) * pagesize:page * pagesize]
        return "".join(result)

    def getPageInRange(self, page, pagesize, lines):
        """A helper to cut out a page out of an array of lines.

        For a given page nr, page size in lines, and total length in lines,
        returns the normalized page number and total number of pages.  If the
        client requests a page after the last, she gets the last page.  If the
        client requests a page before the first, she gets the first page.

        You can easily calculate the start and end indexes in the following
        fashion:

          page, total = getPageInRange(page, pagesize, lines)
          start_idx = (page - 1) * pagesize
          end_idx = page * pagesize

        """
        totalpages = (lines + pagesize - 1) / pagesize
        if page < 0:
            page = totalpages + 1 + page
        return max(1, min(page, totalpages)), totalpages

    def openLog(self, filename):
        return file(filename)
