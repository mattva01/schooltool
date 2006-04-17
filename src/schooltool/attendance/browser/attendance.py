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
import itertools
import pytz

from zope.app import zapi
from zope.app.publisher.browser import BrowserView
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.component import adapts
from zope.viewlet import viewlet
from zope.schema import Choice
from zope.app.form.browser.itemswidgets import DropdownWidget
from zope.schema.vocabulary import SimpleVocabulary
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
from zope.i18n import translate

from schooltool.batching.batch import Batch
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable.interfaces import ITimetableCalendarEvent
from schooltool.calendar.utils import parse_date, parse_time
from schooltool.course.interfaces import ISection
from schooltool.app.browser import ViewPreferences
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.attendance.interfaces import IUnresolvedAbsenceCache
from schooltool.person.interfaces import IPerson
from schooltool.group.interfaces import IGroup
from schooltool.calendar.utils import utcnow
from schooltool.attendance.interfaces import IHomeroomAttendance
from schooltool.attendance.interfaces import IHomeroomAttendanceRecord
from schooltool.attendance.interfaces import ISectionAttendance
from schooltool.attendance.interfaces import ISectionAttendanceRecord
from schooltool.attendance.interfaces import ABSENT, TARDY, PRESENT, UNKNOWN
from schooltool.attendance.interfaces import AttendanceError
from schooltool import SchoolToolMessage as _


AttendanceCSSViewlet = viewlet.CSSViewlet("attendance.css")


def datetime_to_schoolday_date(datetime):
    """Given a datetime, return the date of the schoolday.

    Takes the school's timezone into account.
    """
    app = ISchoolToolApplication(None)
    tzinfo = pytz.timezone(IApplicationPreferences(app).timezone)
    return datetime.astimezone(tzinfo).date()


def getCurrentSectionMeeting(section, datetime):
    """Find the closest section meeting event, if it exists on a given day.

    Returns the event of the section meeting if there is one on a given day,
    and None otherwise.
    """
    date = datetime_to_schoolday_date(datetime)
    closest_meeting = None
    last_meeting = None
    events = ITimetables(section).makeTimetableCalendar(date, date)
    for ev in reversed(sorted(events, key=lambda e: e.dtstart)):
        if datetime < ev.dtstart + ev.duration:
            closest_meeting = ev
        if last_meeting is None:
            last_meeting = ev
    return closest_meeting or last_meeting


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

    def __init__(self, name, title, color, symbol, disabled, sparkline_url,
                 arrival_time):
        self.name = name
        self.title = title
        self.color = color
        self.symbol = symbol
        self.disabled = disabled
        self.sparkline_url = sparkline_url
        self.arrival_time = arrival_time

    def __repr__(self):
        return 'RealtimeInfo(%r, %r, %r, %r, %r, %r)' % \
               (self.name, self.title, self.color, self.symbol, self.disabled,
                self.sparkline_url)


