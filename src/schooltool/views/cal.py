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
from schooltool.views import View, textErrorPage
from schooltool.cal import daterange, ICalReader, ICalParseError
from schooltool.component import getPath

__metaclass__ = type


moduleProvides(IModuleSetup)


class SchooldayModelCalendarView(View):
    """iCalendar view for ISchooldayModel."""

    datetime_hook = datetime.datetime

    def do_GET(self, request):
        request.setHeader('Content-Type', 'text/calendar; charset=UTF-8')
        end_date = self.context.last
        uid_suffix = "%s@%s" % (getPath(self.context),
                                request.getRequestHostname())
        dtstamp = self.datetime_hook.utcnow().strftime("%Y%m%dT%H%M%SZ")
        result = [
            "BEGIN:VCALENDAR",
            "PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN",
            "VERSION:2.0",
            "BEGIN:VEVENT",
            "UID:school-period-%s" % uid_suffix,
            "SUMMARY:School Period",
            "DTSTART;VALUE=DATE:%s" % self.context.first.strftime("%Y%m%d"),
            "DTEND;VALUE=DATE:%s" % end_date.strftime("%Y%m%d"),
            "DTSTAMP:%s" % dtstamp,
            "END:VEVENT",
        ]
        for date in daterange(self.context.first, self.context.last):
            if self.context.isSchoolday(date):
                s = date.strftime("%Y%m%d")
                result += [
                    "BEGIN:VEVENT",
                    "UID:schoolday-%s-%s" % (s, uid_suffix),
                    "SUMMARY:Schoolday",
                    "DTSTART;VALUE=DATE:%s" % s,
                    "DTSTAMP:%s" % dtstamp,
                    "END:VEVENT",
                ]
        result.append("END:VCALENDAR")
        return "\r\n".join(result)

    def do_PUT(self, request):
        ctype = request.getHeader('Content-Type')
        if ';' in ctype:
            ctype = ctype[:ctype.index(';')]
        if ctype != 'text/calendar':
            return textErrorPage(request,
                                 "Unsupported content type: %s" % ctype)
        first = last = None
        days = []
        reader = ICalReader(request.content)
        try:
            for event in reader.iterEvents():
                if event.get('summary', '').lower() == 'school period':
                    new_first = event.dtstart
                    new_last = getattr(event, 'dtend', first)
                    if first is None:
                        first, last = new_first, new_last
                    elif (first, last) != (new_first, new_last):
                        return textErrorPage(request,
                                    "Multiple definitions of school period")
                elif event.get('summary', '').lower() == 'schoolday':
                    dtend = getattr(event, 'dtend', event.dtstart)
                    if dtend != event.dtstart:
                        return textErrorPage(request,
                                    "Schoolday longer than one day")
                    days.append(event.dtstart)
                else:
                    continue
                for prop in ('rrule', 'rdate', 'exrule', 'exdate'):
                    if prop in event:
                        return textErrorPage(request,
                            "Repeating events/exceptions not yet supported")
        except ICalParseError, e:
            return textErrorPage(request, str(e))
        else:
            if not first or not last:
                return textErrorPage(request, "School period not defined")
            for day in days:
                if not first <= day <= last:
                    return textErrorPage(request,
                                         "School day outside school period")
            self.context.clear()
            self.context.first = first
            self.context.last = last
            for day in days:
                self.context.add(day)
        request.setHeader('Content-Type', 'text/plain')
        return "Calendar imported"


def setUp():
    """See IModuleSetup."""
    registerView(ISchooldayModel, SchooldayModelCalendarView)

