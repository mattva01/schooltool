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
import itertools

from schooltool.browser import AppObjectBreadcrumbsMixin
from schooltool.browser import notFoundPage, ToplevelBreadcrumbsMixin
from schooltool.browser import View, Template
from schooltool.browser import valid_name
from schooltool.browser.auth import ManagerAccess, PrivateAccess, PublicAccess
from schooltool.browser.cal import next_month, week_start
from schooltool.browser.widgets import SelectionWidget, TextWidget
from schooltool.browser.widgets import dateParser, intParser
from schooltool.cal import SchooldayModel
from schooltool.common import to_unicode, parse_date
from schooltool.component import getPath, traverse
from schooltool.component import getTimePeriodService
from schooltool.component import getTimetableModel, getTimetableSchemaService
from schooltool.interfaces import IApplication, IApplicationObject, IPerson
from schooltool.interfaces import ITimetableSchemaService, ISchooldayModel
from schooltool.interfaces import ITimetabled, ITimetable
from schooltool.membership import Membership, memberOf
from schooltool.rest import absoluteURL
from schooltool.rest.timetable import format_timetable_for_presentation
from schooltool.timetable import SchooldayTemplate, SchooldayPeriod
from schooltool.timetable import Timetable, TimetableDay
from schooltool.translation import ugettext as _
from schooltool.uris import URIGroup

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
                periods = getTimePeriodService(self.context).keys()
                schemas = getTimetableSchemaService(self.context).keys()
                if self.period not in periods or name not in schemas:
                    raise KeyError(self.period, name)
                else:
                    return NoTimetableView(self.context, (self.period, name))
            return TimetableView(tt, (self.period, name))


class NoTimetableView(View):
    """View for a nonexistent timetable.

    Can be accessed at /persons/$id/timetables/$period/$schema.
    """

    __used_for__ = ITimetabled

    authorization = PublicAccess

    do_GET = staticmethod(notFoundPage)

    def __init__(self, context, key):
        View.__init__(self, context)
        self.key = key

    def _traverse(self, name, request):
        if name == 'setup.html' and IPerson.providedBy(self.context):
            return TimetableSetupView(self.context, self.key)
        else:
            raise KeyError(name)


class TimetableView(View, AppObjectBreadcrumbsMixin):
    """View for a timetable.

    Can be accessed at /persons/$id/timetables/$period/$schema.
    """

    __used_for__ = ITimetable

    authorization = PrivateAccess

    template = Template("www/timetable.pt")

    def __init__(self, context, key):
        View.__init__(self, context)
        self.key = key

    def breadcrumbs(self):
        owner = self.context.__parent__.__parent__
        breadcrumbs = AppObjectBreadcrumbsMixin.breadcrumbs(self,
                                                            context=owner)
        name = self.context.__name__
        breadcrumbs.append((_('Timetable for %s, %s') % name,
                            self.request.uri))
        return breadcrumbs

    def title(self):
        timetabled = self.context.__parent__.__parent__
        return _("%s's timetable for %s") % (timetabled.title,
                                             ", ".join(self.key))

    def rows(self):
        return format_timetable_for_presentation(self.context)

    def canEdit(self):
        # RESTive timetable views only allow managers to change timetables
        return self.isManager()

    def do_POST(self, request):
        if not self.canEdit():
            return self.do_GET(request)
        for exc in self._exceptionsToRemove(request):
            tt = exc.activity.timetable
            tt.exceptions.remove(exc)
        # Cannot just call do_GET here, because self.context is most likely a
        # composite timetable that needs to be regenerated.
        return self.redirect(request.uri, request)

    def _exceptionsToRemove(self, request):
        """Generator for timetable exceptions that need to be removed.

        Yields ITimetableException objects from self.context.exceptions
        if the matching REMOVE.%d field is found in the request.
        """
        for arg in self.request.args:
            if arg.startswith('REMOVE.'):
                try:
                    idx = int(arg[len('REMOVE.'):])
                    if 1 <= idx <= len(self.context.exceptions):
                        yield self.context.exceptions[idx - 1]
                except (ValueError, IndexError):
                    pass # Ignore hacking attempts and obsolete forms

    def _traverse(self, name, request):
        timetabled = self.context.__parent__.__parent__
        if name == 'setup.html' and IPerson.providedBy(timetabled):
            return TimetableSetupView(timetabled, self.key)
        else:
            raise KeyError(name)


