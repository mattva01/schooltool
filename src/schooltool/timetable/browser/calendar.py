#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Timetabling calendar integration.
"""
from datetime import datetime, time, timedelta
import urllib

import zope.schema
from zope.app.form.browser.add import AddView
from zope.interface import Interface, implements, implementer
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import CachedProperty
from zope.component import adapter, getUtility
from zope.formlib import form
from zope.html.field import HtmlFragment
from zope.session.interfaces import ISession
from zope.proxy import sameProxiedObjects
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.viewlet.interfaces import IViewlet

from schooltool.app.browser import ViewPreferences
from schooltool.app.browser.interfaces import IEventForDisplay
from schooltool.app.browser.cal import CalendarEventView
from schooltool.app.browser.cal import CalendarEventViewMixin
from schooltool.app.browser.cal import YearlyCalendarView
from schooltool.app.browser.cal import DailyCalendarRowsView
from schooltool.app.browser.cal import getCalendarEventDeleteLink
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.membership import URIMembership, URIGroup
from schooltool.app.utils import vocabulary
from schooltool.app.relationships import URISection, URIInstruction
from schooltool.calendar.browser.event import FlourishCalendarEventAddView
from schooltool.person.interfaces import IPerson
from schooltool.relationship import getRelatedObjects
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin import flourish
from schooltool.timetable import interfaces
from schooltool.timetable.calendar import ScheduleCalendarEvent
from schooltool.timetable.schedule import iterMeetingsInTimezone
from schooltool.timetable.interfaces import IHaveSchedule
from schooltool.term.interfaces import IDateManager, ITermContainer
from schooltool.term.term import getTermForDate

from schooltool.common import SchoolToolMessage as _


scheduleCalendarFieldNames = (
    "title", "description", "start_date", "start_time",
    "duration", "duration_type", "allday", "location",
    )


class ScheduleEventEditView(CalendarEventView, form.Form):

    title = _("Modify meeting information")

    form_fields = form.fields(HtmlFragment(
            __name__='description',
            title=_("Description"),
            required=False))

    template = ViewPageTemplateFile("templates/schedule_event_edit.pt")

    def setUpWidgets(self, ignore_request=False):
        self.widgets = form.setUpEditWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            ignore_request=ignore_request)

    def __init__(self, context, request):
        form.Form.__init__(self, context, request)
        CalendarEventView.__init__(self, context, request)

    def redirect_to_parent(self):
        url = absoluteURL(self.context.__parent__, self.request)
        self.request.response.redirect(url)
        return ''

    @form.action(_("Apply"))
    def handle_edit_action(self, action, data):
        self.context.description = data['description']
        return self.redirect_to_parent()

    @form.action(_("Cancel"), condition=form.haveInputWidgets)
    def handle_cancel_action(self, action, data):
        return self.redirect_to_parent()


class FlourishScheduleEventEditView(flourish.page.Page,
                                    ScheduleEventEditView):
    __init__ = ScheduleEventEditView.__init__
    update = ScheduleEventEditView.update

    legend = _("Meeting Details")

    def nextURL(self):
        return (self.request.get('back_url') or
                absoluteURL(self.context, self.request))


class IScheduleEventAddForm(Interface):
    """Schema for schedule calendar event adding form."""

    title = zope.schema.TextLine(
        title=_("Title"),
        required=False)
    allday = zope.schema.Bool(
        title=_("All day"),
        required=False)
    start_date = zope.schema.Date(
        title=_("Date"),
        required=False)
    start_time = zope.schema.TextLine(
        title=_("Time"),
        description=_("Start time in 24h format"),
        required=False)

    duration = zope.schema.Int(
        title=_("Duration"),
        required=False,
        default=60)

    duration_type = zope.schema.Choice(
        title=_("Duration Type"),
        required=False,
        default="minutes",
        vocabulary=vocabulary([("minutes", _("Minutes")),
                               ("hours", _("Hours")),
                               ("days", _("Days"))]))

    location = zope.schema.TextLine(
        title=_("Location"),
        required=False)

    description = HtmlFragment(
        title=_("Description"),
        required=False)


class ScheduleEventAddView(CalendarEventViewMixin, AddView):
    """A view for adding an event."""

    schema = IScheduleEventAddForm

    title = _("Add meeting")
    submit_button_title = _("Add")

    show_book_checkbox = True
    show_book_link = False
    _event_uid = None

    error = None

    def __init__(self, context, request):

        prefs = ViewPreferences(request)
        self.timezone = prefs.timezone

        if "field.start_date" not in request:
            # XXX: shouldn't use date.today; it depends on the server's timezone
            # which may not match user expectations
            today = getUtility(IDateManager).today.strftime("%Y-%m-%d")
            request.form["field.start_date"] = today
        super(AddView, self).__init__(context, request)

    def create(self, **kwargs):
        """Create an event."""
        data = self.processRequest(kwargs)
        event = self._factory(data['start'], data['duration'], data['title'],
                              location=data['location'],
                              allday=data['allday'],
                              description=data['description'])
        # XXX: also meeting id! Don't forget the meeting id.
        return event

    def add(self, event):
        self.context.addEvent(event)
        uid = event.unique_id
        self._event_name = event.__name__
        session_data = ISession(self.request)['schooltool.calendar']
        session_data.setdefault('added_event_uids', set()).add(uid)
        return event

    def update(self):
        if 'UPDATE' in self.request:
            return self.updateForm()
        elif 'CANCEL' in self.request:
            self.update_status = ''
            self.request.response.redirect(self.nextURL())
            return self.update_status
        else:
            return AddView.update(self)

    def nextURL(self):
        if "field.book" in self.request:
            url = absoluteURL(self.context, self.request)
            return '%s/%s/booking.html' % (url, self._event_name)
        else:
            return absoluteURL(self.context, self.request)


class FlourishScheduleEventAddView(FlourishCalendarEventAddView):

    fieldNames = scheduleCalendarFieldNames
    schema = IScheduleEventAddForm

    _keyword_arguments = scheduleCalendarFieldNames
    _factory = ScheduleCalendarEvent

    def create(self, **kwargs):
        data = self.processRequest(kwargs)
        event = self._factory(data['start'], data['duration'], data['title'],
                              location=data['location'],
                              allday=data['allday'],
                              description=data['description'])
        # XXX: also meeting id! Don't forget the meeting id.
        return event

    def setUpCustomWidgets(self):
        self.setCustomWidget('description', height=5)

    def update(self):
        if ("field.title" not in self.request):
            calendar = ISchoolToolCalendar(self.context)
            owner = IHaveSchedule(calendar.__parent__)
            self.request.form["field.title"] = owner.title
        super(FlourishScheduleEventAddView, self).update()


class TermLegendViewlet(object):
    implements(IViewlet)

    def legend(self):
        terms = self.__parent__.legend.items()
        terms.sort(key=lambda t: t[0].first)
        return [{'title': term.title,
                 'cssclass': "legend-item term%s" % cssClass}
                for term, cssClass in terms]


class ScheduleYearlyCalendarView(YearlyCalendarView):

    def __init__(self, context, request):
        super(YearlyCalendarView, self).__init__(context,request)
        self.numterms = 1
        self.calendar = None

    @CachedProperty
    def legend(self):
        numterms = 1
        legend = {}
        terms = ITermContainer(self.cursor, {})
        for quarter in self.getYear(self.cursor):
            for month in quarter:
                for week in month:
                    for day in week:
                        term = None
                        for term in terms.values():
                            if day.date in term:
                                break
                        if term and not term in legend:
                            legend[term] = self.numterms
                            numterms += 1
        return legend

    def renderRow(self, week, month):
        result = []

        terms = ITermContainer(self.cursor, {})

        for day in week:
            term = None
            for term in terms.values():
                if day.date in term:
                    break
            cssClass = "term%d" % self.legend.get(term, 0)
            result.append('<td class="cal_yearly_day">')
            if day.date.month == month:
                if day.today():
                    cssClass += ' today'
                # Let us hope that URLs will not contain < > & or "
                # This is somewhat related to
                # https://bugs.launchpad.net/schooltool/+bug/79781
                result.append('<a href="%s" class="%s">%s</a>' %
                              (self.calURL('daily', day.date), cssClass,
                               day.date.day))
            result.append('</td>')

        return "\n".join(result)


class ScheduleDailyCalendarRowsView(DailyCalendarRowsView):
    """Daily calendar rows view for SchoolTool.

    This view differs from the original view in SchoolTool in that it can
    also show schedule periods instead of hour numbers.
    """

    def getDefaultMeetings(self, date, timezone):
        term = getTermForDate(date)
        if term is None:
            return []
        schoolyear = ISchoolYear(term)
        timetable_container = interfaces.ITimetableContainer(schoolyear)
        default_schedule = timetable_container.default
        if default_schedule is None:
            return []
        meetings = list(iterMeetingsInTimezone(
                default_schedule, timezone, date))
        return meetings

    def meetingTitle(self, meeting):
        if (meeting.period is None or
            not meeting.period.title):
            return self.rowTitle(meeting.dtstart.time(), meeting.duration)
        return meeting.period.title

    def calendarRows(self, cursor, starthour, endhour, events):
        tz = self.getPersonTimezone()
        meetings = self.getDefaultMeetings(cursor, tz.zone)
        meeting_rows = [
            (self.meetingTitle(meeting), meeting.dtstart, meeting.duration)
            for meeting in meetings]

        daystart = tz.localize(datetime.combine(cursor, time()))

        rows = []

        row_start = tz.localize(datetime.combine(cursor, time()) +
                                timedelta(hours=starthour))
        row_start = tz.normalize(row_start)

        rows_end = tz.localize(datetime.combine(cursor, time()) +
                               timedelta(hours=endhour))
        rows_end = tz.normalize(rows_end + timedelta(hours=1))

        if meeting_rows:
            row_start = min(row_start, meeting_rows[0][1].astimezone(tz))
            meet_end = meeting_rows[-1][1] + meeting_rows[-1][2]
            rows_end = max(rows_end, meet_end.astimezone(tz))

        while row_start < rows_end:
            row = None
            if meeting_rows:
                time_until_meeting = meeting_rows[0][1] - row_start
                if time_until_meeting < time.resolution:
                    meeting = meeting_rows.pop(0)
                    row = meeting
                elif time_until_meeting < timedelta(hours=1, minutes=15):
                    row = (self.rowTitle(row_start.time(), time_until_meeting),
                           row_start, time_until_meeting)

            if row is None:
                hstart = tz.normalize(row_start + timedelta(hours=1))
                hstart = hstart.replace(minute=0, second=0, microsecond=0)
                delta = hstart - row_start
                if delta < timedelta(minutes=15):
                    delta += timedelta(hours=1)
                row = (self.rowTitle(row_start.time(), delta), row_start, delta)

            if row[1].astimezone(tz).date() == daystart.date():
                rows.append(row)
            row_start = tz.normalize(row_start + row[2])
        return rows


@adapter(IEventForDisplay, IBrowserRequest, interfaces.IScheduleCalendar)
@implementer(Interface)
def getScheduleCalendarEventDeleteLink(event, request, calendar):
    schedule = event.context.schedule
    if schedule is not None:
        return None
    return getCalendarEventDeleteLink(event, request, calendar)


class TimetableCalendarListSubscriber(object):
    """A subscriber that can tell which calendars should be displayed."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getCalendars(self):
        """Get a list of calendars to display.

        Yields tuples (calendar, color1, color2).
        """

        owner = self.context.__parent__

        user = IPerson(self.request.principal, None)
        if (user is not None and
            sameProxiedObjects(user, owner)):
            return

        instructs = list(getRelatedObjects(
                owner, URISection, rel_type=URIInstruction))
        member_of = list(getRelatedObjects(
                owner, URIGroup, rel_type=URIMembership))

        for obj in instructs + member_of:
            if IHaveSchedule.providedBy(obj):
                cal = ISchoolToolCalendar(obj, None)
                if cal is not None:
                    yield(ISchoolToolCalendar(obj), '#9db8d2', '#7590ae')
