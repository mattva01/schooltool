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
import logging

import pytz
from BTrees.OOBTree import OOBTree
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
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.security.management import queryInteraction


from schooltool import SchoolToolMessage as _
from schooltool.person.interfaces import IPerson
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


def date_to_schoolday_start(date):
    """Given a date, return the datetime of the beginning of the day.

    Takes the school's timezone into account.
    """
    app = ISchoolToolApplication(None)
    tzinfo = pytz.timezone(IApplicationPreferences(app).timezone)
    return tzinfo.localize(datetime.datetime.combine(date, datetime.time(0)))


def date_to_schoolday_end(date):
    """Given a date, return the datetime of the end of the day.

    Takes the school's timezone into account.
    """
    return date_to_schoolday_start(date) + datetime.timedelta(days=1)


def getRequestFromInteraction(request_type=IBrowserRequest):
    """Extract the browser request from the current interaction.

    Returns None when there is no interaction, or when the interaction has no
    participations that provide request_type.
    """
    interaction = queryInteraction()
    if interaction is not None:
        for participation in interaction.participations:
            if request_type.providedBy(participation):
                return participation
    return None


class AttendanceLoggingProxy(object):
    """Logging proxy for attendance records.

    Logs information about operations performed on attendance recrod
    into an attendance log file.
    """

    def __init__(self, attentdance_record, person):
        self.__dict__["attentdance_record"] = attentdance_record
        self.__dict__["person"] = person

    def _getLoggedInPerson(self):
        """Get the name of the principal.

        Returns None when there is no interaction or request.
        """
        # XXX ignas: what about restive views ?
        request = getRequestFromInteraction()

        if request:
            return IPerson(request.principal).__name__
        else:
            return None

    def _getLogger(self):
        return logging.getLogger("attendance")

    def log(self, action):
        logger = self._getLogger()
        logger.info("%s, %s, %s of %s: %s" % (datetime.datetime.utcnow(),
                                              self._getLoggedInPerson(),
                                              self.attentdance_record,
                                              self.person.__name__,
                                              action))

    def addExplanation(self, explanation):
        self.attentdance_record.addExplanation(explanation)
        self.log("added an explanation")

    def acceptExplanation(self):
        self.attentdance_record.acceptExplanation()
        self.log("accepted explanation")

    def rejectExplanation(self):
        self.attentdance_record.rejectExplanation()
        self.log("rejected explanation")

    def __repr__(self):
        return repr(self.attentdance_record)

    def __getattr__(self, name):
        return getattr(self.attentdance_record, name)

    def __setattr__(self, name, value):
        setattr(self.attentdance_record, name, value)


class DayAttendanceLoggingProxy(AttendanceLoggingProxy):
    implements(IDayAttendanceRecord)


class SectionAttendanceLoggingProxy(AttendanceLoggingProxy):
    implements(ISectionAttendanceRecord)

    def makeTardy(self, arrival_time):
        self.attentdance_record.makeTardy(arrival_time)
        self.log("tardified an absence, arrival time (%s)" % arrival_time)


#
# Attendance record classes
#

