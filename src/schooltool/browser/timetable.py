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

import sets
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
            periods_for_day.append(periods)
            if longest_day is None or len(periods) > len(longest_day):
                longest_day = periods
            previous_day = periods

        if 'ADD_PERIOD' in self.request.args:
            longest_day.append(_('Period %d') % (len(longest_day) + 1))

        ttschema = Timetable(day_ids)
        for day, periods in zip(day_ids, periods_for_day):
            ttschema[day] = TimetableDay(periods)

        # TODO: ttschema.model = model
        return ttschema


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
