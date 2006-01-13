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
Storage of attendance records.

$Id$
"""
__docformat__ = 'reStructuredText'

import datetime

import pytz
from persistent import Persistent
from persistent.list import PersistentList
from persistent.dict import PersistentDict
from zope.interface import implements
from zope.app.annotation.interfaces import IAnnotations
from zope.i18n import translate
from zope.app.location.location import Location
from zope.wfmc.interfaces import IWorkItem
from zope.wfmc.interfaces import IParticipant
from zope.wfmc.interfaces import IActivity
from zope.wfmc.interfaces import IProcessDefinition
from zope.interface import implements
from zope.component import adapts
from zope.app import zapi
from zope.security.proxy import removeSecurityProxy

from schooltool import SchoolToolMessage as _
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.calendar.simple import ImmutableCalendar
from schooltool.calendar.simple import SimpleCalendarEvent
from schooltool.attendance.interfaces import IDayAttendance
from schooltool.attendance.interfaces import IDayAttendanceRecord
from schooltool.attendance.interfaces import ISectionAttendance
from schooltool.attendance.interfaces import ISectionAttendanceRecord
from schooltool.attendance.interfaces import IAbsenceExplanation
from schooltool.attendance.interfaces import UNKNOWN, PRESENT, ABSENT, TARDY
from schooltool.attendance.interfaces import NEW, ACCEPTED, REJECTED
from schooltool.attendance.interfaces import AttendanceError
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.person.interfaces import IPerson


#
# Attendance record classes
#

class AttendanceRecord(Persistent):
    """Base class for attendance records."""

    def __init__(self, status):
        assert status in (UNKNOWN, PRESENT, ABSENT)
        self.status = status
        self.late_arrival = None
        self.explanations = PersistentList()
        if status == ABSENT:
            self._createWorkflow()

    def _createWorkflow(self):
        pd = zapi.getUtility(IProcessDefinition,
                             name='schooltool.attendance.explanation')
        pd().start(self)

    def isUnknown(self): return self.status == UNKNOWN
    def isPresent(self): return self.status == PRESENT
    def isAbsent(self):  return self.status == ABSENT
    def isTardy(self):   return self.status == TARDY

    def isExplained(self):
        if self.status not in (ABSENT, TARDY):
            raise AttendanceError(
                "only absences and tardies can be explained.")
        for e in self.explanations:
            if e.isAccepted():
                return True
        return False

    def acceptExplanation(self):
        # TODO: more sanity checks (e.g. don't overrule previous rejections)
        self._work_item.acceptExplanation()

    def rejectExplanation(self):
        # TODO: more sanity checks (e.g. don't overrule previous acceptances)
        self._work_item.rejectExplanation()

    def addExplanation(self, text):
        if self.status not in (ABSENT, TARDY):
            raise AttendanceError(
                "only absences and tardies can be explained.")
        if (self.explanations and
            not self.explanations[-1].isProcessed()):
            raise AttendanceError(
                "you have unprocessed explanations.")
        if (self.explanations and
            self.explanations[-1].isAccepted()):
            raise AttendanceError(
                "can't add an explanation to an explained absence.")
        explanation = AbsenceExplanation(text)
        self.explanations.append(explanation)

    def makeTardy(self, arrival_time):
        assert type(arrival_time) == datetime.datetime
        if not self.isAbsent():
            raise AttendanceError("makeTardy when status is %s, not ABSENT"
                                  % self.status)
        self._work_item.makeTardy(arrival_time)


class AbsenceExplanation(Persistent):
    """An explanation of an absence/tardy."""

    implements(IAbsenceExplanation)

    def __init__(self, text):
        self.text = text
        self.status = NEW

    def isProcessed(self):
        return self.status != NEW

    def isAccepted(self):
        return self.status == ACCEPTED


class DayAttendanceRecord(AttendanceRecord):
    """Record of a student's presence or absence on a given day."""

    implements(IDayAttendanceRecord)

    def __init__(self, date, status):
        assert type(date) == datetime.date
        AttendanceRecord.__init__(self, status)
        self.date = date

    def __repr__(self):
        return 'DayAttendanceRecord(%r, %s)' % (self.date, self.status)