class AttendanceView(BrowserView):
    """Attendance view for a section

    Shows a realtime or a retrospective attendance form depending on
    when the view is accessed.
    """

    __used_for__ = ISection

    realtime_template = ViewPageTemplateFile("templates/real_time.pt")
    retro_template = ViewPageTemplateFile("templates/retro.pt")
    no_section_meeting_today_template = ViewPageTemplateFile(
                                            "templates/no_section_meeting.pt")

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
        for person in self.iterTransitiveMembers():
            past_status = self.studentStatus(person)
            ar = self._getAttendanceRecord(ISectionAttendance(person))
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
                sparkline_url,
                ar.late_arrival
                ))

        result.sort(key=lambda this: this.title)
        return result

    def getDaysAttendanceRecords(self, student, date):
        """Return all attendance records for a student and a given date."""
        section_ars = list(ISectionAttendance(student).getAllForDay(date))
        homeroom_ars = list(IHomeroomAttendance(student).getAllForDay(date))
        return section_ars + homeroom_ars

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
        # If there are persons with UNKNOWN status, show the 'absent' button,
        # otherwise show 'tardy' and 'arrived'.
        self.unknowns = False

        for person in self.iterTransitiveMembers():
            check_id = "%s_check" % person.__name__
            selected = check_id in self.request

            attendance = ISectionAttendance(person)
            self.updateAttendance(attendance, selected)

            if self.homeroom:
                hr_attendance = IHomeroomAttendance(person)
                self.updateAttendance(hr_attendance, selected)

    def updateAttendance(self, attendance, selected):
        ar = self._getAttendanceRecord(attendance)
        if 'ABSENT' in self.request:
            if ar.isUnknown():
                present = not selected
                self._record(attendance, present)
        elif 'TARDY' in self.request:
            try:
                arrived = self.getArrival()
            except ValueError:
                self.error = _('The arrival time you entered is '
                               'invalid.  Please use HH:MM format')
                return
            if selected and ar.isAbsent():
                ar.makeTardy(arrived)

        ar = self._getAttendanceRecord(attendance)
        if ar.isUnknown():
            self.unknowns = True

    def retro_update(self):
        """Process submissions for the retroactive form"""
        self.arrival_errors = {}
        self.arrivals = {}
        if 'SUBMIT' in self.request:
            for person in self.iterTransitiveMembers():
                name = person.__name__
                arrival_string = self.request.get(name + '_tardy', '').strip()
                if self.request.get(name) == 'T':
                    if not arrival_string:
                        self.arrival_errors[name] = _(
                            'You need to provide the arrival time')
                        continue
                    try:
                        self.arrivals[name] = self.getArrival(name + '_tardy')
                    except ValueError:
                        self.arrival_errors[name] = _(
                            'The arrival time you entered is '
                            'invalid.  Please use HH:MM format')
                elif arrival_string:
                    self.arrival_errors[name] = _(
                        'Arrival times only apply to tardy students')
            if self.arrival_errors:
                return
            for person in self.iterTransitiveMembers():
                attendance = ISectionAttendance(person)
                self._retroUpdatePerson(attendance, person)
                if self.homeroom:
                    hattendance = IHomeroomAttendance(person)
                    self._retroUpdatePerson(hattendance, person)

    def _retroUpdatePerson(self, attendance, person):
        name = person.__name__
        action = self.request.get(name, 'U')
        if action == 'P':
            self._record(attendance, True)
        elif action == 'A':
            self._record(attendance, False)
        elif action == 'T':
            self._record(attendance, False)
            ar = self._getAttendanceRecord(attendance)
            ar.makeTardy(self.arrivals[name])

    def _getAttendanceRecord(self, attendance):
        """Get a attendance record for this section meeting."""
        return attendance.get(self.context, self.meeting.dtstart)

    def _record(self, attendance, present):
        """Record a student's presence or absence."""
        attendance.record(removeSecurityProxy(self.context),
                          self.meeting.dtstart, self.meeting.duration,
                          self.period_id, present)

    def getArrival(self, field='arrival'):
        """Extracts the date of late arrivals from the request.

        If the time is not specified, defaults to now.
        """
        if self.request.get(field):
            tz = ViewPreferences(self.request).timezone
            time = parse_time(self.request[field])
            result = datetime.datetime.combine(self.date, time)
            return tz.localize(result)
        return pytz.utc.localize(datetime.datetime.utcnow())

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
        if self.date is None and self.period_id is None:
            self.findClosestMeeting()
        if self.date is None or self.period_id is None:
            # Not enough traversal path elements
            raise NotFound(self.context, self.__name__, self.request)
        self.meeting = getPeriodEventForSection(self.context, self.date,
                                               self.period_id)
        if not self.meeting:
            raise NotFound(self.context, self.__name__, self.request)
        timetable = self.meeting.activity.timetable
        homeroom_ids = timetable[self.meeting.day_id].homeroom_period_ids
        self.homeroom = (self.meeting.period_id in homeroom_ids)


    def findClosestMeeting(self):
        """Find the closest section meeting."""
        if 'date' in self.request.form and 'period_id' in self.request.form:
            self.date = parse_date(self.request['date'])
            self.period_id = self.request['period_id']
            return
        now = pytz.utc.localize(datetime.datetime.utcnow())
        ev = getCurrentSectionMeeting(self.context, now)
        if not ev:
            raise NoSectionMeetingToday
        self.date = datetime_to_schoolday_date(now)
        self.period_id = ev.period_id

    def sectionMeetingFinished(self):
        app = ISchoolToolApplication(None)
        mins = IApplicationPreferences(app).attendanceRetroactiveTimeout
        delta = datetime.timedelta(minutes=mins)
        if self.meeting.dtstart + self.meeting.duration + delta < utcnow():
            return True
        return False

    def __call__(self):
        """Process form submissions and render the view."""
        try:
            self.verifyParameters()
        except NoSectionMeetingToday:
            return self.no_section_meeting_today_template()

        if self.sectionMeetingFinished():
            self.retro_update()
            return self.retro_template()
        else:
            self.update()
            return self.realtime_template()


class NoSectionMeetingToday(Exception):
    """There are no section meetings today."""


