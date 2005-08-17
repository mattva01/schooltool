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
SchoolTool application interfaces

$Id$
"""
import zope.interface

from schooltool import SchoolToolMessageID as _

# Those interfaces are imported here, since they will later actually move here.
from schoolbell.app.interfaces import \
     ISchoolBellApplication as ISchoolToolApplication
from schoolbell.app.interfaces import IApplicationInitializationEvent
from schoolbell.app.interfaces import ApplicationInitializationEvent
from schoolbell.app.interfaces import IApplicationPreferences


class IShowTimetables(zope.interface.Interface):
    """Adapter to flag whether to show timetables in the calendar overlay."""

    showTimetables = zope.schema.Bool(
            title=_("Show timetables"),
            description=_("""
            An option that controls whether the timetable of this calendar's
            owner is shown in the calendar views.
            """))
