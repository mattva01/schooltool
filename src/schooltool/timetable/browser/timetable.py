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

from zope.interface import Interface
from zope.schema import TextLine, Date, Int
from zope.schema.interfaces import RequiredMissing
from zope.app import zapi
from zope.app.publisher.browser import BrowserView
from zope.app.form.browser.add import AddView
from zope.app.form.browser.submit import Update
from zope.app.form.utility import setUpEditWidgets
from zope.app.form.interfaces import WidgetsError
from zope.app.container.interfaces import INameChooser
from zope.app.event.objectevent import modified
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form.utility import getWidgetsData, setUpWidgets
from zope.app.form.interfaces import IInputWidget
from zope.app.form.interfaces import IWidgetInputError
from zope.i18n import translate
from zope.security.proxy import removeSecurityProxy

from schoolbell.calendar.utils import parse_date, parse_time
from schoolbell.calendar.utils import next_month, week_start
from schoolbell.app.browser.cal import month_names

from schooltool.timetable.interfaces import ITimetable, ITimetableSchema
from schooltool.timetable.interfaces import ITermContainer, ITerm
from schooltool.timetable.interfaces import ITimetableSchemaContainer
from schooltool.timetable.interfaces import ITimetableModelFactory
from schooltool.interfaces import IPerson, ISection
from schooltool.timetable import Term, Timetable, TimetableDay
from schooltool.timetable import TimetableActivity
from schooltool.timetable import TimetableSchema, TimetableSchemaDay
from schooltool.timetable import SchooldayTemplate, SchooldayPeriod
from schooltool.timetable import getNextTermForDate, getTermForDate
from schooltool import getSchoolToolApplication
from schooltool.browser.app import ContainerView
from schooltool import SchoolToolMessageID as _


class TermContainerView(ContainerView):
    """Term container view."""

    __used_for__ = ITermContainer

    index_title = _("Terms")
    add_title = _("Add a new term")
    add_url = "new.html"


class ITermForm(Interface):
    """Form schema for ITerm add/edit views."""

    title = TextLine(title=_("Title"))

    first = Date(title=_("Start date"))

    last = Date(title=_("End date"))


class TermView(BrowserView):
    """Browser view for terms."""

    __used_for__ = ITerm

    def calendar(self):
        """Prepare the calendar for display.

        Returns a structure composed of lists and dicts, see `TermRenderer`
        for more details.
        """
        return TermRenderer(self.context).calendar()


class TermEditViewMixin(object):
    """Mixin for Term add/edit views."""

    def _buildTerm(self):
        """Build a Term object from form values.

        Returns None if the form doesn't contain enough information.
        """
        try:
            data = getWidgetsData(self, ITermForm)
        except WidgetsError:
            return None
        try:
            term = Term(data['title'], data['first'], data['last'])
        except ValueError:
            return None # date range invalid
        term.addWeekdays(0, 1, 2, 3, 4, 5, 6)
        holidays = self.request.form.get('holiday', [])
        if not isinstance(holidays, list):
            holidays = [holidays]
        for holiday in holidays:
            try:
                term.remove(parse_date(holiday))
            except ValueError:
                pass # ignore ill-formed or out-of-range dates
        toggle = [n for n in range(7) if ('TOGGLE_%d' % n) in self.request]
        if toggle:
            term.toggleWeekdays(*toggle)
        return term


class TermEditView(BrowserView, TermEditViewMixin):
    """Edit view for terms."""

    __used_for__ = ITerm

    creating = False

    update_status = None

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        setUpEditWidgets(self, ITermForm)

    def title(self):
        title = _("Change Term: $title")
        title.mapping = {'title': self.context.title}
        return title

    def update(self):
        if self.update_status is not None:
            return self.update_status # We've been called before.
        self.update_status = ''
        self.term = self._buildTerm()
        if self.term is None:
            self.term = self.context
        elif Update in self.request:
            self.context.reset(self.term.first, self.term.last)
            for day in self.term:
                if self.term.isSchoolday(day):
                    self.context.add(day)
            modified(self.context)
            self.update_status = _("Saved changes.")
        return self.update_status

    def calendar(self):
        """Prepare the calendar for display.

        Returns a structure composed of lists and dicts, see `TermRenderer`
        for more details.
        """
        return TermRenderer(self.term).calendar()


