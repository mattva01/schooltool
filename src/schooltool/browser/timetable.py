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
import cgi
import sets
import datetime

from schooltool.browser import View, Template
from schooltool.browser import notFoundPage
from schooltool.browser import valid_name
from schooltool.browser.auth import PublicAccess
from schooltool.browser.auth import PrivateAccess
from schooltool.browser.auth import ManagerAccess
from schooltool.browser.widgets import TextWidget
from schooltool.interfaces import ITimetabled
from schooltool.interfaces import ITimetable
from schooltool.interfaces import ITimetableSchemaService
from schooltool.interfaces import ITimePeriodService
from schooltool.interfaces import ISchooldayModel
from schooltool.translation import ugettext as _
from schooltool.timetable import Timetable, TimetableDay
from schooltool.timetable import SchooldayTemplate
from schooltool.timetable import SchooldayPeriod
from schooltool.cal import SchooldayModel
from schooltool.rest.timetable import format_timetable_for_presentation
from schooltool.common import to_unicode
from schooltool.common import parse_date
from schooltool.component import getTimetableModel
from schooltool.rest import absoluteURL

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


class TimetableSchemaView(TimetableView):
    """View for a timetable schema

    Can be accessed at /ttschemas/$schema.
    """

    authorization = ManagerAccess

    def __init__(self, context):
        TimetableView.__init__(self, context, None)

    def title(self):
        return "Timetable schema %s" % self.context.__name__


class TimetableSchemaWizard(View):
    """View for defining a new timetable schema.

    Can be accessed at /newttschema.
    """

    __used_for__ = ITimetableSchemaService

    authorization = ManagerAccess

    template = Template("www/ttwizard.pt")

    def do_GET(self, request):
        self.name_error = None
        if 'name' not in self.request.args:
            self.name = 'default'
        else:
            self.name = to_unicode(self.request.args.get('name')[0]).strip()
            if not self.name:
                self.name_error = _("Timetable schema name must not be empty")
            elif not valid_name(self.name):
                self.name_error = _("Timetable schema name can only contain"
                                    " English letters, numbers, and the"
                                    " following punctuation characters:"
                                    " - . , ' ( )")
            elif self.name in self.context.keys():
                self.name_error = _("Timetable schema with this name"
                                    " already exists.")

        self.model_error = None
        self.model_name = to_unicode(self.request.args.get('model', [None])[0])

        self.ttschema = self._buildSchema()
        self.day_templates = self._buildDayTemplates()

        if 'CREATE' in request.args:
            try:
                factory = getTimetableModel(self.model_name)
            except KeyError:
                self.model_error = _("Please select a value")
            if not self.name_error and not self.model_error:
                model = factory(self.ttschema.day_ids, self.day_templates)
                self.ttschema.model = model
                self.context[self.name] = self.ttschema
                return self.redirect("/ttschemas", request)
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
        result = {None: SchooldayTemplate()}
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