class AttendanceRecord(Persistent):
    """Base class for attendance records."""

    # These are class attributes to conserve ZODB space
    late_arrival = None
    explanations = ()

    def __init__(self, status):
        assert status in (UNKNOWN, PRESENT, ABSENT)
        self.status = status
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
        if not self.explanations or self.explanations[-1].isProcessed():
            raise AttendanceError("there are no outstanding explanations.")
        self._work_item.acceptExplanation()

    def rejectExplanation(self):
        if not self.explanations or self.explanations[-1].isProcessed():
            raise AttendanceError("there are no outstanding explanations.")
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
        if not self.explanations: # convert the tuple to a persistent list
            self.explanations = PersistentList()
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

    def __str__(self):
        return 'DayAttendanceRecord(%s, %s)' % (self.date, self.status)


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

    def __str__(self):
        return 'SectionAttendanceRecord(%s, %s, section=%s)' %(
            self.datetime,
            self.status,
            self.section.__name__)


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

    def __init__(self, person):
        self._records = PersistentDict()
        # When it is time to optimize, convert it to OOBTree
        self.person = person

    def _wrapRecordForLogging(self, ar):
        return DayAttendanceLoggingProxy(ar, self.person)

    def __iter__(self):
        for ar in self._records.values():
            yield self._wrapRecordForLogging(ar)

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
            return self._wrapRecordForLogging(self._records[date])
        except KeyError:
            return self._wrapRecordForLogging(DayAttendanceRecord(date, UNKNOWN))

    def record(self, date, present):
        assert type(date) == datetime.date
        if date in self._records:
            raise AttendanceError('record for %s already exists' % date)
        if present: status = PRESENT
        else: status = ABSENT
        ar = DayAttendanceRecord(date, status)
        self._records[date] = ar
        self._wrapRecordForLogging(ar).log("created")


class SectionAttendance(Persistent, AttendanceFilteringMixin,
                        AttendanceCalendarMixin):
    """Persistent object that stores section attendance records for a student.
    """

    implements(ISectionAttendance)

    def __init__(self, person):
        self.person = person
        self._records = OOBTree() # datetime -> list of AttendanceRecords

    def __iter__(self):
        for group in self._records.values():
            for record in group:
                yield self._wrapRecordForLogging(record)

    def _wrapRecordForLogging(self, ar):
        return SectionAttendanceLoggingProxy(ar, self.person)

    def filter(self, first, last):
        assert type(first) == datetime.date
        assert type(last) == datetime.date
        dt_min = date_to_schoolday_start(first)
        dt_max = date_to_schoolday_end(last)
        for group in self._records.values(min=dt_min, max=dt_max,
                                          excludemax=True):
            for record in group:
                yield self._wrapRecordForLogging(record)

    def getAllForDay(self, date):
        return self.filter(date, date)

    def get(self, section, datetime):
        for ar in self._records.get(datetime, ()):
            if ar.section == section:
                return self._wrapRecordForLogging(ar)
        ar = SectionAttendanceRecord(section, datetime, status=UNKNOWN)
        return self._wrapRecordForLogging(ar)

    def record(self, section, datetime, duration, period_id, present):
        if self.get(section, datetime).status != UNKNOWN:
            raise AttendanceError('record for %s at %s already exists'
                                  % (section, datetime))
        if present: status = PRESENT
        else: status = ABSENT
        # Optimization: attendance records with status PRESENT are never
        # changed, and look the same for all students.  If we reuse the
        # same persistent object for all section members, we conserve
        # a huge amount of memory and disk space.
        # XXX mg: go read http://www.zope.org/Wikis/ZODB/VolatileAttributes
        #     I am not sure it is safe to store a Persistent object in a
        #     _v_attr, as it might survive transaction boundaries.  If you
        #     happen to use it from a different transaction, will it work?
        if (status == PRESENT and
            getattr(section, "_v_SectionAttendance_cache",
                    (None, ))[0] == datetime):
            ar = section._v_SectionAttendance_cache[1]
        else:
            ar = SectionAttendanceRecord(section, datetime, status=status,
                                         duration=duration,
                                         period_id=period_id)
            if status == PRESENT:
                section._v_SectionAttendance_cache = (datetime, ar)
        if datetime not in self._records:
            self._records[datetime] = ()
        self._records[datetime] += (ar, )
        self._wrapRecordForLogging(ar).log("created")

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
        attendance = SectionAttendance(person)
        annotations[SECTION_ATTENDANCE_KEY] = attendance
    return attendance


def getDayAttendance(person):
    """Return the section attendance record for a person."""
    annotations = IAnnotations(person)
    try:
        attendance = annotations[DAY_ATTENDANCE_KEY]
    except KeyError:
        attendance = DayAttendance(person)
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
