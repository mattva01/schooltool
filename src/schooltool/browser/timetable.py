#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Web-application views for the schooltool.timetable objects.

$Id$
"""

import re
import sets
import datetime
from schooltool.browser import View, Template
from schooltool.browser import notFoundPage
from schooltool.browser.auth import PublicAccess
from schooltool.browser.auth import PrivateAccess
from schooltool.browser.auth import ManagerAccess
from schooltool.interfaces import ITimetabled
from schooltool.interfaces import ITimetable
from schooltool.interfaces import ITimetableSchemaService
from schooltool.translation import ugettext as _
from schooltool.timetable import Timetable, TimetableDay
from schooltool.timetable import SchooldayTemplate
from schooltool.timetable import SchooldayPeriod
from schooltool.rest.timetable import format_timetable_for_presentation
from schooltool.common import to_unicode

__metaclass__ = type


class TimetableTraverseView(View):
    """View for traversing (composite) timetables.

    Can be accessed at /persons/$id/timetables.

    Allows accessing the timetable view at .../timetables/$period/$schema
    """

    __used_for__ = ITimetabled

    authorization = PublicAccess

    do_GET = staticmethod(notFoundPage)

    def __init__(self, context, period=None):
        View.__init__(self, context)
        self.period = period

    def _traverse(self, name, request):
        if self.period is None:
            return TimetableTraverseView(self.context, name)
        else:
            tt = self.context.getCompositeTimetable(self.period, name)
            if tt is None:
                raise KeyError(self.period, name)
            return TimetableView(tt, (self.period, name))


class TimetableView(View):
    """View for a timetable.

    Can be accessed at /persons/$id/timetables/$period/$schema.
    """

    __used_for__ = ITimetable

    authorization = PrivateAccess

    template = Template("www/timetable.pt")

    def __init__(self, context, key):
        View.__init__(self, context)
        self.key = key

    def title(self):
        timetabled = self.context.__parent__.__parent__
        return _("%s's timetable for %s") % (timetabled.title,
                                             ", ".join(self.key))

    def rows(self):
        return format_timetable_for_presentation(self.context)


class TimetableSchemaWizard(View):
    """View for defining a timetable schema.

    XXX can be accessed at /TEST/tt (for now, while debugging).
    """

    __used_for__ = ITimetableSchemaService

    authorization = ManagerAccess

    template = Template("www/ttwizard.pt")

    def do_GET(self, request):
        self.ttschema = self._buildSchema()
        self.model_name = self.request.args.get('model', [None])[0]
        # TODO: verify if model_name is OK and display the dreaded red border
        self.day_templates = self._buildDayTemplates()
        # TODO: actual schema creation
        return View.do_GET(self, request)

    def rows(self):
        return format_timetable_for_presentation(self.ttschema)

    def _buildSchema(self):
        """Built a timetable schema from data contained in the request."""
        n = 1
        day_ids = []
        day_idxs = []
        while 'day%d' % n in self.request.args:
            if 'DELETE_DAY_%d' % n not in self.request.args:
                day_id = to_unicode(self.request.args['day%d' % n][0]).strip()
                if not day_id:
                    day_id = _('Day %d' % (len(day_ids) + 1))
                day_ids.append(day_id)
                day_idxs.append(n)
            n += 1
        if 'ADD_DAY' in self.request.args or not day_ids:
            day_ids.append(_('Day %d' % (len(day_ids) + 1)))
            day_idxs.append(-1)
        day_ids = fix_duplicates(day_ids)

        periods_for_day = []
        longest_day = None
        previous_day = None
        for idx, day in zip(day_idxs, day_ids):
            n = 1
            if ('COPY_DAY_%d' % idx in self.request.args
                and previous_day is not None):
                periods = list(previous_day)
            else:
                periods = []
                while 'day%d.period%d' % (idx, n) in self.request.args:
                    raw_value = self.request.args['day%d.period%d' % (idx, n)]
                    periods.append(to_unicode(raw_value[0]).strip())
                    n += 1
                periods = filter(None, periods)
                if not periods:
                    periods = [_('Period 1')]
                else:
                    periods = fix_duplicates(periods)
            periods_for_day.append(periods)
            if longest_day is None or len(periods) > len(longest_day):
                longest_day = periods
            previous_day = periods

        if 'ADD_PERIOD' in self.request.args:
            longest_day.append(_('Period %d') % (len(longest_day) + 1))

        ttschema = Timetable(day_ids)
        for day, periods in zip(day_ids, periods_for_day):
            ttschema[day] = TimetableDay(periods)

        return ttschema

    def _buildDayTemplates(self):
        """Built a dict of day templates from data contained in the request.

        The dict is suitable to be passed as the second argument to the
        timetable model factory.
        """
        result = {}
        n = 1
        while 'time%d.period' % n in self.request.args:
            raw_value = self.request.args['time%d.period' % n][0]
            period = to_unicode(raw_value).strip()
            for day in range(7):
                raw_value = self.request.args.get('time%d.day%d' % (n, day),
                                                  [''])[0]
                value = to_unicode(raw_value).strip()
                if not value:
                    continue
                try:
                    start, duration = parse_time_range(value)
                except ValueError:
                    # ignore invalid values for now
                    continue
                if day not in result:
                    result[day] = SchooldayTemplate()
                result[day].add(SchooldayPeriod(period, start, duration))
            n += 1
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


def parse_time_range(value):
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

    Invalid values cause a ValueError

        >>> parse_time_range('something else')
        Traceback (most recent call last):
          ...
        ValueError: bad time range: something else

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
    m = re.match(r'\s*(\d+):(\d+)\s*-\s*(\d+):(\d+)\s*$', value)
    if not m:
        raise ValueError('bad time range: %s' % value)
    h1, m1, h2, m2 = map(int, m.groups())
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

