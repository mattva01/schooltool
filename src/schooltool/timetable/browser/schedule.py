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
SchoolTool timetabling views.
"""
import datetime
import urllib
import pytz
from persistent.list import PersistentList

import zope.schema
import zope.event
import zope.lifecycleevent
from zope.container.interfaces import INameChooser
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapts
from zope.component import getUtility, queryMultiAdapter
from zope.intid.interfaces import IIntIds
from zope.interface.exceptions import Invalid
from zope.interface import implements
from zope.interface import Interface
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.absoluteurl import absoluteURL

from z3c.form import form, field, button, widget, validator
from z3c.form.util import getSpecification

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.calendar.utils import parse_date, parse_time
from schooltool.common import DateRange
from schooltool.course.interfaces import ISection
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.term.interfaces import ITerm
from schooltool.term.term import getTermForDate
from schooltool.timetable.schedule import MeetingException
#from schooltool.timetable import SchooldaySlot
#from schooltool.timetable import TimetableActivity
#from schooltool.timetable import TimetableReplacedEvent
#from schooltool.timetable.interfaces import ITimetableSchemaContainer
#from schooltool.timetable.interfaces import ITimetable, IOwnTimetables
#from schooltool.timetable.interfaces import ITimetables, ITimetableDict
#from schooltool.timetable import TimetableOverlapError, TimetableOverflowError
#from schooltool.timetable import validateAgainstTerm
#from schooltool.timetable import validateAgainstOthers
from schooltool.timetable.interfaces import IHaveSchedule
from schooltool.traverser.traverser import TraverserPlugin

from schooltool.common import SchoolToolMessage as _



#def format_timetable_for_presentation(timetable):
#    """Prepare a timetable for presentation with Page Templates.
#
#    Returns a matrix where columns correspond to days, rows correspond to
#    periods, and cells contain a dict with two keys
#
#      'period' -- the name of this period (different days may have different
#                  periods)
#
#      'activity' -- activity or activities that occur during that period of a
#                    day.
#
#    First, let us create a timetable:
#
#      >>> from schooltool.timetable import Timetable, TimetableDay
#      >>> timetable = Timetable(['day 0', 'day 1', 'day 2', 'day 3'])
#      >>> timetable['day 0'] = TimetableDay()
#      >>> timetable['day 1'] = TimetableDay(['A', 'B'])
#      >>> timetable['day 2'] = TimetableDay(['C', 'D', 'E'])
#      >>> timetable['day 3'] = TimetableDay(['F'])
#      >>> timetable['day 1'].add('A', TimetableActivity('Something'))
#      >>> timetable['day 1'].add('B', TimetableActivity('A2'))
#      >>> timetable['day 1'].add('B', TimetableActivity('A1'))
#      >>> timetable['day 2'].add('C', TimetableActivity('Else'))
#      >>> timetable['day 3'].add('F', TimetableActivity('A3'))
#
#    Here's how it looks like
#
#      >>> matrix = format_timetable_for_presentation(timetable)
#      >>> for row in matrix:
#      ...    for cell in row:
#      ...        print '%(period)1s: %(activity)-11s |' % cell,
#      ...    print
#       :             | A: Something   | C: Else        | F: A3          |
#       :             | B: A1 / A2     | D:             |  :             |
#       :             |  :             | E:             |  :             |
#
#
#    """
#    rows = []
#    for ncol, (id, day) in enumerate(timetable.items()):
#        nrow = 0
#        for nrow, (period, actiter) in enumerate(day.items()):
#            activities = []
#            for a in actiter:
#                activities.append(a.title)
#            activities.sort()
#            if nrow >= len(rows):
#                rows.append([{'period': '', 'activity': ''}] * ncol)
#            rows[nrow].append({'period': period,
#                               'activity': " / ".join(activities)})
#        for nrow in range(nrow + 1, len(rows)):
#            rows[nrow].append({'period': '', 'activity': ''})
#    return rows


#class TimetablesTraverser(TraverserPlugin):
#    """A traverser that allows to traverse to a timetable of its context."""
#
#    def traverse(self, name):
#        return ITimetables(self.context).timetables


#class TimetableView(BrowserView):
#
#    __used_for__ = ITimetable
#
#    def rows(self):
#        return format_timetable_for_presentation(self.context)