class TimetableSetupView(View, AppObjectBreadcrumbsMixin):
    """Timetable set up view.

    Shows a web form with a drop-down box for every timetable period.
    Each drop-down box contains a list of groups that have activities
    during that time period.  If the person belongs to any of those groups,
    then they are selected in the appropriate drop-down boxes.  When
    the form is submitted, the person is added to and removed from groups
    according to the choices made in this form.

    Can be accessed at /persons/$id/timetables/$period/$schema/setup.html
    """

    __used_for__ = IApplicationObject

    authorization = ManagerAccess

    template = Template("www/timetable-setup.pt")

    def __init__(self, context, key):
        """Create the view.

        `context` is an application object (normally IPerson).

        `key` is a tuple (period_id, schema_id) identifying a timetable.
        """
        View.__init__(self, context)
        self.key = key

    def breadcrumbs(self):
        breadcrumbs = AppObjectBreadcrumbsMixin.breadcrumbs(self,
                                                    context=self.context)
        breadcrumbs.append((_('Timetable for %s, %s') % self.key,
                            self.request.uri))
        return breadcrumbs

    def title(self):
        """Return the title of the page."""
        return _("%s's timetable setup (%s)") % (self.context.title,
                                                 ", ".join(self.key))

    def schema(self):
        """Return the timetable schema for self.key."""
        period_id, schema_id = self.key
        return getTimetableSchemaService(self.context)[schema_id]

    def groupMap(self):
        """Compute a mapping timetable periods to groups that have activities.

        Returns a dict {(day_id, period_id): [group]}.  The list for each
        period contains all groups in the system that have activities in the
        (non-composite) timetable during that timetable period.
        """
        schema = self.schema()
        group_map = {}
        for day_id, day in schema.items():
            for period_id in day.periods:
                group_map[day_id, period_id] = sets.Set()
        for group in traverse(self.context, '/groups').itervalues():
            timetable = group.timetables.get(self.key)
            if timetable:
                for day_id, period_id, activity in timetable.itercontent():
                    group_map[day_id, period_id].add(group)
        return group_map

    def allGroups(self, group_map):
        """Return a set of all groups that can be selected."""
        groups = sets.Set()
        for groupset in group_map.itervalues():
            groups.update(groupset)
        return groups

    def createForm(self, group_map):
        """Return a list of timetable days containing form widgets.

        Returns a list of dicts with the following keys:

            'title' -- timetable day name
            'periods' -- a list of periods in this day

        Each period in a day is represented by a dict with the following keys:

            'title' -- period name
            'widgets' -- a list of drop-down widgets

        Each drop-down box lists all groups that have activities during this
        timetable period, and also "None" as an additional choice.  There is
        at least one widget for every period.  More than one widget appear
        only when there are scheduling conflicts.

        """
        idx = itertools.count(1)
        all_widgets = []

        def days(schema):
            for day_id, day in schema.items():
                yield {'title': day_id,
                       'periods': list(periods(day_id, day))}

        def periods(day_id, day):
            for period_id in day.periods:
                choices = [(group.title, group)
                           for group in group_map[day_id, period_id]]
                choices.sort()
                choices = [(value, title) for title, value in choices]
                selected = [group for group, title in choices
                            if memberOf(self.context, group)]
                if not selected:
                    selected = [None]
                widgets = []
                for value in selected:
                    widget = SelectionWidget('g%d' % idx.next(), '',
                                             [(None, _('None'))] + choices,
                                             value=value,
                                             parser=self.groupParser,
                                             formatter=self.groupFormatter)
                    widgets.append(widget)
                    all_widgets.append(widget)
                yield {'title': period_id,
                       'widgets': widgets}

        return list(days(self.schema())), all_widgets

    def groupParser(self, raw_value):
        """Convert a group name from the HTML form to a group object."""
        if raw_value:
            try:
                group = traverse(self.context, '/groups/%s' % raw_value)
            except KeyError:
                pass
            else:
                if group in self.all_groups:
                    return group
        return None

    def groupFormatter(self, value):
        """Convert a group object to a group name for the HTML form."""
        if value is None:
            return ''
        else:
            return value.__name__

    def getSelectedGroups(self):
        """Return a set of groups that are selected in all the widgets.

        If you call this method before calling widget.update(request) for
        all the widgets, you will get the old set of groups -- i.e. those
        groups that self.context is a member of.

        If you call this method after calling widget.update(request) for
        all the widgets, you will get the new set of groups -- i.e. those
        groups that the user indicated that self.context should be a member of.
        """
        groups = sets.Set()
        for widget in self.widgets:
            if widget.value is not None:
                groups.add(widget.value)
        return groups

    def do_GET(self, request):
        """Process the request.

        Sets the following attributes on self:

            `all_groups` -- a set of all groups that can be selected in widgets
            (used for validation in `groupParser`).

            `days` -- structural representation of the form for the page
            template.

            `widgets` -- a list of all form widgets.

        If 'SAVE' is present in the request arguments, the view adds and
        removes self.context to/from groups as indicated in the form.
        """
        group_map = self.groupMap()
        self.all_groups = self.allGroups(group_map)
        self.days, self.widgets = self.createForm(group_map)
        old_groups = self.getSelectedGroups()
        errors = False
        for widget in self.widgets:
            widget.update(request)
            if widget.error:
                errors = True
        if 'SAVE' in request.args and not errors:
            new_groups = self.getSelectedGroups()
            for group in old_groups - new_groups:
                self._removeFromGroup(group)
            for group in new_groups - old_groups:
                self._addToGroup(group)
            self.days, self.widgets = self.createForm(group_map)
        return View.do_GET(self, request)

    def _addToGroup(self, group):
        """Add self.context to `group`.

        No exception is raised if self.context is already a member of `group`.
        """
        try:
            Membership(group=group, member=self.context)
        except ValueError:
            pass
        else:
            request = self.request
            request.appLog(_("Relationship '%s' between %s and %s created")
                           % (_('Membership'), getPath(self.context),
                              getPath(group)))

    def _removeFromGroup(self, group):
        """Remove self.context from `group`.

        No exception is raised if self.context is not a member of `group`.
        """
        for link in self.context.listLinks(URIGroup):
            if link.traverse() is group:
                link.unlink()
                request = self.request
                request.appLog(_("Relationship '%s' between %s and %s"
                                 " removed")
                               % (_('Membership'), getPath(self.context),
                                  getPath(group)))
                break


