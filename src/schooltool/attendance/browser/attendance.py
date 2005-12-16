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
Views for SchoolTool attendance

$Id$
"""
import datetime

from zope.app.publisher.browser import BrowserView
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.component import queryMultiAdapter

from schooltool.traverser.interfaces import ITraverserPlugin
from schooltool.calendar.utils import parse_date
from schooltool.timetable.interfaces import ITimetables
from schooltool.app.browser import ViewPreferences


class RealtimeAttendanceView(BrowserView):
    """View for SectionAttendanceInfo object"""
    # XXX: untested!
    def update(self):
        pass


def verifyPeriodForSection(section, date, period_id, tz):
    """Return True if the section has a period with a given id on a
    given date
    """
    start = tz.localize(datetime.datetime.combine(date, datetime.time()))
    end = start + datetime.date.resolution

    for ev in ITimetables(section).makeTimetableCalendar().expand(start, end):
        if period_id == ev.period_id:
            return True
    return False


class SectionAttendanceTraverserPlugin(object):
    """Traverser for attendance views

    This plugin extracts a date and period id from the traversal
    stack, following the view name.
    """

    implements(ITraverserPlugin)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        if name == 'attendance':
            view = queryMultiAdapter((self.context, request),
                                     name=name)
            traversal_stack = request.getTraversalStack()

            try:
                view.date = parse_date(traversal_stack.pop())
                view.period_id = traversal_stack.pop()
            except (ValueError, IndexError):
                raise NotFound(self.context, name, request)


            # This should be the timezone that is used for timetables.
            # If timetables start using the server global timezone,
            # this should be fixed as well.
            tz = ViewPreferences(request).timezone

            if not verifyPeriodForSection(self.context, view.date,
                                          view.period_id, tz):
                raise NotFound(self.context, name, request)
            request.setTraversalStack(traversal_stack)
            return view
        raise NotFound(self.context, name, request)
