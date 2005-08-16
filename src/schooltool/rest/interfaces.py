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
SchoolTool restive view interfaces

$Id: interfaces.py 3798 2005-05-17 15:33:29Z gintas $
"""

from zope.interface import Interface
from zope.app.http.interfaces import INullResource


class ITimetableFileFactory(Interface):
    """A special interface fot a custom file factory that needs the request. """

    def __call__(name, content_type, data):
        """Create a timetable

        The file `name`, content `type`, `data` and `request` are provided to
        help create the object.
        """


class INullTimetable(INullResource):
    """Placeholder objects for new timetables to be created via PUT
    """


class ICompositeTimetables(Interface):
    """A marker interface used when traversing into composite timetables."""

    def getCompositeTimetable(term_id, tt_schema_id):
        """Return a composite timetable for a given object with a
        given timetable schema for a given time period id.

        The timetable returned includes the events from the timetables
        of parent groups, groups taught, etc.

        This function can return None if the object has no timetable.
        """

    def listCompositeTimetables():
        """Return a sequence of (time_period_id, tt_schema_id) for all
        available composite timetables.
        """
