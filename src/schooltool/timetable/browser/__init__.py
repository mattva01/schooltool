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

$Id$
"""

import datetime
import itertools
import sets
import re

from zope.component import adapts
from zope.i18n import translate
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy

from zope.app import zapi
from zope.app.publisher.browser import BrowserView
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from schooltool.calendar.utils import parse_date, parse_time
from schooltool.app.cal import CalendarEvent
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.person.interfaces import IPerson
from schooltool.traverser.interfaces import ITraverserPlugin

from schooltool import SchoolToolMessageID as _
from schooltool.timetable.interfaces import ITimetables, IHaveTimetables
from schooltool.timetable.interfaces import ITimetable
from schooltool.timetable.interfaces import ITerm
from schooltool.course.interfaces import ISection
from schooltool.timetable import Timetable, TimetableDay
from schooltool.timetable import TimetableActivity
from schooltool.timetable import SchooldayTemplate, SchooldaySlot
from schooltool.timetable.term import getNextTermForDate, getTermForDate
from schooltool.app.app import getSchoolToolApplication


class TabindexMixin(object):
    """Tab index calculator mixin for views."""

    def __init__(self):
        self.__tabindex = 0
        self.__tabindex_matrix = []

    def next_tabindex(self):
        """Return the next tabindex.

          >>> view = TabindexMixin()
          >>> [view.next_tabindex() for n in range(5)]
          [1, 2, 3, 4, 5]

        See the docstring for tabindex_matrix for an example where
        next_tabindex() returns values out of order
        """
        if self.__tabindex_matrix:
            return self.__tabindex_matrix.pop(0)
        else:
            self.__tabindex += 1
            return self.__tabindex

    def tabindex_matrix(self, nrows, ncols):
        """Ask next_tabindex to return transposed tab indices for a matrix.

        For example, suppose that you have a 3 x 5 matrix like this:

               col1 col2 col3 col4 col5
          row1   1    4    7   10   13
          row2   2    5    8   11   14
          row3   3    6    9   12   15

        Then you do

          >>> view = TabindexMixin()
          >>> view.tabindex_matrix(3, 5)
          >>> [view.next_tabindex() for n in range(5)]
          [1, 4, 7, 10, 13]
          >>> [view.next_tabindex() for n in range(5)]
          [2, 5, 8, 11, 14]
          >>> [view.next_tabindex() for n in range(5)]
          [3, 6, 9, 12, 15]

        After the matrix is finished, next_tabindex reverts back to linear
        allocation:

          >>> [view.next_tabindex() for n in range(5)]
          [16, 17, 18, 19, 20]

        """
        first = self.__tabindex + 1
        self.__tabindex_matrix += [first + col * nrows + row
                                     for row in range(nrows)
                                       for col in range(ncols)]
        self.__tabindex += nrows * ncols


class TimetablesTraverser(object):
    """A traverser that allows to traverse to a calendar owner's calendar."""

    adapts(IHaveTimetables)
    implements(ITraverserPlugin)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        if name == 'timetables':
            return ITimetables(self.context).timetables

        raise NotFound(self.context, name, request)


def fix_duplicates(names):
    """Change a list of names so that there are no duplicates.

    Trivial cases:

      >>> fix_duplicates([])
      []
      >>> fix_duplicates(['a', 'b', 'c'])
      ['a', 'b', 'c']

    Simple case:

      >>> fix_duplicates(['a', 'b', 'b', 'a', 'b'])
      ['a', 'b', 'b (2)', 'a (2)', 'b (3)']

    More interesting cases:

      >>> fix_duplicates(['a', 'b', 'b', 'a', 'b (2)', 'b (2)'])
      ['a', 'b', 'b (3)', 'a (2)', 'b (2)', 'b (2) (2)']

    """
    seen = sets.Set(names)
    if len(seen) == len(names):
        return names    # no duplicates
    result = []
    used = sets.Set()
    for name in names:
        if name in used:
            n = 2
            while True:
                candidate = '%s (%d)' % (name, n)
                if not candidate in seen:
                    name = candidate
                    break
                n += 1
            seen.add(name)
        result.append(name)
        used.add(name)
    return result


