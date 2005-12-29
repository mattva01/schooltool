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
Views for SchoolTool attendance sparkline

$Id$
"""

import datetime

from schooltool.course.interfaces import ISection
from zope.app.publisher.browser import BrowserView
from schooltool.app.app import getSchoolToolApplication
from schooltool.calendar.utils import parse_date

from schooltool.attendance.sparkline import AttendanceSparkline


class AttendanceSparklineView(BrowserView):
    """Realtime attendance view for a section"""

    __used_for__ = ISection

    def update(self):
        self.section = self.context
        person_id = self.request['person']
        app = getSchoolToolApplication()
        self.person = app['persons'][person_id]
        date = self.request['date']
        self.date = parse_date(date)

    def __call__(self):
        self.update()
        sparkline = AttendanceSparkline(self.person, self.section, self.date)
        self.request.response.setHeader('Content-Type', 'image/png')
        return sparkline.renderAsPngData()