class SectionAttendanceRecord(AttendanceRecord):
    """Record of a student's presence or absence at a given section meeting."""

    implements(ISectionAttendanceRecord)

    def __init__(self, section, datetime, status,
                 duration=datetime.timedelta(0), period_id=None):
        assert datetime.tzinfo is not None, 'need datetime with timezone'
        AttendanceRecord.__init__(self, status)
        self.section = section
        self.datetime = datetime
        self.duration = duration
        self.period_id = period_id

    @property
    def date(self):
        app = ISchoolToolApplication(None)
        tzinfo = pytz.timezone(IApplicationPreferences(app).timezone)
        return self.datetime.astimezone(tzinfo).date()

    def __repr__(self):
        return 'SectionAttendanceRecord(%r, %r, %s)' % (self.section,
                                                        self.datetime,
                                                        self.status)


#
# Attendance storage classes
#


class AttendanceFilteringMixin(object):
    """Mixin that implements IAttendance.filter on top of __iter__."""

    def filter(self, first, last):
        assert type(first) == datetime.date
        assert type(last) == datetime.date
        for ar in self:
            if first <= ar.date <= last:
                yield ar


class AttendanceCalendarMixin(object):
    """Mixin that implements IAttendance.makeCalendar on top of filter.

    Classes that mix this in need to provide the following methods:

        tardyEventTitle(record)
        absenceEventTitled(record)
        makeCalendarEvent(record, title)

    """

    def incidentDescription(self, record):
        """The description of the event for the attendance record."""
        # The mapping argument is here to suppress a spurious deprecation
        # warning.  See Zope 3 bug http://www.zope.org/Collectors/Zope3-dev/531
        workaround = {'': ''}
        if record.isExplained():
            return translate(_("Explanation was accepted.", mapping=workaround))
        else:
            return translate(_("Is not explanained yet.", mapping=workaround))

    def makeCalendar(self):
        events = []
        for record in self:
            title = None
            if record.isTardy():
                title = self.tardyEventTitle(record)
            elif record.isAbsent():
                title = self.absenceEventTitle(record)
            if title:
                description = self.incidentDescription(record)
                event = self.makeCalendarEvent(record, title, description)
                event.__parent__ = None
                events.append(event)
        return ImmutableCalendar(events)


class DayAttendance(Persistent, AttendanceFilteringMixin,
                    AttendanceCalendarMixin):
    """Persistent object that stores day attendance records for a student."""

    implements(IDayAttendance)

    def __init__(self):
        self._records = PersistentDict()
        # When it is time to optimize, convert it to OOBTree

    def __iter__(self):
        return iter(self._records.values())

    def tardyEventTitle(self, record):
        """Produce a title for a calendar event representing a tardy."""
        return translate(_('Was late for homeroom.'))

    def absenceEventTitle(self, record):
        """Produce a title for a calendar event representing an absence."""
        return translate(_('Was absent from homeroom.'))

    def makeCalendarEvent(self, record, title, description):
        """Produce a calendar event for an absence or a tardy."""
        # XXX mg: Having to specify a date*time* for an all-day event makes NO
        #         SENSE WHATSOEVER.  Grr!
        dtstart = datetime.datetime.combine(record.date, datetime.time())
        return SimpleCalendarEvent(title=title,
                                   description=description,
                                   dtstart=dtstart,
                                   duration=datetime.timedelta(1),
                                   allday=True)

    def get(self, date):
        assert type(date) == datetime.date
        try:
            return self._records[date]
        except KeyError:
            return DayAttendanceRecord(date, UNKNOWN)

    def record(self, date, present):
        assert type(date) == datetime.date
        if date in self._records:
            raise AttendanceError('record for %s already exists' % date)
        if present: status = PRESENT
        else: status = ABSENT
        self._records[date] = DayAttendanceRecord(date, status)