def parse_time_range(value, default_duration=None):
    """Parse a range of times (e.g. 9:45-14:20).

    Example:

        >>> parse_time_range('9:45-14:20')
        (datetime.time(9, 45), datetime.timedelta(0, 16500))

        >>> parse_time_range('00:00-24:00')
        (datetime.time(0, 0), datetime.timedelta(1))

        >>> parse_time_range('10:00-10:00')
        (datetime.time(10, 0), datetime.timedelta(0))

    Time ranges may span midnight

        >>> parse_time_range('23:00-02:00')
        (datetime.time(23, 0), datetime.timedelta(0, 10800))

    When the default duration is specified, you may omit the second time

        >>> parse_time_range('23:00', 45)
        (datetime.time(23, 0), datetime.timedelta(0, 2700))

    Invalid values cause a ValueError

        >>> parse_time_range('something else')
        Traceback (most recent call last):
          ...
        ValueError: bad time range: something else

        >>> parse_time_range('9:00')
        Traceback (most recent call last):
          ...
        ValueError: duration is not specified

        >>> parse_time_range('9:00-9:75')
        Traceback (most recent call last):
          ...
        ValueError: minute must be in 0..59

        >>> parse_time_range('5:99-6:00')
        Traceback (most recent call last):
          ...
        ValueError: minute must be in 0..59

        >>> parse_time_range('14:00-24:01')
        Traceback (most recent call last):
          ...
        ValueError: hour must be in 0..23

    White space can be inserted between times

        >>> parse_time_range(' 9:45 - 14:20 ')
        (datetime.time(9, 45), datetime.timedelta(0, 16500))

    but not inside times

        >>> parse_time_range('9: 45-14:20')
        Traceback (most recent call last):
          ...
        ValueError: bad time range: 9: 45-14:20

    """
    m = re.match(r'\s*(\d+):(\d+)\s*(?:-\s*(\d+):(\d+)\s*)?$', value)
    if not m:
        raise ValueError('bad time range: %s' % value)
    h1, m1 = int(m.group(1)), int(m.group(2))
    if not m.group(3):
        if default_duration is None:
            raise ValueError('duration is not specified')
        duration = default_duration
    else:
        h2, m2 = int(m.group(3)), int(m.group(4))
        if (h2, m2) != (24, 0):   # 24:00 is expressly allowed here
            datetime.time(h2, m2) # validate the second time
        duration = (h2*60+m2) - (h1*60+m1)
        if duration < 0:
            duration += 1440
    return datetime.time(h1, m1), datetime.timedelta(minutes=duration)


def format_time_range(start, duration):
    """Format a range of times (e.g. 9:45-14:20).

    Example:

        >>> format_time_range(datetime.time(9, 45),
        ...                   datetime.timedelta(0, 16500))
        '09:45-14:20'

        >>> format_time_range(datetime.time(0, 0), datetime.timedelta(1))
        '00:00-24:00'

        >>> format_time_range(datetime.time(10, 0), datetime.timedelta(0))
        '10:00-10:00'

        >>> format_time_range(datetime.time(23, 0),
        ...                   datetime.timedelta(0, 10800))
        '23:00-02:00'

    """
    end = (datetime.datetime.combine(datetime.date.today(), start) + duration)
    ends = end.strftime('%H:%M')
    if ends == '00:00' and duration == datetime.timedelta(1):
        return '00:00-24:00' # special case
    else:
        return '%s-%s' % (start.strftime('%H:%M'), ends)


