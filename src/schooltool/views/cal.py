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
Views for calendaring.

$Id$
"""

import datetime
from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.views import View
from schooltool.cal import daterange
from schooltool.component import getPath

__metaclass__ = type


moduleProvides(IModuleSetup)


class SchooldayModelCalendarView(View):
    """iCalendar view for ISchooldayModel."""

    def do_GET(self, request):
        request.setHeader('Content-Type', 'text/calendar; charset=UTF-8')
        end_date = self.context.end - datetime.date.resolution
        uid_suffix = "%s@%s" % (getPath(self.context),
                                request.getRequestHostname())
        result = [
            "BEGIN:VCALENDAR",
            "PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN",
            "VERSION:2.0",
            "BEGIN:VEVENT",
            "UID:school-period-%s" % uid_suffix,
            "SUMMARY:School Period",
            "DTSTART;VALUE=DATE:%s" % self.context.start.strftime("%Y%m%d"),
            "DTEND;VALUE=DATE:%s" % end_date.strftime("%Y%m%d"),
            "END:VEVENT",
        ]
        for date in daterange(self.context.start, self.context.end):
            if self.context.isSchoolday(date):
                s = date.strftime("%Y%m%d")
                result += [
                    "BEGIN:VEVENT",
                    "UID:schoolday-%s-%s" % (s, uid_suffix),
                    "SUMMARY:Schoolday",
                    "DTSTART;VALUE=DATE:%s" % s,
                    "END:VEVENT",
                ]
        result.append("END:VCALENDAR")
        return "\r\n".join(result)


def setUp():
    """See IModuleSetup."""
    registerView(ISchooldayModel, SchooldayModelCalendarView)