class TermAddView(AddView, TermEditViewMixin):
    """Adding view for terms."""

    __used_for__ = ITermContainer

    creating = True

    title = _("New term")

    # Since this view is registered via <browser:page>, and not via
    # <browser:addform>, we need to set up some attributes for AddView.
    schema = ITermForm
    _arguments = ()
    _keyword_arguments = ()
    _set_before_add = ()
    _set_after_add = ()

    def update(self):
        """Process the form."""
        self.term = self._buildTerm()
        return AddView.update(self)

    def create(self):
        """Create the object to be added.

        We already have it, actually -- unless there was an error in the form.
        """
        if self.term is None:
            raise WidgetsError([])
        return self.term

    def add(self, content):
        """Add the object to the term container."""
        chooser = INameChooser(self.context)
        name = chooser.chooseName(None, content)
        self.context[name] = content

    def nextURL(self):
        """Return the location to visit once the term's been added."""
        return zapi.absoluteURL(self.context, self.request)

    def calendar(self):
        """Prepare the calendar for display.

        Returns None if the form doesn't contain enough information.  Otherwise
        returns a structure composed of lists and dicts (see `TermRenderer`
        for more details).
        """
        if self.term is None:
            return None
        return TermRenderer(self.term).calendar()


class TermRenderer(object):
    """Helper for rendering ITerms."""

    first_day_of_week = 0 # Monday  TODO: get from IPersonPreferences

    def __init__(self, term):
        self.term = term

    def calendar(self):
        """Prepare the calendar for display.

        Returns a list of month dicts (see `month`).
        """
        calendar = []
        date = self.term.first
        counter = itertools.count(1)
        while date <= self.term.last:
            start_of_next_month = next_month(date)
            end_of_this_month = start_of_next_month - datetime.date.resolution
            maxdate = min(self.term.last, end_of_this_month)
            calendar.append(self.month(date, maxdate, counter))
            date = start_of_next_month
        return calendar

    def month(self, mindate, maxdate, counter):
        """Prepare one month for display.

        Returns a dict with these keys:

            month   -- title of the month
            year    -- the year number
            weeks   -- a list of week dicts in this month (see `week`)

        """
        assert (mindate.year, mindate.month) == (maxdate.year, maxdate.month)
        weeks = []
        date = week_start(mindate, self.first_day_of_week)
        while date <= maxdate:
            weeks.append(self.week(date, mindate, maxdate, counter))
            date += datetime.timedelta(days=7)
        return {'month': month_names[mindate.month],
                'year': mindate.year,
                'weeks': weeks}

    def week(self, start_of_week, mindate, maxdate, counter):
        """Prepare one week of a Term for display.

        `start_of_week` is the date when the week starts.

        `mindate` and `maxdate` are used to indicate which month (or part of
        the month) interests us -- days in this week that fall outside
        [mindate, maxdate] result in a dict containing None values for all
        keys.

        `counter` is an iterator that returns indexes for days
        (itertools.count(1) is handy for this purpose).

        `term` is an ITerm that indicates which days are schooldays,
        and which are holidays.

        Returns a dict with these keys:

            number  -- week number
            days    -- a list of exactly seven dicts

        Each day dict has the following keys

            date    -- date as a string (YYYY-MM-DD)
            number  -- day of month
                       (None when date is outside [mindate, maxdate])
            index   -- serial number of this day (used in Javascript)
            class   -- CSS class ('holiday' or 'schoolday')
            checked -- True for holidays, False for schooldays
            onclick -- onclick event handler that calls toggle(index)

        """
        # start_of_week will be a Sunday or a Monday.  If it is a Sunday,
        # we want to take the ISO week number of the following Monday.  If
        # it is a Monday, we won't break anything by taking the week number
        # of the following Tuesday.
        week_no = (start_of_week + datetime.date.resolution).isocalendar()[1]
        date = start_of_week
        days = []
        for day in range(7):
            if mindate <= date <= maxdate:
                index = counter.next()
                checked = not self.term.isSchoolday(date)
                css_class = checked and 'holiday' or 'schoolday'
                days.append({'number': date.day, 'class': css_class,
                             'date': date.strftime('%Y-%m-%d'),
                             'index': index, 'checked': checked,
                             'onclick': 'javascript:toggle(%d)' % index})
            else:
                days.append({'number': None, 'class': None, 'index': None,
                             'onclick': None, 'checked': None, 'date': None})
            date += datetime.date.resolution
        return {'number': week_no,
                'days': days}


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


