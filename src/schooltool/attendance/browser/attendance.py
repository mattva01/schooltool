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
from pytz import utc

from zope.app import zapi
from zope.app.publisher.browser import BrowserView
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.component import queryMultiAdapter
from zope.viewlet import viewlet
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy

from schooltool.traverser.interfaces import ITraverserPlugin
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable.interfaces import ITimetableCalendarEvent
from schooltool.calendar.utils import parse_date, parse_time
from schooltool.course.interfaces import ISection
from schooltool.app.browser import ViewPreferences
from schooltool.person.interfaces import IPerson
from schooltool.group.interfaces import IGroup
from schooltool.attendance.interfaces import IDayAttendance
from schooltool.attendance.interfaces import ISectionAttendance
from schooltool.attendance.interfaces import ABSENT, TARDY, PRESENT, UNKNOWN
from schooltool import SchoolToolMessage as _


AttendanceCSSViewlet = viewlet.CSSViewlet("attendance.css")


def getPeriodEventForSection(section, date, period_id):
    """Find the section meeting event, if it exists.

    Returns the event of the section meeting if the section has a period with a
    given id on a given date, and None otherwise.
    """
    for ev in ITimetables(section).makeTimetableCalendar(date, date):
        if period_id == ev.period_id:
            return ev
    return None


def formatAttendanceRecord(ar):
    """Returns a short indication of the status of an attendance record:

        >>> class AttendanceRecordStub:
        ...     status = 'ABSENT'
        >>> ar = AttendanceRecordStub()

    '-' for absent:

        >>> formatAttendanceRecord(ar)
        '-'

    'T' for tardy

        >>> ar.status = 'TARDY'
        >>> formatAttendanceRecord(ar)
        'T'

    ' '  for unknown:

        >>> ar.status = 'UNKNOWN'
        >>> formatAttendanceRecord(ar)
        ' '

    And finally, '+' for present.

        >>> ar.status = 'PRESENT'
        >>> formatAttendanceRecord(ar)
        '+'

    """
    if ar.status == ABSENT:
        return '-'
    elif ar.status == TARDY:
        return 'T'
    elif ar.status == PRESENT:
        return '+'
    return ' '


class AttendanceCalendarEventViewlet(object):
    """Viewlet for section meeting calendar events.

    Adds an Attendance link to all section meeting events.
    """

    def attendanceLink(self):
        """Construct the URL for the attendance form for a section meeting.

        Returns None if the calendar event is not a section meeting event.
        """
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


class RealtimeInfo(object):
    """A row of information about a student for the realtime attendance form"""

    def __init__(self, name, title, color, symbol, disabled, sparkline_url):
        self.name = name
        self.title = title
        self.color = color
        self.symbol = symbol
        self.disabled = disabled
        self.sparkline_url = sparkline_url

    def __repr__(self):
        return 'RealtimeInfo(%r, %r, %r, %r, %r, %r)' % \
               (self.name, self.title, self.color, self.symbol, self.disabled,
                self.sparkline_url)