class StudentAttendanceView(BrowserView):
    """Attendance view for a student.

    Lists pending unexcused attendance incidents, and a summary of absences and
    tardies by term.
    """

    adapts(IPerson, IBrowserRequest)

    template = ViewPageTemplateFile('templates/student-attendance.pt')

    def __call__(self):
        """Process the form and render the view."""
        self.update()
        return self.template()

    def update(self):
        """Process the form."""
        self.statuses = []
        self.errors = []

        # hand craft dropdown widget from dict
        app = ISchoolToolApplication(None)
        code_dict = IApplicationPreferences(app).attendanceStatusCodes
        code_items = sorted((i[1], i[0]) for i in code_dict.items())
        code_vocabulary = SimpleVocabulary.fromItems(code_items)
        self.code = ''
        code_field = Choice(__name__='code', title=u'Set status:',
                            required=False,
                            vocabulary=code_vocabulary).bind(self)
        self.code_widget = DropdownWidget(code_field, code_vocabulary, self.request)

        if 'UPDATE' not in self.request:
            return
        code = ''
        if self.code_widget.hasInput():
            code = self.code_widget.getInputValue()
        explanation = self.request.get('explanation', '').strip()
        resolve = self.request.get('resolve', '')
        for ar in self.unresolvedAbsences():
            if ar['id'] in self.request.form:
                self._process(ar['attendance_record'], translate(ar['text']),
                              explanation, resolve, code)

    def _process(self, ar, text, explanation, resolve, code):
        """Process a single attendance record"""
        # We want only one status message per attendance record, so if we
        # both add an explanation and accept/reject it in one go, only the
        # acceptance/rejection status message will be shown.
        status = None
        mapping = mapping={'absence': text}
        if explanation:
            if self._addExplanation(ar, explanation, mapping):
                status = _('Added an explanation for $absence',
                           mapping=mapping)
            else:
                # If we couldn't add an explanation, let's not accept/reject
                # some other explanation that just happened to be there.
                return
        if resolve == 'accept':
            if self._acceptExplanation(ar, code, mapping):
                status = _('Resolved $absence', mapping=mapping)
        elif resolve == 'reject':
            if self._rejectExplanation(ar, mapping):
                status = _('Rejected explanation for $absence',
                           mapping=mapping)
        if status:
            self.statuses.append(status)

    def _addExplanation(self, ar, explanation, mapping):
        """Add an explanation, reporting errors gracefully."""
        try:
            ar.addExplanation(explanation)
            return True
        except AttendanceError:
            self.errors.append(_('Cannot add new explanation for'
                                 ' $absence: old explanation not'
                                 ' accepted/rejected', mapping=mapping))
            return False

    def _acceptExplanation(self, ar, code, mapping):
        """Accept an explanation, reporting errors gracefully."""
        try:
            ar.acceptExplanation(code)
            return True
        except AttendanceError:
            self.errors.append(_('There are no outstanding'
                                 ' explanations to accept for'
                                 ' $absence', mapping=mapping))
            return False

    def _rejectExplanation(self, ar, mapping):
        """Reject an explanation, reporting errors gracefully."""
        try:
            ar.rejectExplanation()
            return True
        except AttendanceError:
            self.errors.append(_('There are no outstanding'
                                 ' explanations to reject for'
                                 ' $absence', mapping=mapping))
            return False

    @property
    def term_for_detailed_summary(self):
        """Return the term for a detailed list of absences."""
        app = ISchoolToolApplication(None)
        term_name = self.request.get('term', None)
        return app['terms'].get(term_name, None)

    def terms(self):
        """List all terms in chronological order."""
        app = ISchoolToolApplication(None)
        terms = sorted(app['terms'].values(), key=lambda t: t.first)
        return terms

    def makeId(self, ar):
        """Create an ID to identify an attendance record."""
        if IHomeroomAttendanceRecord.providedBy(ar):
            prefix = "h"
            name = "homeroom"
        else:
            assert ISectionAttendanceRecord.providedBy(ar)
            prefix = "s"
            name = ar.section.__name__.encode('UTF-8').encode('base64')
            name = name.rstrip() # chomp off the trailing newline
        return "%s_%s_%s" % (prefix, ar.datetime.isoformat('_'), name)

    def formatAttendanceRecord(self, ar):
        """Format an attendance record for display."""
        assert ar.isAbsent() or ar.isTardy()
        if IHomeroomAttendanceRecord.providedBy(ar):
            title = translate(_('homeroom'))
        else:
            assert ISectionAttendanceRecord.providedBy(ar)
            title = translate(ar.section.label)

        mapping = {'date': ar.date,
                   'time': ar.datetime.strftime('%H:%M'),
                   'section': title}

        if ar.isAbsent():
            return _('$date $time: absent from $section', mapping=mapping)
        else:
            return _('$date $time: late for $section', mapping=mapping)

    def outstandingExplanation(self, ar):
        """Return the outstanding unaccepted explanation, if any."""
        if ar.explanations and not ar.explanations[-1].isProcessed():
            return ar.explanations[-1].text
        else:
            return None

    def interleaveAttendanceRecords(self, homeroom_attendances,
                                    section_attendances):
        """Interleave day and section attendance records."""
        homeroom_iter = itertools.chain(homeroom_attendances, [None])
        section_iter = itertools.chain(section_attendances, [None])
        cur_homeroom = homeroom_iter.next()
        cur_section = section_iter.next()
        while cur_homeroom is not None and cur_section is not None:
            if cur_homeroom.datetime <= cur_section.datetime:
                yield cur_homeroom
                cur_homeroom = homeroom_iter.next()
            else:
                yield cur_section
                cur_section = section_iter.next()
        if cur_homeroom is not None:
            yield cur_homeroom
            for cur_homeroom in homeroom_iter:
                if cur_homeroom is not None:
                    yield cur_homeroom
        if cur_section is not None:
            yield cur_section
            for cur_section in section_iter:
                if cur_section is not None:
                    yield cur_section

    def unresolvedAbsences(self):
        """Return all unresolved absences and tardies."""
        homeroom_attendance = IHomeroomAttendance(self.context)
        section_attendance = ISectionAttendance(self.context)
        l = []
        for ar in self.interleaveAttendanceRecords(homeroom_attendance,
                                                   section_attendance):
            if (ar.isAbsent() or ar.isTardy()) and not ar.isExplained():
                l.append({'id': self.makeId(ar),
                          'text': self.formatAttendanceRecord(ar),
                          'attendance_record': ar,
                          'explanation': self.outstandingExplanation(ar)})
        return l

    def absencesForTerm(self, term):
        """Return all absences and tardies in a term."""
        homeroom_attendance = IHomeroomAttendance(self.context)
        section_attendance = ISectionAttendance(self.context)
        for ar in self.interleaveAttendanceRecords(
                            homeroom_attendance.filter(term.first, term.last),
                            section_attendance.filter(term.first, term.last)):
            if ar.isAbsent() or ar.isTardy():
                yield self.formatAttendanceRecord(ar)

    def summaryPerTerm(self):
        """List a summary of absences and tardies for each term."""
        homeroom_attendance = IHomeroomAttendance(self.context)
        section_attendance = ISectionAttendance(self.context)
        for term in self.terms():
            n_homeroom_absences, n_homeroom_tardies = self.countAbsences(
                    homeroom_attendance.filter(term.first, term.last))
            n_section_absences, n_section_tardies = self.countAbsences(
                    section_attendance.filter(term.first, term.last))
            yield {'name': term.__name__,
                   'title': term.title,
                   'first': term.first,
                   'last': term.last,
                   'homeroom_absences': n_homeroom_absences,
                   'homeroom_tardies': n_homeroom_tardies,
                   'section_absences': n_section_absences,
                   'section_tardies': n_section_tardies}

    def countAbsences(self, attendance_records):
        """Count absences and tardies."""
        n_absences = n_tardies = 0
        for ar in attendance_records:
            if ar.isAbsent():
                n_absences += 1
            elif ar.isTardy():
                n_tardies += 1
        return n_absences, n_tardies


class AttendancePanelView(BrowserView):
    """A control panel for tracking global attendance."""

    __used_for__ = ISchoolToolApplication

    def getItems(self, search_str):
        cache = IUnresolvedAbsenceCache(self.context)
        subjects = [(self.context['persons'][username], absences)
                    for username, absences in iter(cache)]
        # TODO: It would be more efficient to only calculate stats for
        # the given person.
        return [{'title': person.title,
                 'person': person,
                 'hr_absences':
                    len(filter(IHomeroomAttendanceRecord.providedBy, absences)),
                 'section_absences':
                    len(filter(ISectionAttendanceRecord.providedBy, absences))
                 }
                for person, absences in subjects
                if search_str.lower() in person.title.lower()]

    def update(self):
        if 'CLEAR_SEARCH' in self.request:
            self.request.form['SEARCH'] = ''
        search_str = self.request.get('SEARCH', '')
        results = self.getItems(search_str)
        start = int(self.request.get('batch_start', 0))
        size = int(self.request.get('batch_size', 10))
        self.batch = Batch(results, start, size, sort_by='title')