class TimePeriodViewBase(View):
    """Base class for time period views."""

    authorization = ManagerAccess

    template = Template("www/time-period.pt")

    def __init__(self, context):
        View.__init__(self, context)
        self.start_widget = TextWidget('start', _('Start date'),
                                       self.date_parser)
        self.end_widget = TextWidget('end', _('End date'),
                                     self.date_parser, self.end_date_validator)

    def date_parser(self, date):
        if date is None or not date.strip():
            return None
        try:
            return parse_date(date)
        except ValueError:
            raise ValueError(_("Invalid date.  Please specify YYYY-MM-DD."))

    def end_date_validator(self, date):
        if date is None or self.start_widget.value is None:
            return
        if date < self.start_widget.value:
            raise ValueError(_("End date cannot be earlier than start date."))

    def title(self):
        raise NotImplementedError('override this in subclasses')

    def _buildModel(self, request):
        first = self.start_widget.value
        last = self.end_widget.value
        if first is None or last is None or last < first:
            return None
        model = SchooldayModel(first, last)
        model.addWeekdays(0, 1, 2, 3, 4, 5, 6)
        for holiday in request.args.get('holiday', []):
            try:
                model.remove(parse_date(holiday))
            except ValueError:
                continue
        toggle = [n for n in range(7) if ('TOGGLE_%d' % n) in request.args]
        if toggle:
            model.toggleWeekdays(*toggle)
        return model

    def calendar(self):
        if self.model is None:
            return []
        calendar = []
        start_of_month = self.model.first
        limit = self.model.last + datetime.timedelta(1)
        index = 0
        while start_of_month < limit:
            month_title = _('%(month)s %(year)s') % {
                                'month': start_of_month.strftime('%B'),
                                'year': start_of_month.year
                            }
            weeks = []
            start_of_week = week_start(start_of_month)
            start_of_next_month = min(next_month(start_of_month), limit)
            while start_of_week < start_of_next_month:
                week_title = _('Week %d') % start_of_week.isocalendar()[1]
                days = []
                day = start_of_week
                for n in range(7):
                    if start_of_month <= day < start_of_next_month:
                        index += 1
                        checked = not self.model.isSchoolday(day)
                        if checked:
                            css_class = 'holiday'
                        else:
                            css_class = 'schoolday'
                        days.append({'number': day.day, 'class': css_class,
                                     'date': day.strftime('%Y-%m-%d'),
                                     'onclick': 'javascript:toggle(%d)'%index,
                                     'index': index,
                                     'checked': checked})
                    else:
                        days.append({'number': None, 'class': None,
                                     'date': None, 'checked': None,
                                     'index': None, 'onclick': None})
                    day += datetime.timedelta(1)
                weeks.append({'title': week_title,
                              'days': days})
                start_of_week += datetime.timedelta(7)
            calendar.append({'title': month_title, 'weeks': weeks})
            start_of_month = start_of_next_month
        return calendar


class TimePeriodView(TimePeriodViewBase):
    """View for editing a time period.

    Can be accessed at /time-periods/$period.
    """

    __used_for__ = ISchooldayModel

    def title(self):
        return _("Time period %s") % self.context.__name__

    def do_GET(self, request):
        self.status = None
        self.start_widget.update(request)
        self.end_widget.update(request)
        self.model = self._buildModel(request)
        if self.model is None:
            self.model = self.context
        if self.start_widget.value is None and self.start_widget.error is None:
            self.start_widget.setValue(self.context.first)
        if self.end_widget.value is None and self.end_widget.error is None:
            self.end_widget.setValue(self.context.last)
        if 'UPDATE' in request.args:
            self.start_widget.require()
            self.end_widget.require()
            if not (self.start_widget.error or self.end_widget.error):
                service = self.context.__parent__
                key = self.context.__name__
                self.context = self.model
                service[key] = self.context
                self.status = _("Saved changes.")
        return View.do_GET(self, request)


class NewTimePeriodView(TimePeriodViewBase):
    """View for defining a new time period.

    Can be accessed at /newtimeperiod.
    """

    template = Template("www/time-period.pt")

    def __init__(self, service):
        TimePeriodViewBase.__init__(self, None)
        self.service = service
        self.name_widget = TextWidget('name', _('Name'), self.name_parser,
                                      self.name_validator)

    def name_parser(self, name):
        if name is None:
            return None
        return name.strip()

    def name_validator(self, name):
        if name is None:
            return
        if not name:
            raise ValueError(_("Time period name must not be empty"))
        elif not valid_name(name):
            raise ValueError(_("Time period name can only contain"
                               " English letters, numbers, and the"
                               " following punctuation characters:"
                               " - . , ' ( )"))
        elif name in self.service.keys():
            raise ValueError(_("Time period with this name already exists."))

    def title(self):
        return _("New time period")

    def do_GET(self, request):
        self.status = None
        self.name_widget.update(request)
        self.start_widget.update(request)
        self.end_widget.update(request)
        self.model = self._buildModel(request)
        if 'CREATE' in request.args:
            self.name_widget.require()
            self.start_widget.require()
            self.end_widget.require()
            if not (self.name_widget.error or self.start_widget.error or
                    self.end_widget.error) and self.model is not None:
                self.service[self.name_widget.value] = self.model
                return self.redirect("/time-periods", request)
        return View.do_GET(self, request)

    def date_parser(self, date):
        if date is None:
            return None
        if not date.strip():
            raise ValueError(_("This field is required."))
        try:
            return parse_date(date)
        except ValueError:
            raise ValueError(_("Invalid date.  Please specify YYYY-MM-DD."))