# XXX: copied this from schooltool-0.9.rest.timetable
# Remove this once there is a thing like that in REST
# alga 2005-05-12
def format_timetable_for_presentation(timetable):
    """Prepare a timetable for presentation with Page Templates.

    Returns a matrix where columns correspond to days, rows correspond to
    periods, and cells contain a dict with two keys

      'period' -- the name of this period (different days may have different
                  periods)

      'activity' -- activity or activities that occur during that period of a
                    day.

    First, let us create a timetable:

      >>> from pprint import pprint
      >>> from schooltool.timetable import TimetableActivity
      >>> timetable = Timetable(['day 1', 'day 2', 'day 3'])
      >>> timetable['day 1'] = TimetableDay(['A', 'B'])
      >>> timetable['day 2'] = TimetableDay(['C', 'D', 'E'])
      >>> timetable['day 3'] = TimetableDay(['F'])
      >>> timetable['day 1'].add('A', TimetableActivity('Something'))
      >>> timetable['day 1'].add('B', TimetableActivity('A2'))
      >>> timetable['day 1'].add('B', TimetableActivity('A1'))

    Some timetable activities may have associated resources

      >>> from schooltool.resource.resource import Resource
      >>> r1 = Resource('R1')
      >>> r2 = Resource('R2')
      >>> timetable['day 2'].add('C', TimetableActivity('Else',
      ...                                               resources=[r1]))
      >>> timetable['day 3'].add('F', TimetableActivity('A3',
      ...                                               resources=[r2, r1]))

    Here's how it looks like

      >>> matrix = format_timetable_for_presentation(timetable)
      >>> for row in matrix:
      ...    for cell in row:
      ...        print '%(period)1s: %(activity)-11s |' % cell,
      ...    print
      A: Something   | C: Else (R1)   | F: A3 (R1, R2) |
      B: A1 / A2     | D:             |  :             |
       :             | E:             |  :             |


    """
    rows = []
    for ncol, (id, day) in enumerate(timetable.items()):
        for nrow, (period, actiter) in enumerate(day.items()):
            activities = []
            for a in actiter:
                resources = [r.title for r in a.resources]
                if resources:
                    resources.sort()
                    activities.append('%s (%s)'
                                      % (a.title, ', '.join(resources)))
                else:
                    activities.append(a.title)
            activities.sort()
            if nrow >= len(rows):
                rows.append([{'period': '', 'activity': ''}] * ncol)
            rows[nrow].append({'period': period,
                               'activity': " / ".join(activities)})
        for nrow in range(nrow + 1, len(rows)):
            rows[nrow].append({'period': '', 'activity': ''})
    return rows


class TimetableView(BrowserView):

    __used_for__ = ITimetable

    def title(self):
        timetabled = self.context.__parent__.__parent__
        msg = _("${object}'s timetable")
        msg.mapping = {'object': timetabled.title}
        return msg

    def rows(self):
        return format_timetable_for_presentation(self.context)


class TimetableSetupViewMixin(BrowserView):
    """Common methods for setting up timetables."""

    def getSchema(self):
        """Return the chosen timetable schema."""
        app = getSchoolToolApplication()
        ttschemas = app["ttschemas"]
        selected_ttschema = self.request.get('ttschema', ttschemas.default_id)
        return ttschemas.get(selected_ttschema, ttschemas.values()[0])