#class TabindexMixin(object):
#    """Tab index calculator mixin for views."""
#
#    def __init__(self):
#        self.__tabindex = 0
#        self.__tabindex_matrix = []
#
#    def next_tabindex(self):
#        """Return the next tabindex.
#
#          >>> view = TabindexMixin()
#          >>> [view.next_tabindex() for n in range(5)]
#          [1, 2, 3, 4, 5]
#
#        See the docstring for tabindex_matrix for an example where
#        next_tabindex() returns values out of order
#        """
#        if self.__tabindex_matrix:
#            return self.__tabindex_matrix.pop(0)
#        else:
#            self.__tabindex += 1
#            return self.__tabindex
#
#    def tabindex_matrix(self, nrows, ncols):
#        """Ask next_tabindex to return transposed tab indices for a matrix.
#
#        For example, suppose that you have a 3 x 5 matrix like this:
#
#               col1 col2 col3 col4 col5
#          row1   1    4    7   10   13
#          row2   2    5    8   11   14
#          row3   3    6    9   12   15
#
#        Then you do
#
#          >>> view = TabindexMixin()
#          >>> view.tabindex_matrix(3, 5)
#          >>> [view.next_tabindex() for n in range(5)]
#          [1, 4, 7, 10, 13]
#          >>> [view.next_tabindex() for n in range(5)]
#          [2, 5, 8, 11, 14]
#          >>> [view.next_tabindex() for n in range(5)]
#          [3, 6, 9, 12, 15]
#
#        After the matrix is finished, next_tabindex reverts back to linear
#        allocation:
#
#          >>> [view.next_tabindex() for n in range(5)]
#          [16, 17, 18, 19, 20]
#
#        """
#        first = self.__tabindex + 1
#        self.__tabindex_matrix += [first + col * nrows + row
#                                     for row in range(nrows)
#                                       for col in range(ncols)]
#        self.__tabindex += nrows * ncols


#class TimetableConflictMixin(object):
#    """A mixin for views that check for booking conflicts."""
#
#    def sectionMap(self, term, ttschema):
#        """Compute a mapping of timetable slots to sections.
#
#        Returns a dict {(day_id, period_id): Set([section])}.  The set for
#        each period contains all sections that have activities in the
#        (non-composite) timetable during that timetable period.
#        """
#        from schooltool.timetable import findRelatedTimetables
#
#        section_map = {}
#        for day_id, day in ttschema.items():
#            for period_id in day.periods:
#                section_map[day_id, period_id] = set()
#
#        term_tables = [removeSecurityProxy(tt)
#                       for tt in findRelatedTimetables(term)]
#
#        for timetable in findRelatedTimetables(ttschema):
#            if removeSecurityProxy(timetable) not in term_tables:
#                continue
#            for day_id, period_id, activity in timetable.activities():
#                section_map[day_id, period_id].add(timetable.__parent__.__parent__)
#
#        return section_map
#
#    def getSchema(self):
#        """Return the chosen timetable schema.
#
#        If there are no timetable schemas, None is returned.
#        """
#        app = ISchoolToolApplication(None)
#        ttschemas = ITimetableSchemaContainer(app, None)
#        if ttschemas is None:
#            return None
#        ttschema_id = self.request.get('ttschema', ttschemas.default_id)
#        ttschema = ttschemas.get(ttschema_id, None)
#        if not ttschema and ttschemas:
#            ttschema = ttschemas.values()[0]
#        return ttschema
#
#    @property
#    def owner(self):
#        # XXX: make this property obsolete as soon as possible
#        return self.context
#
#    def getTerm(self):
#        """Return the chosen term."""
#        # XXX: make this method obsolete as soon as possible
#        return ITerm(self.owner)
#
#    def getSections(self, item):
#        raise NotImplementedError(
#            "This method should be implemented in subclasses")
#
#    def getGroupSections(self):
#        raise NotImplementedError(
#            "This method should be implemented in subclasses")
#
#    def getTimetable(self):
#        # XXX: somewhat broken as of now.
#        timetables = ITimetables(self.owner)
#        term = self.getTerm()
#        ttschema = self.getSchema()
#        return timetables.lookup(term, ttschema)


#class TimetableSetupViewBase(BrowserView, TimetableConflictMixin):
#    """Common methods for setting up timetables."""
#
#    @property
#    def ttschemas(self):
#        return ITimetableSchemaContainer(ISchoolToolApplication(None))


#class TimetableAddForm(TimetableSetupViewBase):
#
#    template = ViewPageTemplateFile('templates/timetable-add.pt')
#
#    def getTerm(self):
#        """Return the chosen term."""
#        return ITerm(self.context)
#
#    def addTimetable(self, timetable):
#        chooser = INameChooser(self.context)
#        name = chooser.chooseName('', timetable)
#        self.context[name] = timetable
#
#    def __call__(self):
#        self.has_timetables = bool(self.ttschemas)
#        if not self.has_timetables:
#            return self.template()
#        self.term = self.getTerm()
#        self.ttschema = self.getSchema()
#        self.ttkeys = ['.'.join((self.term.__name__, self.ttschema.__name__))]
#        if 'SUBMIT' in self.request:
#            timetable = self.ttschema.createTimetable(self.term)
#            self.addTimetable(timetable)
#            # TODO: find a better place to redirect to
#            self.request.response.redirect(
#                absoluteURL(self.context, self.request))
#        return self.template()


