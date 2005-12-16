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

from zope.app import zapi
from zope.app.publisher.browser import BrowserView
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.component import queryMultiAdapter

from schooltool.traverser.interfaces import ITraverserPlugin
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable.interfaces import ITimetableCalendarEvent
from schooltool.calendar.utils import parse_date
from schooltool.course.interfaces import ISection
from schooltool.app.browser import ViewPreferences
from schooltool.person.interfaces import IPerson
from schooltool.group.interfaces import IGroup
from schooltool.attendance.interfaces import IDayAttendance
from schooltool.attendance.interfaces import ISectionAttendance


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


class AttendanceCalendarEventViewlet(object):
    """Viewlet for section meeting calendar events.

    Adds an Attendance link to all section meeting events.
    """

    def attendanceLink(self):
        event_for_display = self.manager.event
        calendar_event = event_for_display.context
        if not ITimetableCalendarEvent.providedBy(calendar_event):
            return None
        section = calendar_event.activity.owner
        if not ISection.providedBy(section):
            return None
        return '%s/attendance/%s/%s' % (
                    zapi.absoluteURL(section, self.request),
                    event_for_display.dtstarttz.date(),
                    calendar_event.period_id)


class RealtimeAttendanceView(BrowserView):
    """Realtime attendance view for a section"""

    __used_for__ = ISection

    def listMembers(self):
        """Return a list of tuples of member data prepared for display.

        This method gathers all members of the section that are
        persons, and all members of section members that are groups.

        Each entry contains the following data:

            person_id, title, attendance_status
        """
        result = []
        for member in self.context.members:
            if IPerson.providedBy(member):
                status = self.studentStatus(member)
                result.append((member.__name__, member.title, status))
            if IGroup.providedBy(member):
                for person in member.members:
                    # recursive groups not supported
                    status = self.studentStatus(person)
                    result.append((person.__name__, person.title, status))

        result.sort(lambda this, other: cmp(this[1], other[1]))
        return result

    def studentStatus(self, student):
        """Returns the attendance status of a student

        This status can be used as the name of a CSS class for this
        student's record in the form.

        The status can be one of:

           attendance-clear     -- no records today
           attendance-ok        -- only 'present' records
           attendance-absent    -- only unexplained absences/tardies
           attendance-alert     -- both presences and absences/tardies recorded
           attendance-explained -- only explained absences/tardies

        """
        records = ISectionAttendance(student).getAllForDay(self.date)
        #records.extend([IDayAttendance(student).get(self.date)])
        was_present = False
        was_absent = False
        was_absent_unexplained = False
        for ar in records:
            if ar.isUnknown():
                continue
            elif ar.isPresent():
                was_present = True
            else:
                was_absent = True
                if not ar.isExplained():
                    was_absent_unexplained = True
        if was_present and was_absent_unexplained:
            return 'attendance-alert'
        elif was_absent and not was_absent_unexplained:
            return 'attendance-explained'
        elif was_absent:
            return 'attendance-absent'
        elif was_present:
            return 'attendance-present'
        else:
            return 'attendance-clear'

