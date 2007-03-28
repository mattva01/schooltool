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
Resource Booking caledar and events

$Id$
"""
from zope.interface import implements
from zope.component import queryAdapter
from zope.publisher.interfaces import NotFound

from schooltool.calendar.simple import ImmutableCalendar
from schooltool.traverser.traverser import NameTraverserPlugin

from lyceum.interfaces import IGroupTimetableCalendar


class GroupTimetableCalendar(ImmutableCalendar):
    implements(IGroupTimetableCalendar)

    def __init__(self, context):
        self.context = context
        self.__parent__ = self.context
        self.__name__ = 'tt_calendar'
        self.title = "Timetable Calendar"


class GroupTimetableCalendarTraverserPlugin(NameTraverserPlugin):
    """Traverse to an adapter by name."""

    traversalName = 'tt_calendar'

    def _traverse(self, request, name):
        timetableCalendar = queryAdapter(self.context, IGroupTimetableCalendar)
        if timetableCalendar is None:
            raise NotFound(self.context, name, request)

        timetableCalendar.request = request
        return timetableCalendar