class RealtimeAttendanceView(BrowserView):
    """Realtime attendance view for a section"""

    __used_for__ = ISection

    template = ViewPageTemplateFile("templates/real_time.pt")

    error = None

    # Additional parameters extracted from additional URL elements
    date = None
    period_id = None

    def iterTransitiveMembers(self):
        """Return all transitive members of a section

        Sections can have students as members, and can have groups
        that have students as members.  Groups within groups are not
        allowed.
        """
        persons = []
        for member in self.context.members:
            if IPerson.providedBy(member):
                yield member
            if IGroup.providedBy(member):
                for person in member.members:
                    # recursive groups not supported
                    yield person

    def listMembers(self):
        """Return a list of RealtimeInfo objects about all members"""
        result = []
        meeting = getPeriodEventForSection(self.context, self.date,
                                           self.period_id)
        for person in self.iterTransitiveMembers():
            past_status = self.studentStatus(person)
            ar = ISectionAttendance(person).get(self.context, meeting.dtstart)
            current_status = formatAttendanceRecord(ar)
            disabled_checkbox = ar.isPresent() or ar.isTardy()
            section_url = zapi.absoluteURL(ISection(self.context),
                                   self.request)
            sparkline_url = '%s/@@sparkline.png?person=%s&date=%s' % \
                            (section_url, person.username, self.date)

            result.append(RealtimeInfo(
                person.__name__, # id
                person.title,    # title
                past_status,     # colour
                current_status,  # letter
                disabled_checkbox,
                sparkline_url
                ))

        result.sort(key=lambda this: this.title)
        return result

    def getDaysAttendanceRecords(self, student, date):
        """Return all attendance records for a student and a given date."""
        records = list(ISectionAttendance(student).getAllForDay(date))
        records.append(IDayAttendance(student).get(date))
        return records

    def studentStatus(self, student):
        """Returns the attendance status of a student

        This status can be used as the name of a CSS class for this
        student's record in the form.

        The status can be one of:

           attendance-clear     -- no records today
           attendance-present   -- only 'present' records
           attendance-absent    -- only unexplained absences/tardies
           attendance-alert     -- both presences and absences/tardies recorded
           attendance-explained -- only explained absences/tardies

        """
        was_present = False
        was_absent = False
        was_absent_unexplained = False
        for ar in self.getDaysAttendanceRecords(student, self.date):
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

    def update(self):
        """Process form submissions."""
        meeting = getPeriodEventForSection(self.context, self.date,
                                           self.period_id)

        # If there are persons with UNKNOWN status, show the 'absent' button,
        # otherwise show 'tardy' and 'arrived'.
        self.unknowns = False

        if 'TARDY' in self.request:
            try:
                arrived = self.getArrival()
            except ValueError:
                self.error = _('The arrival time you entered is '
                               'invalid.  Please use HH:MM format')
                return

        for person in self.iterTransitiveMembers():
            attendance = ISectionAttendance(person)
            ar = attendance.get(self.context, meeting.dtstart)
            check_id = "%s_check" % person.__name__

            if 'ABSENT' in self.request:
                if check_id in self.request and ar.isUnknown():
                    attendance.record(
                        removeSecurityProxy(self.context), meeting.dtstart,
                        meeting.duration, self.period_id, False)
                elif ar.isUnknown():
                    attendance.record(
                        removeSecurityProxy(self.context), meeting.dtstart,
                        meeting.duration, self.period_id, True)

            if 'TARDY' in self.request:
                if check_id in self.request and ar.isAbsent():
                    ar.makeTardy(arrived)

            ar = attendance.get(self.context, meeting.dtstart)
            if ar.isUnknown():
                self.unknowns = True

    def getArrival(self):
        """Extracts the date of late arrivals from the request.

        If the time is not specified, defaults to now.
        """
        if self.request.get('arrival'):
            tz = ViewPreferences(self.request).timezone
            time = parse_time(self.request['arrival'])
            result = datetime.datetime.combine(self.date, time)
            return tz.localize(result)
        return datetime.datetime.utcnow().replace(tzinfo=utc)

    def publishTraverse(self, request, name):
        """Collect additional URL elements."""
        if self.date is None:
            try:
                self.date = parse_date(name)
                return self
            except ValueError:
                pass # will raise NotFound at the end
        elif self.period_id is None:
            self.period_id = name
            return self
        raise NotFound(self.context, name, self.request)

    def verifyParameters(self):
        """Check if the date and period_id parameters are valid.

        Raises a NotFound error if they aren't.
        """
        if self.date is None or self.period_id is None:
            # Not enough traversal path elements
            raise NotFound(self.context, self.__name__, self.request)
        if not getPeriodEventForSection(self.context, self.date,
                                        self.period_id):
            raise NotFound(self.context, self.__name__, self.request)

    def __call__(self):
        """Process form submissions and render the view."""
        self.verifyParameters()
        self.update()
        return self.template()