class TimetableSchemaView(TimetableView):
    """View for a timetable schema

    Can be accessed at /ttschemas/$schema.
    """

    authorization = ManagerAccess

    def breadcrumbs(self):
        app = traverse(self.context, '/')
        name = self.context.__name__
        return [
            (_('Start'), absoluteURL(self.request, app, 'start')),
            (_('Timetable schemas'),
             absoluteURL(self.request, app, 'ttschemas')),
            (name, absoluteURL(self.request, app, 'ttschemas/%s' % name))]

    def __init__(self, context):
        TimetableView.__init__(self, context, None)

    def title(self):
        return "Timetable schema %s" % self.context.__name__


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


class TimetableSchemaWizard(View, TabindexMixin):
    """View for defining a new timetable schema.

    Can be accessed at /newttschema.
    """

    __used_for__ = ITimetableSchemaService

    authorization = ManagerAccess

    template = Template("www/ttwizard.pt")

    days_of_week = (_("Monday"),
                    _("Tuesday"),
                    _("Wednesday"),
                    _("Thursday"),
                    _("Friday"),
                    _("Saturday"),
                    _("Sunday"),
                   )

    def __init__(self, context):
        View.__init__(self, context)
        TabindexMixin.__init__(self)
        self.name_widget = TextWidget('name', _('Name'), self.name_parser,
                                      self.name_validator,
                                      tabindex=self.next_tabindex())
        self.duration_widget = TextWidget('duration', _('Duration'),
                                          unit=_('minutes (used if you do not'
                                                 ' specify the ending time'
                                                 ' explicitly)'),
                                          css_class='narrow',
                                          parser=intParser,
                                          validator=self.duration_validator)

    def name_parser(name):
        """Strip whitespace from names.

          >>> name_parser = TimetableSchemaWizard.name_parser
          >>> name_parser(None)
          >>> name_parser('  ')
          ''
          >>> name_parser(' default ')
          'default'

        """
        if name is None:
            return None
        return name.strip()
    name_parser = staticmethod(name_parser)

    def name_validator(self, name):
        if name is None:
            return
        if not name:
            raise ValueError(_("Timetable schema name must not be empty"))
        elif not valid_name(name):
            raise ValueError(_("Timetable schema name can only contain"
                               " English letters, numbers, and the"
                               " following punctuation characters:"
                               " - . , ' ( )"))
        elif name in self.context.keys():
            raise ValueError(_("Timetable schema with this name already"
                               " exists."))

    def duration_validator(value):
        """Check if duration is acceptable.

          >>> duration_validator = TimetableSchemaWizard.duration_validator
          >>> duration_validator(None)
          >>> duration_validator(42)
          >>> duration_validator(0)
          >>> duration_validator(1440)
          >>> duration_validator(-1)
          Traceback (most recent call last):
            ...
          ValueError: Duration cannot be negative
          >>> duration_validator(1441)
          Traceback (most recent call last):
            ...
          ValueError: Duration cannot be longer than 24 hours

        """
        if value is None:
            return
        if value < 0:
            raise ValueError(_("Duration cannot be negative"))
        if value > 24 * 60:
            raise ValueError(_("Duration cannot be longer than 24 hours"))
    duration_validator = staticmethod(duration_validator)

    def do_GET(self, request):
        self.name_widget.update(request)
        if self.name_widget.value is None and self.name_widget.error is None:
            self.name_widget.raw_value = 'default'
            self.name_widget.value = 'default'
        self.duration_widget.update(request)

        # We could build a custom widget for the model radio buttons, but I do
        # not think it is worth the trouble.
        self.model_error = None
        try:
            raw_value = self.request.args.get('model', [None])[0]
            self.model_name = to_unicode(raw_value)
        except UnicodeError:
            self.model_name = None
            self.model_error = _("Invalid UTF-8 data.")

        self.ttschema = self._buildSchema()
        self.day_templates = self._buildDayTemplates()

        if 'CREATE' in request.args:
            try:
                factory = getTimetableModel(self.model_name)
            except KeyError:
                self.model_error = _("Please select a value")
            if not self.name_widget.error and not self.model_error:
                model = factory(self.ttschema.day_ids, self.day_templates)
                self.ttschema.model = model
                key = self.name_widget.value
                self.context[key] = self.ttschema
                request.appLog(_("Timetable schema %s created") %
                               getPath(self.context[key]))
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
                try:
                    raw_value = self.request.args['day%d' % n][0]
                    day_id = to_unicode(raw_value).strip()
                except UnicodeError:
                    day_id = None
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
            if ('COPY_DAY_%d' % (idx - 1) in self.request.args
                and previous_day is not None):
                periods = list(previous_day)
            else:
                periods = []
                while 'day%d.period%d' % (idx, n) in self.request.args:
                    raw_value = self.request.args['day%d.period%d' % (idx, n)]
                    try:
                        periods.append(to_unicode(raw_value[0]).strip())
                    except UnicodeError:
                        pass
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
        default_duration = self.duration_widget.value
        result = {None: SchooldayTemplate()}
        n = 1
        self.discarded_some_periods = False
        while 'time%d.period' % n in self.request.args:
            raw_value = self.request.args['time%d.period' % n][0]
            try:
                period = to_unicode(raw_value).strip()
            except UnicodeError:
                n += 1
                continue
            for day in range(7):
                raw_value = self.request.args.get('time%d.day%d' % (n, day),
                                                  [''])[0]
                try:
                    value = to_unicode(raw_value).strip()
                except UnicodeError:
                    continue
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
            if 'COPY_PERIODS_%d' % day in self.request.args:
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

    def breadcrumbs(self):
        app = traverse(self.context, '/')
        name = self.context.__name__
        return [
            (_('Start'), absoluteURL(self.request, app, 'start')),
            (_('Timetable schemas'),
             absoluteURL(self.request, app, 'ttschemas'))]


