#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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

from schooltool.browser import View, Template
from schooltool.browser import notFoundPage
from schooltool.browser.auth import PublicAccess
from schooltool.browser.auth import PrivateAccess
from schooltool.interfaces import ITimetabled
from schooltool.interfaces import ITimetable
from schooltool.translation import ugettext as _

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
        # XXX Refactor!  This method is identical to
        #     schooltool.rest.timetable.TimetableReadView.rows
        #     It also has no unit tests.
        rows = []
        for ncol, (id, day) in enumerate(self.context.items()):
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
        return rows
