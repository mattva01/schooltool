#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Lyceum journal views.

$Id$

"""
import pytz
import urllib
from datetime import datetime

from zope.app import zapi
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.i18n.interfaces.locales import ICollator
from zope.interface import implements
from zope.publisher.browser import BrowserView
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL

from zc.table.interfaces import IColumn

from schooltool.app.browser.cal import month_names
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.course.interfaces import ISection
from schooltool.person.interfaces import IPerson
from schooltool.skin.breadcrumbs import Breadcrumbs
from schooltool.skin.breadcrumbs import CustomNameBreadCrumbInfo
from schooltool.skin.interfaces import IBreadcrumbInfo
from schooltool.table.interfaces import ITableFormatter
from schooltool.table.table import LocaleAwareGetterColumn
from schooltool.timetable.interfaces import ITimetableCalendarEvent
from schooltool.timetable.interfaces import ITimetables
from schooltool.traverser.traverser import AdapterTraverserPlugin

from lyceum.journal.interfaces import ILyceumJournal
from lyceum import LyceumMessage as _


def today():
    app = ISchoolToolApplication(None)
    tzinfo = pytz.timezone(IApplicationPreferences(app).timezone)
    dt = pytz.utc.localize(datetime.utcnow())
    return dt.astimezone(tzinfo).date()


class JournalCalendarEventViewlet(object):
    """Viewlet for section meeting calendar events.

    Adds an Attendance link to all section meeting events.
    """

    def attendanceLink(self):
        """Construct the URL for the attendance form for a section meeting.

        Returns None if the calendar event is not a section meeting event.
        """
        event_for_display = self.manager.event
        calendar_event = event_for_display.context
        journal = ILyceumJournal(calendar_event, None)
        if journal:
            return '%s/index.html?event_id=%s' % (
                zapi.absoluteURL(journal, self.request),
                urllib.quote(event_for_display.context.unique_id))


class GradeClassColumn(LocaleAwareGetterColumn):

    def getter(self, item, formatter):
        groups = ISchoolToolApplication(None)['groups']
        if item.gradeclass is not None:
            return groups[item.gradeclass].title
        return ""


class PersonGradesColumn(object):
    implements(IColumn)

    template = ViewPageTemplateFile("templates/journal_grade_column.pt")

    title = None
    name = None

    def __init__(self, meeting):
        self.meeting = meeting
        self.name = meeting.unique_id

    def meetingDate(self):
        app = ISchoolToolApplication(None)
        tzinfo = pytz.timezone(IApplicationPreferences(app).timezone)
        date = self.meeting.dtstart.astimezone(tzinfo).date()
        return date

    def getCellValue(self, item):
        journal = ILyceumJournal(self.meeting)
        return journal.getGrade(item, self.meeting, default="")

    def extra_url(self):
        parameters = []
        if 'month' in self.request:
            parameters.append("month=%s" % urllib.quote(self.request['month']))
        if 'TERM' in self.request:
            parameters.append("TERM=%s" % urllib.quote(self.request['TERM']))
        return "&" + "&".join(parameters)

    def renderHeader(self, formatter):
        header = self.meetingDate().strftime("%d")

        self.request = formatter.request
        journal = ILyceumJournal(self.meeting)
        meeting_id = self.meeting.unique_id
        url = absoluteURL(journal, self.request)
        url = "%sindex.html?event_id=%s%s" % (url,
                                              urllib.quote(self.meeting.unique_id),
                                              self.extra_url())
        header = '<a href="%s">%s</a>' % (url, header)

        meetingDate = self.meetingDate()
        klass = ""
        if meetingDate == today():
            klass = 'class="today" '

        return '<span %stitle="%s">%s</span>' % (
            klass, meetingDate.strftime("%Y-%m-%d"), header)

    def renderCell(self, item, formatter):
        self.request = formatter.request
        self.context = item
        return self.template()


class SelectedPersonGradesColumn(PersonGradesColumn):

    template = ViewPageTemplateFile("templates/selected_journal_grade_column.pt")

    def getCellName(self, item):
        return "%s.%s" % (item.__name__, self.meeting.__name__)

    def getHeader(self):
        return self.meetingDate().strftime("%d")

    def renderHeader(self, formatter):
        meetingDate = self.meetingDate()
        klass = ""
        if meetingDate == today():
            klass = 'class="today" '

        return '<span %stitle="%s">%s</span>' % (
            klass, meetingDate.strftime("%Y-%m-%d"), self.getHeader())

    def renderCell(self, item, formatter):
        self.request = formatter.request
        self.context = item
        return self.template()


class LyceumJournalView(object):

    template = ViewPageTemplateFile("templates/journal.pt")

    def __init__(self, context, request):
        self.context, self.request = context, request
        self.active_month = self.getActiveMonth()

    def __call__(self):
        if 'UPDATE_SUBMIT' in self.request:
            self.updateGradebook()

        app = ISchoolToolApplication(None)
        person_container = app['persons']
        self.gradebook = queryMultiAdapter((person_container, self.request),
                                           ITableFormatter)
        self.gradebook.setUp(items=self.members(),
                             columns_before=[GradeClassColumn(title=_('Grade'), name='grade')],
                             columns_after=self.gradeColumns(),
                             batch_size=0)
        return self.template()

    def allMeetings(self):
        term = self.getSelectedTerm()
        calendar = ISchoolToolCalendar(self.context.section)
        events = []
        # maybe expand would be better in here
        for event in calendar:
            if (ITimetableCalendarEvent.providedBy(event) and
                event.dtstart.date() in term):
                events.append(event)
        return sorted(events)

    def meetings(self):
        for event in self.allMeetings():
            if event.dtstart.date().month == self.active_month:
                yield event

    def members(self):
        members = [member for member in self.context.section.members
                   if IPerson.providedBy(member)]
        collator = ICollator(self.request.locale)
        members.sort(key=lambda a: collator.key(a.last_name))
        return members

    def updateGradebook(self):
        members = self.members()
        for meeting in self.meetings():
            for person in members:
                meeting_id = meeting.unique_id
                cell_id = "%s.%s" % (person.__name__, meeting.__name__)
                cell_value = self.request.get(cell_id, None)
                if cell_value is not None:
                    self.context.setGrade(person, meeting, cell_value)

    def gradeColumns(self):
        columns = []
        for meeting in self.meetings():
            app = ISchoolToolApplication(None)
            tzinfo = pytz.timezone(IApplicationPreferences(app).timezone)
            meeting_date = meeting.dtstart.astimezone(tzinfo).date()
            if meeting_date == self.selectedDate():
                columns.append(SelectedPersonGradesColumn(meeting))
            else:
                columns.append(PersonGradesColumn(meeting))
        return columns

    def getSelectedTerm(self):
        terms = ISchoolToolApplication(None)['terms']
        term_id = self.request.get('TERM', None)
        if term_id:
            term = terms[term_id]
            if term in self.scheduled_terms:
                return term

        return self.getCurrentTerm()

    def selectedDate(self):
        event_id = self.request.get('event_id', None)
        if event_id is not None:
            calendar = ISchoolToolCalendar(self.context.section)
            event = calendar.find(event_id)
            app = ISchoolToolApplication(None)
            tzinfo = pytz.timezone(IApplicationPreferences(app).timezone)
            if event:
                date = event.dtstart.astimezone(tzinfo).date()
                return date

        return today()

    def getCurrentTerm(self):
        date = self.selectedDate()
        for term in self.scheduled_terms:
            if date in term:
                return term
        return None

    @property
    def scheduled_terms(self):
        terms = ISchoolToolApplication(None)['terms']
        tt = ITimetables(self.context.section).timetables
        for key in tt.keys():
            term_id, schema_id = key.split(".")
            term = terms[term_id]
            yield term

    @property
    def section(self):
        app = ISchoolToolApplication(None)
        section = app['sections'][self.__parent__.__name__]
        return section

    def monthsInSelectedTerm(self):
        month = -1
        for meeting in self.allMeetings():
            if meeting.dtstart.date().month != month:
                yield meeting.dtstart.date().month
                month = meeting.dtstart.date().month

    def monthTitle(self, number):
        return month_names[number]

    def monthURL(self, month_id):
        url = absoluteURL(self.context.section, self.request)
        return "%s/journal/index.html?month=%s%s" % (url, month_id, self.extra_url())

    def getActiveMonth(self):
        available_months = list(self.monthsInSelectedTerm())
        if 'month' in self.request:
            month = int(self.request['month'])
            if month in available_months:
                return month

        month = self.selectedDate().month
        if month in available_months:
            return month

        return available_months[0]

    def extra_url(self):
        parameters = []
        if 'TERM' in self.request:
            parameters.append("TERM=%s" % urllib.quote(self.request['TERM']))
        return "&" + "&".join(parameters)


class JournalAbsoluteURL(BrowserView):
    implements(IAbsoluteURL)

    def __str__(self):
        section_id = self.context.__name__
        sections = ISchoolToolApplication(None)['sections']
        section = sections[section_id]

        url = zapi.absoluteURL(section, self.request)
        url += '/journal/'
        return url

    __call__ = __str__


class JournalBreadcrumbs(Breadcrumbs):

    @property
    def crumbs(self):
        section_id = self.context.__name__
        sections = ISchoolToolApplication(None)['sections']
        section = sections[section_id]
        section_crumbs = getMultiAdapter((section, self.request),
                                         name='breadcrumbs')
        for crumb in section_crumbs.crumbs:
            yield crumb

        info = getMultiAdapter((self.context, self.request), IBreadcrumbInfo)
        yield {'name': info.name, 'url': info.url, 'active': info.active}


JournalBreadcrumbInfo = CustomNameBreadCrumbInfo(_('Journal'))


LyceumJournalTraverserPlugin = AdapterTraverserPlugin(
    'journal', ILyceumJournal)