class PersonTimetableSetupView(TimetableSetupViewMixin):
    """A view for scheduling a student.

    This view displays a drop-down for every timetable period, listing the
    sections scheduled for that period.  When the user submits the form, the
    person is added to selected sections and removed from unselected ones.
    """

    __used_for__ = IPerson

    template = ViewPageTemplateFile('templates/person-timetable-setup.pt')

    def getTerm(self):
        """Return the chosen term."""
        if 'term' in self.request:
            terms = getSchoolToolApplication()["terms"]
            return terms[self.request['term']]
        else:
            return getNextTermForDate(datetime.date.today())

    def sectionMap(self, term, ttschema):
        """Compute a mapping of timetable slots to sections.

        Returns a dict {(day_id, period_id): Set([section])}.  The set for
        each period contains all sections that have activities in the
        (non-composite) timetable during that timetable period.
        """
        ttkey = "%s.%s" % (term.__name__, ttschema.__name__)
        section_map = {}
        for day_id, day in ttschema.items():
            for period_id in day.periods:
                section_map[day_id, period_id] = sets.Set()
        for section in getSchoolToolApplication()['sections'].values():
            timetable = ITimetables(section).timetables.get(ttkey)
            if timetable:
                for day_id, period_id, activity in timetable.itercontent():
                    section_map[day_id, period_id].add(section)
        return section_map

    def allSections(self, section_map):
        """Return a set of all sections that can be selected."""
        sections = sets.Set()
        for sectionset in section_map.itervalues():
            sections.update(sectionset)
        return sections

    def getDays(self, ttschema, section_map):
        """Return the current selection.

        Returns a list of dicts with the following keys

            title   -- title of the timetable day
            periods -- list of timetable periods in that day

        Each period is represented by a dict with the following keys

            title    -- title of the period
            sections -- all sections that are scheduled for this slot
            selected -- a list of sections of which self.context is a member,
                        or a list containing [None] if there are none.
            in_group -- user is a member of a section as part of a group.

        """

        def days(schema):
            for day_id, day in schema.items():
                yield {'title': day_id,
                       'periods': list(periods(day_id, day))}

        def sortedbytitle(seq, key=None):
            l = list(seq)
            if key is None:
                l.sort(lambda x, y: cmp(x.title, y.title))
            else:
                l.sort(lambda x, y: cmp(x[key].title, y[key].title))
            return l

        def periods(day_id, day):
            for period_id in day.periods:
                sections = section_map[day_id, period_id]
                sections = sortedbytitle(sections)

                in_group = []
                for group in sortedbytitle(self.context.groups):
                    for section in sections:
                        if group in section.members:
                            in_group.append({'group': group,
                                            'section': section})
                in_group = sortedbytitle(in_group, 'section')

                selected = []
                if not in_group:
                    selected = [section for section in sections
                                if self.context in section.members]
                    selected = sortedbytitle(selected)
                if not selected:
                    selected = [None]

                yield {'title': period_id,
                       'selected': selected,
                       'sections': sections,
                       'in_group': in_group}

        return list(days(ttschema))

    def __call__(self):
        self.app = getSchoolToolApplication()
        self.has_timetables = bool(self.app["terms"] and self.app["ttschemas"])
        if not self.has_timetables:
            return self.template()
        self.term = self.getTerm()
        self.ttschema = self.getSchema()
        section_map = self.sectionMap(self.term, self.ttschema)
        self.days = self.getDays(self.ttschema, section_map)
        if 'SAVE' in self.request:
            student = removeSecurityProxy(self.context)
            all_sections = self.allSections(section_map)
            selected = self.request.get('sections', [])
            for section in all_sections:
                want = section.__name__ in selected
                have = student in section.members
                if want and not have:
                    section.members.add(student)
                elif not want and have:
                    section.members.remove(student)
            self.days = self.getDays(self.ttschema, section_map)
        return self.template()


