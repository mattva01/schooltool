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
import operator
from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import ISchooldayModel, ICalendar
from schooltool.views import View, textErrorPage
from schooltool.cal import ICalReader, ICalParseError
from schooltool.cal import ical_text, ical_duration
from schooltool.component import getPath
from schooltool.component import registerView

__metaclass__ = type


moduleProvides(IModuleSetup)


class SchooldayModelCalendarView(View):
    """iCalendar view for ISchooldayModel."""

    datetime_hook = datetime.datetime

    def do_GET(self, request):
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
        for date in self.context:
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
        request.setHeader('Content-Type', 'text/calendar; charset=UTF-8')
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
            complex_prop_names = ('RRULE', 'RDATE', 'EXRULE', 'EXDATE')
            for event in reader.iterEvents():
                summary = event.getOne('SUMMARY', '').lower()
                if summary not in ('school period', 'schoolday'):
                    continue # ignore boring events

                if not event.all_day_event:
                    return textErrorPage(request,
                             "All-day event should be used")

                has_complex_props = reduce(operator.or_,
                                      map(event.hasProp, complex_prop_names))

                if has_complex_props:
                    return textErrorPage(request,
                             "Repeating events/exceptions not yet supported")

                if summary == 'school period':
                    if (first is not None and
                        (first, last) != (event.dtstart, event.dtend)):
                        return textErrorPage(request,
                                    "Multiple definitions of school period")
                    else:
                        first, last = event.dtstart, event.dtend
                elif summary == 'schoolday':
                    if event.duration != datetime.date.resolution:
                        return textErrorPage(request,
                                    "Schoolday longer than one day")
                    days.append(event.dtstart)
        except ICalParseError, e:
            return textErrorPage(request, str(e))
        else:
            if first is None:
                return textErrorPage(request, "School period not defined")
            for day in days:
                if not first <= day < last:
                    return textErrorPage(request,
                                         "Schoolday outside school period")
            self.context.reset(first, last - datetime.date.resolution)
            for day in days:
                self.context.add(day)
        request.setHeader('Content-Type', 'text/plain')
        return "Calendar imported"


class CalendarView(View):
    """iCalendar view for ICalendar."""

    datetime_hook = datetime.datetime

    def do_GET(self, request):
        dtstamp = self.datetime_hook.utcnow().strftime("%Y%m%dT%H%M%SZ")
        uid_suffix = "%s@%s" % (getPath(self.context),
                                request.getRequestHostname())
        result = [
            "BEGIN:VCALENDAR",
            "PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN",
            "VERSION:2.0",
        ]
        for event in self.context:
            uid_hash = hash((event.title, event.dtstart, event.duration))
            result += [
                "BEGIN:VEVENT",
                "UID:%d-%s" % (uid_hash, uid_suffix),
                "SUMMARY:%s" % ical_text(event.title),
                "DTSTART:%s" % event.dtstart.strftime('%Y%m%dT%H%M%S'),
                "DURATION:%s" % ical_duration(event.duration),
                "DTSTAMP:%s" % dtstamp,
                "END:VEVENT",
            ]
        result.append("END:VCALENDAR")
        request.setHeader('Content-Type', 'text/calendar; charset=UTF-8')
        return "\r\n".join(result)


def setUp():
    """See IModuleSetup."""
    registerView(ISchooldayModel, SchooldayModelCalendarView)
    registerView(ICalendar, CalendarView)

