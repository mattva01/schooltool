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
Browser views for calendaring.

$Id$
"""

import datetime

from schooltool.browser import View, Template, notFoundPage
from schooltool.browser.auth import ManagerAccess
from schooltool.cal import CalendarEvent, Period
from schooltool.common import to_unicode, parse_datetime
from schooltool.component import traverse, getPath
from schooltool.interfaces import IResource
from schooltool.translation import ugettext as _


class BookingView(View):

    __used_for__ = IResource

    authorization = ManagerAccess # XXX Should be accessible by teachers too

    error = u""

    do_GET = staticmethod(notFoundPage)

    # XXX Errors are not shown to the user.
    def do_POST(self, request):
        if 'conflicts' in request.args:
            force = (request.args['conflicts'][0] == 'ignore')
        else:
            force = False
        owner_path = to_unicode(request.args['owner'][0])
        start_date_str = to_unicode(request.args['start_date'][0])
        start_time_str = to_unicode(request.args['start_time'][0])
        duration_str = to_unicode(request.args['duration'][0])

        try:
            owner = traverse(self.context, owner_path)
        except KeyError:
            self.error = _("Invalid owner path: %r") % owner_path
            return

        try:
            arg = 'start_date'
            year, month, day = map(int, start_date_str.split('-'))
            datetime.date(year, month, day) # validation
            arg = 'start_time'
            hours, seconds = map(int, start_time_str.split(':'))
            datetime.time(hours, seconds)   # validation

            start = datetime.datetime(year, month, day, hours, seconds)

            arg = 'duration'
            duration = datetime.timedelta(minutes=int(duration_str))
        except (ValueError, TypeError):
            self.error = _("%r argument incorrect") % arg
            return

        if not force:
            p = Period(start, duration)
            for e in self.context.calendar:
                if p.overlaps(Period(e.dtstart, e.duration)):
                    self.error = _("The resource is busy at specified time")
                    return

        title = _('%s booked by %s') % (self.context.title, owner.title)
        ev = CalendarEvent(start, duration, title, owner, self.context)
        self.context.calendar.addEvent(ev)
        owner.calendar.addEvent(ev)
        request.appLog(_("%s (%s) booked by %s (%s) at %s for %s") %
                       (getPath(self.context), self.context.title,
                        getPath(owner), owner.title, start, duration))
