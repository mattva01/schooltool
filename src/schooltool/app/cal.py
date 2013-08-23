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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
BBB imports of objects/interfaces moved to schooltool.calendar.
"""

# XXX: BBB imports for stored ZODB objects

from schooltool.calendar.app import CalendarEvent
from schooltool.calendar.app import Calendar
from schooltool.calendar.app import WriteCalendar

# XXX: misplaced calendar integration

from schooltool.calendar.app import getCalendar
from schooltool.calendar.app import clearCalendarOnDeletion
from schooltool.calendar.app import expandedEventLocation
from schooltool.calendar.app import CALENDAR_KEY
from schooltool.calendar.interfaces import ISchoolToolCalendarEvent
from schooltool.calendar.interfaces import ISchoolToolCalendar
from schooltool.calendar.interfaces import IWriteCalendar
from schooltool.calendar.interfaces import IHaveCalendar
