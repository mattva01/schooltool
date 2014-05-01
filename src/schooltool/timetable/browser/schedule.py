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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool timetabling views.
"""
import datetime
import urllib
import pytz
from persistent.list import PersistentList

import zope.schema
import zope.event
import zope.lifecycleevent
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility, queryMultiAdapter
from zope.intid.interfaces import IIntIds
from zope.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.absoluteurl import absoluteURL
from z3c.form import form, button

import schooltool.skin.flourish.breadcrumbs
import schooltool.skin.flourish.interfaces
import schooltool.skin.flourish.form
import schooltool.skin.flourish.page
from schooltool.calendar.utils import parse_date, parse_time
from schooltool.common.inlinept import InheritTemplate
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin import flourish
from schooltool.term.interfaces import ITerm
from schooltool.term.term import getTermForDate
from schooltool.timetable.schedule import MeetingException
from schooltool.timetable.interfaces import IHaveSchedule

from schooltool.common import SchoolToolMessage as _


class SpecialDayView(BrowserView):
    """The view for changing the periods for a particular day.

    The typical use case: some periods get shortened or and some get
    cancelled altogether if some special event is held at noon.
    """

    select_template = ViewPageTemplateFile('templates/specialday_select.pt')
    form_template = ViewPageTemplateFile('templates/specialday_change.pt')

    error = None
    field_errors = None
    field_error_message = _('Some values were invalid.'
                            '  They are highlighted in red.')
    date = None
    term = None

    def delta(self, start, end):
        """
        Returns a timedelta between two times

            >>> from datetime import time, timedelta
            >>> view = SpecialDayView(None, None)
            >>> view.delta(time(11, 10), time(12, 20))
            datetime.timedelta(0, 4200)

        If a result is negative, it is 'wrapped around':

            >>> view.delta(time(11, 10), time(10, 10)) == timedelta(hours=23)
            True
        """
        today = datetime.date.today()
        dtstart = datetime.datetime.combine(today, start)
        dtend = datetime.datetime.combine(today, end)
        delta = dtend - dtstart
        if delta < datetime.timedelta(0):
            delta += datetime.timedelta(1)
        return delta

    @property
    def schedule(self):
        return self.context

    def meeting_form_key(self, meeting):
        mid = meeting.meeting_id or ''
        mid = unicode(meeting.meeting_id).encode('punycode')
        mid = urllib.quote(mid)
        time = '%s:%s' % (meeting.dtstart.hour, meeting.dtstart.minute)
        time_key = '%s.%s.%s' % (time, meeting.duration, mid)
        period = meeting.period
        if period is None:
            return time_key
        int_ids = getUtility(IIntIds)
        return '%s.%s' % (int_ids.getId(period), mid)

    def getMeetings(self):
        meeting_info = {}
        for meeting in self.schedule.iterMeetings(self.date):
            meeting = removeSecurityProxy(meeting)
            start_time = meeting.dtstart.time()
            end_time = self.timeplustd(start_time, meeting.duration)
            form_key = self.meeting_form_key(meeting)
            meeting_info[form_key] = {
                'form_key': form_key,
                'meeting': meeting,
                'orig_start_time': '',
                'orig_end_time': '',
                'start_time': self.request.get('%s_start' % form_key,
                                               start_time.strftime("%H:%M")),
                'end_time': self.request.get('%s_end' % form_key,
                                             end_time.strftime("%H:%M")),
                }

        for meeting in self.schedule.iterOriginalMeetings(self.date):
            meeting = removeSecurityProxy(meeting)
            form_key = self.meeting_form_key(meeting)
            start_time = meeting.dtstart.time()
            end_time = self.timeplustd(start_time, meeting.duration)
            if form_key in meeting_info:
                info = meeting_info[form_key]
                info['orig_start_time'] = start_time.strftime("%H:%M")
                info['orig_end_time'] = end_time.strftime("%H:%M")
            else:
                meeting_info[form_key] = {
                    'form_key': form_key,
                    'meeting': meeting,
                    'orig_start_time': start_time.strftime("%H:%M"),
                    'orig_end_time': end_time.strftime("%H:%M"),
                    'start_time': self.request.get('%s_start' % form_key, ''),
                    'end_time': self.request.get('%s_end' % form_key, ''),
                }

        return sorted(meeting_info.values(),
                      key=lambda i: i['meeting'].dtstart)

    def extractMeeting(self, form_key):
        start_name = '%s_start' % form_key
        end_name = '%s_end' % form_key
        if (start_name in self.request and end_name in self.request
            and (self.request[start_name] or self.request[end_name])):
            start = end = None
            try:
                start = parse_time(self.request[start_name])
            except ValueError:
                pass
            try:
                end = parse_time(self.request[end_name])
            except ValueError:
                pass
            if start is None:
                self.field_errors.append(start_name)
            if end is None:
                self.field_errors.append(end_name)
            elif start is not None:
                duration = self.delta(start, end)
                return (start, duration)
        return None

    def extractMeetings(self):
        replacements = {}
        for meeting in self.schedule.iterOriginalMeetings(self.date):
            meeting = removeSecurityProxy(meeting)
            form_key = self.meeting_form_key(meeting)
            timespan = self.extractMeeting(form_key)
            if timespan is not None:
                replacements[form_key] = (meeting, ) + timespan

        for meeting in self.schedule.iterMeetings(self.date):
            meeting = removeSecurityProxy(meeting)
            form_key = self.meeting_form_key(meeting)
            timespan = self.extractMeeting(form_key)
            if timespan is not None:
                replacements[form_key] = (meeting, ) + timespan

        return replacements.values()

    def updateExceptions(self, replacements):
        template = PersistentList()
        tz = pytz.timezone(self.schedule.timezone)
        for meeting, start, duration in sorted(replacements,
                                               key=lambda r: r[1]):
            dtstart = datetime.datetime.combine(self.date, start)
            dtstart = dtstart.replace(tzinfo=tz)
            template.append(MeetingException(
                dtstart, duration,
                period=meeting.period,
                meeting_id=meeting.meeting_id))
        # XXX: broken permissions with PersistentDict
        exceptions = removeSecurityProxy(self.schedule.exceptions)
        exceptions[self.date] = template
        zope.lifecycleevent.modified(self.schedule)

    def update(self):
        """Read and validate form data, and update model if necessary.

        Also choose the correct template to render.
        """
        self.field_errors = []
        self.template = self.select_template

        if 'CANCEL' in self.request:
            self.request.response.redirect(
                absoluteURL(self.context, self.request))
            return

        if 'date' in self.request:
            try:
                self.date = parse_date(self.request['date'])
            except ValueError:
                self.error = _("Invalid date. Please use YYYY-MM-DD format.")
            else:
                self.term = getTermForDate(self.date)
                if self.term is None:
                    self.error = _("The date does not belong to any term.")
                    self.date = None

        if self.date:
            self.template = self.form_template

        if self.date and 'SUBMIT' in self.request:
            replacements = self.extractMeetings()
            if self.field_errors:
                self.error = self.field_error_message
            else:
                self.updateExceptions(replacements)
                self.request.response.redirect(
                    absoluteURL(self.context, self.request))

    def timeplustd(self, t, td):
        """Add a timedelta to time.

        datetime authors are cowards.

            >>> view = SpecialDayView(None, None)
            >>> from datetime import time, timedelta
            >>> view.timeplustd(time(10,0), timedelta(0, 5))
            datetime.time(10, 0, 5)
            >>> view.timeplustd(time(23,0), timedelta(0, 3660))
            datetime.time(0, 1)
        """
        dt = datetime.datetime.combine(datetime.date.today(), t)
        dt += td
        return dt.time()


    def __call__(self):
        self.update()
        return self.template()


class FlourishSpecialDayView(flourish.page.Page, SpecialDayView):
    select_template = ViewPageTemplateFile('templates/f_specialday_select.pt')
    form_template = ViewPageTemplateFile('templates/f_specialday_change.pt')
    flourish_template = InheritTemplate(flourish.page.Page.template)

    field_error_message = _('Please correct the marked fields below.')

    def update(self):
        SpecialDayView.update(self)
        self.content_template = self.template
        self.template = self.flourish_template


class ScheduleContainerView(BrowserView):
    template = ViewPageTemplateFile('templates/schedule_container_view.pt')

    @property
    def owner(self):
        return IHaveSchedule(self.context)

    @property
    def term(self):
        return ITerm(self.owner, None)

    @property
    def school_year(self):
        term = self.term
        if term is None:
            return None
        return ISchoolYear(term, None)

    def schedules(self):
        for name, schedule in list(self.context.items()):
            if schedule.timetable.__parent__ is not None:
                yield schedule
            else:
                # Remove stray schedule (LP: #1280528)
                del self.context[name]

    def timetables(self):
        snippets = filter(None, [
            queryMultiAdapter((schedule, self.request), name='schedule_table')
            for schedule in self.schedules()])
        return snippets

    def __call__(self):
        return self.template()


class FlourishScheduleContainerView(flourish.page.WideContainerPage,
                                    ScheduleContainerView):
    pass


class ScheduleDeleteView(BrowserView):
    template = ViewPageTemplateFile('templates/confirm_schedule_delete.pt')

    @property
    def schedule(self):
        name = self.request.get('schedule')
        if name is None or name not in self.context:
            return None
        return self.context[name]

    def nextURL(self):
        return absoluteURL(self.context, self.request)

    def __call__(self):
        schedule = self.schedule
        if schedule is not None:
            if 'CONFIRM' in self.request:
                del self.context[schedule.__name__]
                self.request.response.redirect(self.nextURL())
            elif 'CANCEL' in self.request:
                self.request.response.redirect(self.nextURL())
            else:
                return self.template()
        else:
            self.request.response.redirect(self.nextURL())


def scheduleOwnerTitle(context, request, view, name):
    owner = IHaveSchedule(context)
    return flourish.content.queryContentProvider(
        owner, request, view, 'title')


class ScheduleActionsLinks(flourish.page.RefineLinksViewlet):
    """Manager for Action links in scheduling views."""


class FlourishConfirmDeleteView(flourish.form.DialogForm, form.EditForm):
    """View used for confirming deletion of a timetable."""

    dialog_submit_actions = ('apply',)
    dialog_close_actions = ('cancel',)
    label = None

    def nextURL(self):
        link = flourish.content.queryContentProvider(
            self.context, self.request, self, 'done_link')
        if link is not None:
            return link.url
        return absoluteURL(self.context.__parent__, self.request)

    def delete(self):
        pass

    @button.buttonAndHandler(_("Delete"), name='apply')
    def handleDelete(self, action):
        next_url = self.nextURL()
        self.delete()
        self.request.response.redirect(next_url)
        self.ajax_settings['dialog'] = 'close'

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        pass

    def updateActions(self):
        super(FlourishConfirmDeleteView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class ScheduleAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for schedule Add links."""


class ScheduleContainerBreadcrumbs(flourish.breadcrumbs.Breadcrumbs):

    @property
    def url(self):
        base_url = absoluteURL(self.crumb_parent, self.request)
        return '%s/schedule' % base_url