class SectionTimetableSetupView(TimetableSetupViewMixin):

    __used_for__ = ISection

    template = ViewPageTemplateFile('templates/section-timetable-setup.pt')

    def singleSchema(self):
        return len(self.app['ttschemas'].values()) == 1

    def singleTerm(self):
        return len(self.app['terms'].values()) == 1

    def getTerms(self):
        """Return the chosen term."""
        if 'terms' in self.request:
            terms = getSchoolToolApplication()['terms']
            requested_terms = []

            # request['terms'] may be a list of strings or a single string, we
            # need to handle both cases
            try:
                requested_terms = requested_terms + self.request['terms']
            except TypeError:
                requested_terms.append(self.request['terms'])
            return [terms[term] for term in requested_terms]
        else:
            return [getNextTermForDate(datetime.date.today()),]

    def getDays(self, ttschema):
        """Return the current selection.

        Returns a list of dicts with the following keys

            title   -- title of the timetable day
            periods -- list of timetable periods in that day

        Each period is represented by a dict with the following keys

            title    -- title of the period
            selected -- a boolean whether that period is in self.context's tt
                            for this shcema

        """

        try:
            # All timetables for a given ttschema will have the same pattern
            # regardless of term.
            timetable = ITimetables(self.context).timetables[self.ttkeys[0]]
        except KeyError:
            timetable = None

        def days(schema):
            for day_id, day in schema.items():
                yield {'title': day_id,
                       'periods': list(periods(day_id, day))}

        def periods(day_id, day):
            for period_id in day.periods:
                if timetable:
                    selected = timetable[day_id][period_id]
                else:
                    selected = False
                yield {'title': period_id,
                       'selected': selected}

        return list(days(ttschema))

    def __call__(self):
        self.app = getSchoolToolApplication()
        self.has_timetables = bool(self.app["terms"] and self.app["ttschemas"])
        if not self.has_timetables:
            return self.template()
        self.terms = self.getTerms()
        self.ttschema = self.getSchema()
        self.ttkeys = ['.'.join((term.__name__, self.ttschema.__name__))
                       for term in self.terms]
        self.days = self.getDays(self.ttschema)
        #XXX dumb, this doesn't space course names
        course_title = ''.join([course.title
                                for course in self.context.courses])

        if 'CANCEL' in self.request:
            self.request.response.redirect(
                zapi.absoluteURL(self.context, self.request))
        if 'SAVE' in self.request:
            section = removeSecurityProxy(self.context)
            for key in self.ttkeys:
                timetable =  self.ttschema.createTimetable()
                ITimetables(section).timetables[key] = timetable
                for day_id, day in timetable.items():
                    for period_id in day.periods:
                        if '.'.join((day_id, period_id)) in self.request:
                            act =  TimetableActivity(title=course_title,
                                                     owner=section)
                            timetable[day_id].add(period_id, act)

            # TODO: find a better place to redirect to
            self.request.response.redirect(
                zapi.absoluteURL(
                    ITimetables(self.context).timetables[self.ttkeys[0]],
                    self.request))

        return self.template()


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

    def extractPeriods(self):
        """Return a list of three-tuples with period titles, tstarts,
        durations.

        If errors are encountered in some fields, the names of the
        fields get added to field_errors.
        """
        model = self.context.model
        result = []
        for info in model.originalPeriodsInDay(self.term, self.context,
                                               self.date):
            period_id, tstart, duration = info
            start_name = period_id + '_start'
            end_name = period_id + '_end'
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
                    result.append((period_id, start, duration))

        return result

    def update(self):
        """Read and validate form data, and update model if necessary.

        Also choose the correct template to render.
        """
        self.field_errors = []
        self.template = self.select_template
        if 'CANCEL' in self.request:
            self.request.response.redirect(
                zapi.absoluteURL(self.context, self.request))
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
            daytemplate = []
            for title, start, duration in self.extractPeriods():
                daytemplate.append((title, SchooldaySlot(start, duration)))
            if self.field_errors:
                self.error = _('Some values were invalid.'
                               '  They are highlighted in red.')
            else:
                exceptionDays = removeSecurityProxy(
                    self.context.model.exceptionDays)
                exceptionDays[self.date] = daytemplate
                self.request.response.redirect(
                    zapi.absoluteURL(self.context, self.request))


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

    def getPeriods(self):
        """A helper method that returns a list of tuples of:

        (period_title, orig_start, orig_end, actual_start, actual_end)
        """
        model = self.context.model
        result = []
        actual_times = {}
        for info in model.periodsInDay(self.term, self.context, self.date):
            period_id, tstart, duration = info
            endtime = self.timeplustd(tstart, duration)
            actual_times[period_id] = (tstart.strftime("%H:%M"),
                                       endtime.strftime("%H:%M"))
        for info in model.originalPeriodsInDay(self.term, self.context,
                                                 self.date):
            period_id, tstart, duration = info
            # datetime authors are cowards
            endtime = self.timeplustd(tstart, duration)
            result.append((period_id,
                           tstart.strftime("%H:%M"),
                           endtime.strftime("%H:%M")) +
                          actual_times.get(period_id, ('', '')))
        return result

    def __call__(self):
        self.update()
        return self.template()