# XXX: remove this class soon!
#class SectionTimetableSetupView(TimetableSetupViewBase):
#
#    __used_for__ = ISection
#
#    template = ViewPageTemplateFile('templates/section-timetable-setup.pt')
#
#    def singleSchema(self):
#        return len(self.ttschemas.values()) == 1
#
#    def addTimetable(self, timetable):
#        tt_dict = ITimetables(self.context).timetables
#        chooser = INameChooser(tt_dict)
#        name = chooser.chooseName('', timetable)
#        tt_dict[name] = timetable
#
#    def getDays(self, ttschema):
#        """Return the current selection.
#
#        Returns a list of dicts with the following keys
#
#            title   -- title of the timetable day
#            periods -- list of timetable periods in that day
#
#        Each period is represented by a dict with the following keys
#
#            title    -- title of the period
#            selected -- a boolean whether that period is in self.context's tt
#                            for this shcema
#
#        """
#        timetable = self.getTimetable()
#
#        def days(schema):
#            for day_id, day in schema.items():
#                yield {'title': day_id,
#                       'periods': list(periods(day_id, day))}
#
#        def periods(day_id, day):
#            for period_id in day.periods:
#                if timetable:
#                    selected = timetable[day_id][period_id]
#                else:
#                    selected = False
#                yield {'title': period_id,
#                       'selected': selected}
#
#        return list(days(ttschema))
#
#    @property
#    def consecutive_label(self):
#        return _('Show consecutive periods as one period in journal')
#
#    def __call__(self):
#        self.has_timetables = bool(self.ttschemas)
#        if not self.has_timetables:
#            return self.template()
#        self.ttschema = self.getSchema()
#        self.term = ITerm(self.context)
#        self.ttkeys = ['.'.join((self.term.__name__, self.ttschema.__name__))]
#        self.days = self.getDays(self.ttschema)
#        #XXX dumb, this doesn't space course names
#        course_title = ''.join([course.title
#                                for course in self.context.courses])
#        section = removeSecurityProxy(self.context)
#        timetable = ITimetables(section).lookup(self.term, self.ttschema)
#        if timetable is None:
#            self.consecutive_value = False
#        else:
#            self.consecutive_value = timetable.consecutive_periods_as_one
#
#        if 'CANCEL' in self.request:
#            self.request.response.redirect(self.nextURL())
#
#        if 'SAVE' in self.request:
#            if timetable is None:
#                timetable = self.ttschema.createTimetable(self.term)
#                self.addTimetable(timetable)
#            if self.request.get('consecutive') == 'on':
#                timetable.consecutive_periods_as_one = True
#            else:
#                timetable.consecutive_periods_as_one = False
#
#            for day_id, day in timetable.items():
#                for period_id, period in list(day.items()):
#                    if '.'.join((day_id, period_id)) in self.request:
#                        if not period:
#                            # XXX Resource list is being copied
#                            # from section as this view can't do
#                            # proper resource booking
#                            act = TimetableActivity(title=course_title,
#                                                    owner=section,
#                                                    resources=section.resources)
#                            day.add(period_id, act)
#                    else:
#                        if period:
#                            for act in list(period):
#                                day.remove(period_id, act)
#
#            self.request.response.redirect(self.nextURL())
#
#        return self.template()
#
#    def nextURL(self):
#        return absoluteURL(self.context, self.request)


class SpecialDayView(BrowserView):
    """The view for changing the periods for a particular day.

    The typical use case: some periods get shortened or and some get
    cancelled altogether if some special event is held at noon.
    """

    select_template = ViewPageTemplateFile('templates/specialday_select.pt')
    form_template = ViewPageTemplateFile('templates/specialday_change.pt')

    error = None
    field_errors = None
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
                self.error = _('Some values were invalid.'
                               '  They are highlighted in red.')
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


#class SectionTimetablesViewBase(TimetableSetupViewBase):
#
#    def formatTimetableForTemplate(self, timetable):
#        timetable = removeSecurityProxy(timetable)
#        has_activities = False
#        days = []
#        for day_id, day in timetable.items():
#            periods = []
#            for period, activities in day.items():
#                periods.append({
#                    'title': period,
#                    'activities': " / ".join(
#                        sorted([a.title for a in activities])),
#                    })
#                has_activities |= bool(len(activities))
#            days.append({
#                'title': day_id,
#                'periods': periods,
#                })
#        return {
#            'timetable': timetable,
#            'has_activities': has_activities,
#            'days': days,
#            }


class ScheduleContainerView(BrowserView):
    template = ViewPageTemplateFile('templates/schedule-container-view.pt')

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

    def timetables(self):
        snippets = filter(None, [
            queryMultiAdapter((schedule, self.request), name='schedule_table')
            for schedule in self.context.values()])
        return snippets

    def __call__(self):
        return self.template()


class ScheduleDeleteView(BrowserView):
    template = ViewPageTemplateFile('templates/confirm-schedule-delete.pt')

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