class TimetableSchemaContainerView(ContainerView):
    """TimetableSchema Container view."""

    __used_for__ = ITimetableSchemaContainer

    index_title = _("School Timetables")
    add_title = _("Add a new schema")
    add_url = "add.html"

    def update(self):
        if 'UPDATE_SUBMIT' in self.request:
            self.context.default_id = self.request['ttschema'] or None
        return ''


class IAdvancedTimetableSchemaAddSchema(Interface):

    title = TextLine(title=u"Title", required=False)
    duration = Int(title=u"Duration", description=u"Duration in minutes",
                   required=False)


class AdvancedTimetableSchemaAdd(BrowserView, TabindexMixin):
    """View for defining a new timetable schema.

    Can be accessed at /ttschemas/schemawizard.html.

    TODO: this class will soon be replaced by a new, more complicated wizard,
    defined in the schooltool.browser.ttwizard module.
    """

    __used_for__ = ITimetableSchemaContainer

    template = ViewPageTemplateFile("templates/advancedtts.pt")

    # Used in the page template
    days_of_week = (_("Monday"),
                    _("Tuesday"),
                    _("Wednesday"),
                    _("Thursday"),
                    _("Friday"),
                    _("Saturday"),
                    _("Sunday"),
                   )

    _schema = IAdvancedTimetableSchemaAddSchema

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        TabindexMixin.__init__(self)
        setUpWidgets(self, self._schema, IInputWidget,
                     initial={'title': 'default'})

    def __call__(self):

        # We could build a custom widget for the model radio buttons, but I do
        # not think it is worth the trouble.
        self.model_error = None
        self.model_name = self.request.get('model')

        self.ttschema = self._buildSchema()
        self.day_templates = self._buildDayTemplates()

        if 'CREATE' in self.request:
            data = getWidgetsData(self, self._schema)
            factory = zapi.queryUtility(ITimetableModelFactory,
                                        name=self.model_name)
            if factory is None:
                self.model_error = _("Please select a value")
            if not self.title_widget.error() and not self.model_error:
                model = factory(self.ttschema.day_ids, self.day_templates)
                self.ttschema.model = model
                self.ttschema.title = data['title']
                nameChooser = INameChooser(self.context)
                key = nameChooser.chooseName('', self.ttschema)
                self.context[key] = self.ttschema
                #Note: if you uncomment this, fix the i18n bug inside too.
                #self.request.appLog(_("Timetable schema %s created") %
                #               getPath(self.context[key]))
                return self.request.response.redirect(
                    zapi.absoluteURL(self.context, self.request))
        return self.template()

    def rows(self):
        return format_timetable_for_presentation(self.ttschema)

    def _buildSchema(self):
        """Build a timetable schema from data in the request."""
        n = 1
        day_ids = []
        day_idxs = []
        while 'day%d' % n in self.request:
            if 'DELETE_DAY_%d' % n not in self.request:
                day_id = self.request['day%d' % n].strip()
                if not day_id:
                    day_id_msgid = _('Day ${number}')
                    day_id_msgid.mapping = {'number': len(day_ids) + 1}
                    day_id = translate(day_id_msgid, context=self.request)
                day_ids.append(day_id)
                day_idxs.append(n)
            n += 1
        if 'ADD_DAY' in self.request or not day_ids:
            day_id_msgid = _('Day ${number}')
            day_id_msgid.mapping = {'number': len(day_ids) + 1}
            day_id = translate(day_id_msgid, context=self.request)
            day_ids.append(day_id)
            day_idxs.append(-1)
        day_ids = fix_duplicates(day_ids)

        periods_for_day = []
        longest_day = None
        previous_day = None
        for idx, day in zip(day_idxs, day_ids):
            n = 1
            if ('COPY_DAY_%d' % (idx - 1) in self.request
                and previous_day is not None):
                periods = list(previous_day)
            else:
                periods = []
                while 'day%d.period%d' % (idx, n) in self.request:
                    per_id = self.request['day%d.period%d' % (idx, n)].strip()
                    periods.append(per_id)
                    n += 1
                periods = filter(None, periods)
                if not periods:
                    period1 = translate(_("Period 1"), context=self.request)
                    periods = [period1]
                else:
                    periods = fix_duplicates(periods)
            periods_for_day.append(periods)
            if longest_day is None or len(periods) > len(longest_day):
                longest_day = periods
            previous_day = periods

        if 'ADD_PERIOD' in self.request:
            period_name_msgid = _('Period ${number}')
            period_name_msgid.mapping = {'number': len(longest_day) + 1}
            period_name = translate(period_name_msgid, context=self.request)
            longest_day.append(period_name)

        ttschema = TimetableSchema(day_ids)
        for day, periods in zip(day_ids, periods_for_day):
            ttschema[day] = TimetableSchemaDay(periods)

        return ttschema

    def _buildDayTemplates(self):
        """Built a dict of day templates from data contained in the request.

        The dict is suitable to be passed as the second argument to the
        timetable model factory.
        """
        data = getWidgetsData(self, self._schema)
        default_duration = data.get('duration')
        result = {None: SchooldayTemplate()}
        n = 1
        self.discarded_some_periods = False
        while 'time%d.period' % n in self.request:
            raw_value = [0]
            period = self.request['time%d.period' % n]
            for day in range(7):
                value = self.request.form.get('time%d.day%d' % (n, day), '')
                if not value:
                    continue
                try:
                    start, duration = parse_time_range(value, default_duration)
                except ValueError:
                    # ignore invalid values for now, but tell the user
                    self.discarded_some_periods = True
                    continue
                if day not in result:
                    result[day] = SchooldayTemplate()
                result[day].add(SchooldayPeriod(period, start, duration))
            n += 1
        for day in range(1, 7):
            if 'COPY_PERIODS_%d' % day in self.request:
                if (day - 1) in result:
                    result[day] = result[day - 1]
                elif day in result:
                    del result[day]
        return result

    def all_periods(self):
        """Return a list of all period names in order of occurrence."""
        periods = []
        for day_id in self.ttschema.day_ids:
            for period in self.ttschema[day_id].periods:
                if period not in periods:
                    periods.append(period)
        return periods

    def period_times(self):
        """Return a list of all period times for every day of the week."""
        result = []
        times_for = {}
        for period in self.all_periods():
            times = [None] * 7
            times_for[period] = times
            result.append({'title': period, 'times': times})
        for day, template in self.day_templates.items():
            for event in template:
                if event.title in times_for:
                    range = format_time_range(event.tstart, event.duration)
                    times_for[event.title][day] = range
        return result


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

      >>> from schooltool.app import Resource
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