class EmergencyDayView(BrowserView):
    """On emergencies such as extreme temperetures, blizzards, etc,
    school is cancelled, and a different day gets added to the term
    instead.

    This view lets the administrator choose the cancelled date and
    presents the user with a choice of non-schooldays within a term
    and the days immediately after the term.
    """

    __used_for__ = ITerm

    template = None
    date_template = ViewPageTemplateFile('templates/emergency_select.pt')
    replacement_template = ViewPageTemplateFile('templates/emergency2.pt')

    error = None
    date = None
    replacement = None

    def replacements(self):
        """Return all non-schooldays in term plus 3 days after the term."""
        result = []
        for date in self.context:
            if date > self.date:
                if not self.context.isSchoolday(date):
                    result.append(date)
        last = self.context.last
        day = datetime.timedelta(1)
        result.append(last + day)
        result.append(last + 2 * day)
        result.append(last + 3 * day)
        return result

    def update(self):
        self.template = self.date_template
        if 'CANCEL' in self.request:
            self.request.response.redirect(
                zapi.absoluteURL(self.context, self.request))
            return
        if 'date' in self.request:
            try:
                self.date = parse_date(self.request['date'])
            except ValueError:
                self.error = _("The date you entered is invalid."
                               "  Please use the YYYY-MM-DD format.")
                return
            if not self.date in self.context:
                self.error = _("The date you entered does not belong to"
                               " this term.")
                return
            if not self.context.isSchoolday(self.date):
                self.error = _("The date you entered is not a schoolday.")
                return

            self.template = self.replacement_template
        if 'replacement' in self.request:
            try:
                self.replacement = parse_date(self.request['replacement'])
            except ValueError:
                self.error = _("The replacement date you entered is invalid.")
                return

        if self.date and self.replacement:
            if self.context.last < self.replacement:
                self.context.last = self.replacement
            assert not self.context.isSchoolday(self.replacement)
            assert self.context.isSchoolday(self.date)
            self.context.add(self.replacement)

            # Update all schemas
            ttschemas = getSchoolToolApplication()['ttschemas']
            for schema in ttschemas.values():
                model = schema.model
                exceptionDays = removeSecurityProxy(model.exceptionDays)
                exceptionDayIds = removeSecurityProxy(model.exceptionDayIds)
                exceptionDays[self.date] = SchooldayTemplate()
                day_id = model.getDayId(self.context, self.date)
                exceptionDayIds[self.replacement] = removeSecurityProxy(day_id)

            # Post calendar events to schoolwide calendar
            calendar = ISchoolToolCalendar(getSchoolToolApplication())
            dtstart = datetime.datetime.combine(self.date, datetime.time())
            msg = _('School cancelled due to emergency.'
                    ' Replacement day $replacement.')
            msg.mapping['replacement'] = str(self.replacement)
            msg = translate(msg, context=self.request)
            calendar.addEvent(
                CalendarEvent(dtstart, datetime.timedelta(),
                              msg, allday=True))

            dtstart = datetime.datetime.combine(self.replacement,
                                                datetime.time())
            msg = _('Replacement day for emergency day $emergency.')
            msg.mapping['emergency'] = str(self.date)
            msg = translate(msg, context=self.request)
            calendar.addEvent(
                CalendarEvent(dtstart, datetime.timedelta(),
                              msg, allday=True))

            self.request.response.redirect(
                zapi.absoluteURL(self.context, self.request))



    def __call__(self):
        self.update()
        return self.template()