class TimePeriodViewBase(View):
    """Base class for time period views."""

    authorization = ManagerAccess

    template = Template("www/time-period.pt")

    # Which day is considered to be the first day of the week (0 = Monday,
    # 6 = Sunday).  Currently hardcoded.  A similair value is also hardcoded
    # in schooltool.browser.cal
    first_day_of_week = 0

    month_names = {
        1: _("January"),
        2: _("February"),
        3: _("March"),
        4: _("April"),
        5: _("May"),
        6: _("June"),
        7: _("July"),
        8: _("August"),
        9: _("September"),
        10: _("October"),
        11: _("November"),
        12: _("December"),
    }

    def __init__(self, context):
        View.__init__(self, context)
        self.start_widget = TextWidget('start', _('Start date'), dateParser)
        self.end_widget = TextWidget('end', _('End date'), dateParser,
                                     self.end_date_validator)

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
                              'month': self.month_names[start_of_month.month],
                              'year': start_of_month.year}
            weeks = []
            start_of_week = week_start(start_of_month, self.first_day_of_week)
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

    def breadcrumbs(self):
        app = traverse(self.context, '/')
        name = self.context.__name__
        return [
            (_('Start'), absoluteURL(self.request, app, 'start')),
            (_('Timetable periods'),
             absoluteURL(self.request, app, 'time-periods')),
            (name,
             absoluteURL(self.request, app, 'time-periods/%s' % name))]

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
                service[key] = self.model
                self.context = service[key]
                request.appLog(_("Time period %s updated") %
                               getPath(self.context))
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

    def breadcrumbs(self):
        app = traverse(self.service, '/')
        return [
            (_('Start'), absoluteURL(self.request, app, 'start')),
            (_('Timetable periods'), absoluteURL(self.request, self.service))]

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
        if 'NEXT' in request.args or 'CREATE' in request.args:
            self.name_widget.require()
            self.start_widget.require()
            self.end_widget.require()
        if 'CREATE' in request.args:
            if not (self.name_widget.error or self.start_widget.error or
                    self.end_widget.error) and self.model is not None:
                key = self.name_widget.value
                self.service[key] = self.model
                request.appLog(_("Time period %s created") %
                               getPath(self.service[key]))
                return self.redirect("/time-periods", request)
        return View.do_GET(self, request)