class ContainerServiceViewBase(View):
    """A base view for timetable schema and time period services

    Subclasses must define:

    template  the page template for this view
    newpath   the path of the view for creating a new item.
    subview   the view for editing an item.
    """

    authorization = ManagerAccess

    def list(self):
        return map(self.context.__getitem__, self.context.keys())

    def _traverse(self, name, request):
        return self.subview(self.context[name])

    def update(self):
        result = None
        if 'DELETE' in self.request.args:
            for name in self.request.args['CHECK']:
                del self.context[name]
            result = _('Deleted %s.') % ", ".join(self.request.args['CHECK'])
        if 'ADD' in self.request.args:
            self.request.redirect(absoluteURL(self.request,
                                              self.context.__parent__,
                                              self.newpath))
        return result


class TimetableSchemaServiceView(ContainerServiceViewBase):

    template = Template("www/ttschemas.pt")

    newpath = '/newttschema'
    subview = TimetableSchemaView


class TimePeriodServiceView(ContainerServiceViewBase):

    template = Template("www/time-periods.pt")

    newpath = '/newtimeperiod'
    subview = TimePeriodView


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


def next_month(date):
    """Calculate the first day of the next month from date.

       >>> next_month(datetime.date(2004, 8, 1))
       datetime.date(2004, 9, 1)
       >>> next_month(datetime.date(2004, 8, 31))
       datetime.date(2004, 9, 1)
       >>> next_month(datetime.date(2004, 12, 15))
       datetime.date(2005, 1, 1)
       >>> next_month(datetime.date(2004, 2, 28))
       datetime.date(2004, 3, 1)
       >>> next_month(datetime.date(2004, 2, 29))
       datetime.date(2004, 3, 1)
       >>> next_month(datetime.date(2005, 2, 28))
       datetime.date(2005, 3, 1)

    """
    return (date.replace(day=28) + datetime.timedelta(7)).replace(day=1)


def week_start(date, first_day_of_week=0):
    """Calculate the first day of the week of date.

    Assuming that week starts on Mondays:

       >>> import calendar
       >>> week_start(datetime.date(2004, 8, 19))
       datetime.date(2004, 8, 16)
       >>> week_start(datetime.date(2004, 8, 15))
       datetime.date(2004, 8, 9)
       >>> week_start(datetime.date(2004, 8, 14))
       datetime.date(2004, 8, 9)
       >>> week_start(datetime.date(2004, 8, 21))
       datetime.date(2004, 8, 16)
       >>> week_start(datetime.date(2004, 8, 22))
       datetime.date(2004, 8, 16)
       >>> week_start(datetime.date(2004, 8, 23))
       datetime.date(2004, 8, 23)

    Assuming that week starts on Sundays:

       >>> import calendar
       >>> week_start(datetime.date(2004, 8, 19), calendar.SUNDAY)
       datetime.date(2004, 8, 15)
       >>> week_start(datetime.date(2004, 8, 15), calendar.SUNDAY)
       datetime.date(2004, 8, 15)
       >>> week_start(datetime.date(2004, 8, 14), calendar.SUNDAY)
       datetime.date(2004, 8, 8)
       >>> week_start(datetime.date(2004, 8, 21), calendar.SUNDAY)
       datetime.date(2004, 8, 15)
       >>> week_start(datetime.date(2004, 8, 22), calendar.SUNDAY)
       datetime.date(2004, 8, 22)
       >>> week_start(datetime.date(2004, 8, 23), calendar.SUNDAY)
       datetime.date(2004, 8, 22)

    """
    assert 0 <= first_day_of_week < 7
    delta = date.weekday() - first_day_of_week
    if delta < 0:
        delta += 7
    return date - datetime.timedelta(delta)