class TimetableSchemaView(TimetableView):

    __used_for__ = ITimetableSchema

    def title(self):
        msg = _("Timetable schema ${schema}")
        msg.mapping = {'schema': self.context.__name__}
        return msg


class SimpleTimetableSchemaAdd(BrowserView):
    """A simple timetable schema definition view"""

    _nrperiods = 9

    day_ids = (_("Monday"),
               _("Tuesday"),
               _("Wednesday"),
               _("Thursday"),
               _("Friday"),
               )

    error = None

    template = ViewPageTemplateFile('templates/simpletts.pt')

    def __init__(self, content, request):
        BrowserView.__init__(self, content, request)
        self._schema = {}
        self._schema['title'] = TextLine(__name__='title', title=u"Title")
        for nr in range(1, self._nrperiods + 1):
            pname = 'period_name_%s' % nr
            pstart = 'period_start_%s' % nr
            pfinish = 'period_finish_%s' % nr
            self._schema[pname] = TextLine(__name__=pname,
                                           title=u"Period title",
                                           required=False)
            self._schema[pstart] = TextLine(__name__=pstart,
                                            title=u"Period start time",
                                            required=False)
            self._schema[pfinish] = TextLine(__name__=pfinish,
                                             title=u"Period finish time",
                                             required=False)
        setUpWidgets(self, self._schema, IInputWidget,
                     initial={'title': 'default'})

    def _setError(self, name, error=RequiredMissing()):
        """Set an error on a widget."""
        # XXX Touching widget._error is bad, see
        #     http://dev.zope.org/Zope3/AccessToWidgetErrors
        # The call to setRenderedValue is necessary because
        # otherwise _getFormValue will call getInputValue and
        # overwrite _error while rendering.
        widget = getattr(self, name + '_widget')
        widget.setRenderedValue(widget._getFormValue())
        if not IWidgetInputError.providedBy(error):
            error = WidgetInputError(name, widget.label, error)
        widget._error = error

    def getPeriods(self):
        try:
            data = getWidgetsData(self, self._schema)
        except WidgetsError:
            return []

        result = [] 
        for nr in range(1, self._nrperiods + 1):
            pname = 'period_name_%s' % nr
            pstart = 'period_start_%s' % nr
            pfinish = 'period_finish_%s' % nr
            if data.get(pstart) or data.get(pfinish):
                try:
                    start, duration = parse_time_range(
                        "%s-%s" % (data[pstart], data[pfinish]))
                except ValueError:
                    self.error = _('Please use HH:MM format for period '
                                   'start and end times')
                    continue
                name = data[pname]
                if not name:
                    name = data[pstart]
                result.append((name, start, duration))
        return result

    def createSchema(self, periods):
        daytemplate = SchooldayTemplate()
        for title, start, duration in periods:
            daytemplate.add(SchooldayPeriod(title, start, duration))

        factory = zapi.getUtility(ITimetableModelFactory,
                                  'WeeklyTimetableModel')
        model = factory(self.day_ids, {None: daytemplate})
        schema = TimetableSchema(self.day_ids)
        for day_id in self.day_ids:
            schema[day_id] = TimetableSchemaDay(
                [title for title, start, duration in periods])
        schema.model = model
        return schema

    def __call__(self):
        try:
            data = getWidgetsData(self, self._schema)
        except WidgetsError:
            return self.template()

        if 'CANCEL' in self.request:
            self.request.response.redirect(
                zapi.absoluteURL(self.context, self.request))
        elif 'CREATE' in self.request:
            periods = self.getPeriods()
            if self.error:
                return self.template()

            if not periods:
                self.error = _('You must specify at least one period.')
                return self.template()

            schema = self.createSchema(periods)
            schema.title = data['title']

            nameChooser = INameChooser(self.context)
            name = nameChooser.chooseName('', schema)

            self.context[name] = schema
            self.request.response.redirect(
                zapi.absoluteURL(self.context, self.request))

        return self.template()


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
            timetable = section.timetables.get(ttkey)
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

        """

        def days(schema):
            for day_id, day in schema.items():
                yield {'title': day_id,
                       'periods': list(periods(day_id, day))}

        def periods(day_id, day):
            for period_id in day.periods:
                sections = section_map[day_id, period_id]
                selected = [section for section in sections
                            if self.context in section.members]
                if not selected:
                    selected = [None]
                yield {'title': period_id,
                       'selected': selected,
                       'sections': sections}

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
            timetable = self.context.timetables[self.ttkeys[0]]
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
        self.ttkeys = [''.join((term.__name__, '.', self.ttschema.__name__))
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
                section.timetables[key] = timetable
                for day_id, day in timetable.items():
                    for period_id in day.periods:
                        if ''.join((day_id, '.',period_id)) in self.request:
                            act =  TimetableActivity(title=course_title,
                                                     owner=section)
                            timetable[day_id].add(period_id, act)

            # TODO: find a better place to redirect to
            self.request.response.redirect(
                zapi.absoluteURL(self.context.timetables[self.ttkeys[0]],
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
        for period in model.originalPeriodsInDay(self.term, self.context,
                                                 self.date):
            start_name = period.title + '_start'
            end_name = period.title + '_end'
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
                    result.append((period.title, start, duration))
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
            daytemplate = SchooldayTemplate()
            for title, start, duration in self.extractPeriods():
                daytemplate.add(SchooldayPeriod(title, start, duration))
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
        for period in model.periodsInDay(self.term, self.context, self.date):
            endtime = self.timeplustd(period.tstart, period.duration)
            actual_times[period.title] = (period.tstart.strftime("%H:%M"),
                                          endtime.strftime("%H:%M"))
        for period in model.originalPeriodsInDay(self.term, self.context,
                                                 self.date):
            # datetime authors are cowards
            endtime = self.timeplustd(period.tstart, period.duration)
            result.append((period.title,
                           period.tstart.strftime("%H:%M"),
                           endtime.strftime("%H:%M")) +
                          actual_times.get(period.title, ('', '')))
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

    template = None
    date_template = ViewPageTemplateFile('templates/emergency_select.pt')
    replacement_template = ViewPageTemplateFile('templates/emergency2.pt')

    error = None
    date = None
    replacement = None

    def replacements(self):
        """Return all non-schooldays in term plus 3 days after the term."""
        result = []
        for date in self.term:
            if date > self.date:
                if not self.term.isSchoolday(date):
                    result.append(date)
        last = self.term.last
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

            self.term = getTermForDate(self.date)
            if self.term is None:
                self.error = _("The date you entered does not"
                               " belong to any term.")
                return
            if not self.term.isSchoolday(self.date):
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
            if self.term.last < self.replacement:
                self.term.last = self.replacement
            assert not self.term.isSchoolday(self.replacement)
            assert self.term.isSchoolday(self.date)
            self.term.add(self.replacement)
            model = self.context.model
            exceptionDays = removeSecurityProxy(model.exceptionDays)
            exceptionDayIds = removeSecurityProxy(model.exceptionDayIds)
            exceptionDays[self.date] = SchooldayTemplate()
            day_id = model.getDayId(self.term, self.date)
            exceptionDayIds[self.replacement] = removeSecurityProxy(day_id)

            # XXX: post two all day events on self.date and self.replacement
            # calendar = getSchoolToolApplication().calendar
            # calendar.addEvent(
            #     CalendarEvent(datetime.combine(self.date, datetime.time(),
            #                   datetime.timedelta(),
            #                   _('School is cancelled'),
            #                   allday=True))
            # calendar.addEvent(
            #     CalendarEvent(datetime.combine(self.replacement,
            #                                    datetime.time(),
            #                   datetime.timedelta(),
            #                   translate(_('Replacement schoolday for'
            #                               ' emergency day %s'),
            #                             context=self.request)
            #                   % self.replacement,
            #                   allday=True))

            self.request.response.redirect(
                zapi.absoluteURL(self.context, self.request))



    def __call__(self):
        self.update()
        return self.template()