class ContainerServiceViewBase(View, ToplevelBreadcrumbsMixin):
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
            deleted = []
            for name in self.request.args.get('CHECK', []):
                try:
                    self.logDeletion(self.context[name])
                    del self.context[name]
                    deleted.append(name)
                except KeyError:
                    pass
            if deleted:
                result = _('Deleted %s.') % ", ".join(deleted)
        if 'ADD' in self.request.args:
            self.request.redirect(absoluteURL(self.request,
                                              self.context.__parent__,
                                              self.newpath))
        return result


class TimetableSchemaServiceView(ContainerServiceViewBase):
    """View for the timetable schema service."""

    template = Template("www/ttschemas.pt")

    newpath = '/newttschema'
    subview = TimetableSchemaView

    def logDeletion(self, schema):
        self.request.appLog(_("Timetable schema %s deleted") % getPath(schema))

    def breadcrumbs(self):
        app = traverse(self.context, '/')
        name = self.context.__name__
        return [
            (_('Start'), absoluteURL(self.request, app, 'start')),
            (_('Timetable schemas'), absoluteURL(self.request, app,
                                                 'ttschemas'))]


class TimePeriodServiceView(ContainerServiceViewBase):
    """View for the time period service."""

    template = Template("www/time-periods.pt")

    newpath = '/newtimeperiod'
    subview = TimePeriodView

    def logDeletion(self, period):
        self.request.appLog(_("Time period %s deleted") % getPath(period))

    def breadcrumbs(self):
        app = traverse(self.context, '/')
        name = self.context.__name__
        return [(_('Start'), absoluteURL(self.request, app, 'start')),
                (_('Time periods'), absoluteURL(self.request, app,
                                                'time-periods'))]


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