class SectionAttendance(Persistent, AttendanceFilteringMixin,
                        AttendanceCalendarMixin):
    """Persistent object that stores section attendance records for a student.
    """

    implements(ISectionAttendance)

    def __init__(self):
        self._records = PersistentList()
        # When it is time to optimize, I think self._records should be replaced
        # with a OOBTree, indexed by date.

    def __iter__(self):
        return iter(self._records)

    def tardyEventTitle(self, record):
        """Produce a title for a calendar event representing a tardy."""
        minutes_late = (record.late_arrival - record.datetime).seconds / 60
        return translate(_('Was late for ${section} (${mins} minutes).',
                           mapping={'section': record.section.title,
                                    'mins': minutes_late}))

    def absenceEventTitle(self, record):
        """Produce a title for a calendar event representing an absence."""
        return translate(_('Was absent from ${section}.',
                           mapping={'section': record.section.title}))

    def makeCalendarEvent(self, record, title, description):
        """Produce a calendar event for an absence or a tardy."""
        return SimpleCalendarEvent(title=title,
                                   description=description,
                                   dtstart=record.datetime,
                                   duration=record.duration)

    def getAllForDay(self, date):
        return self.filter(date, date)

    def get(self, section, datetime):
        for ar in self._records:
            if (ar.section, ar.datetime) == (section, datetime):
                return ar
        return SectionAttendanceRecord(section, datetime, status=UNKNOWN)

    def record(self, section, datetime, duration, period_id, present):
        if self.get(section, datetime).status != UNKNOWN:
            raise AttendanceError('record for %s at %s already exists'
                                  % (section, datetime))
        if present: status = PRESENT
        else: status = ABSENT
        ar = SectionAttendanceRecord(section, datetime, status=status,
                                     duration=duration, period_id=period_id)
        self._records.append(ar)


#
# Adapters
#

DAY_ATTENDANCE_KEY = 'schooltool.attendance.DayAttendance'
SECTION_ATTENDANCE_KEY = 'schooltool.attendance.SectionAttendance'


def getSectionAttendance(person):
    """Return the section attendance record for a person."""
    annotations = IAnnotations(person)
    try:
        attendance = annotations[SECTION_ATTENDANCE_KEY]
    except KeyError:
        attendance = SectionAttendance()
        annotations[SECTION_ATTENDANCE_KEY] = attendance
    return attendance


def getDayAttendance(person):
    """Return the section attendance record for a person."""
    annotations = IAnnotations(person)
    try:
        attendance = annotations[DAY_ATTENDANCE_KEY]
    except KeyError:
        attendance = DayAttendance()
        annotations[DAY_ATTENDANCE_KEY] = attendance
    return attendance


#
# Workflow
#

class AttendanceAdmin(Persistent):
    adapts(IActivity)
    implements(IParticipant)

    def __init__(self, activity):
        self.activity = activity


class AttendanceWorkItem(Persistent, Location):

    adapts(IParticipant)
    implements(IWorkItem)

    def __init__(self, participant):
        self.participant = participant


class WaitForExplanation(AttendanceWorkItem):

    def start(self, attendance_record):
        attendance_record._work_item = self

    def makeTardy(self, arrival_time):
        self.participant.activity.workItemFinished(self, 'tardy', arrival_time)

    def rejectExplanation(self):
        self.participant.activity.workItemFinished(self, 'reject', None)

    def acceptExplanation(self):
        self.participant.activity.workItemFinished(self, 'accept', None)


class MakeTardy(AttendanceWorkItem):

    def start(self, attendance_record, arrival_time):
        attendance_record.status = TARDY
        attendance_record.late_arrival = arrival_time
        self.participant.activity.workItemFinished(self)


class AcceptExplanation(AttendanceWorkItem):

    def start(self, attendance_record):
        attendance_record.explanations[-1].status = ACCEPTED
        self.participant.activity.workItemFinished(self)


class RejectExplanation(AttendanceWorkItem):

    def start(self, attendance_record):
        attendance_record.explanations[-1].status = REJECTED
        self.participant.activity.workItemFinished(self)

#
# Calendar Provider
#

class AttendanceCalendarProvider(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def _getAuthenticatedUser(self):
        return IPerson(self.request.principal, None)

    def _isLookingAtOwnCalendar(self, user):
        unproxied_context = removeSecurityProxy(self.context)
        unproxied_calendar = removeSecurityProxy(ISchoolToolCalendar(user))
        return unproxied_context is unproxied_calendar

    def getCalendars(self):
        user = self._getAuthenticatedUser()
        if not user:
            return

        if self._isLookingAtOwnCalendar(user):
            yield (ISectionAttendance(user).makeCalendar(), '#aa0000', '#ff0000')
            yield (IDayAttendance(user).makeCalendar(), '#00aa00', '#00ff00')
