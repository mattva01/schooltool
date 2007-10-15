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
"""Term Interfaces

$Id$
"""
__docformat__ = 'reStructuredText'
import zope.interface
import zope.schema

from zope.app.container import constraints
from zope.app.container.interfaces import IContainer, IContained
from zope.location.interfaces import ILocation

from schooltool.common import SchoolToolMessage as _
from schooltool.common import IDateRange


class ITerm(IDateRange, IContained):
    """A term is a set of school days inside a given date range."""
    constraints.containers('.ITermContainer')

    title = zope.schema.TextLine(
        title=_("Title"))

    def isSchoolday(date):
        """Return whether the date is a schoolday.

        Raises a ValueError if the date is outside of the term covered.
        """


class ITermWrite(zope.interface.Interface):
    """A term is a set of school days inside a given date range.

    This interface defines an term that can be modified.
    """

    def add(day):
        """Mark the day as a schoolday.

        Raises a ValueError if the date is outside of the term covered.
        """

    def remove(day):
        """Mark the day as a holiday.

        Raises a ValueError if the date is outside of the term covered.
        """

    def reset(first, last):
        """Change the term and mark all days as holidays.

        If first is later than last, a ValueError is raised.
        """

    def addWeekdays(*weekdays):
        """Mark that all days of week with a number in weekdays within the
        term will be schooldays.

        The numbering used is the same as one used by datetime.date.weekday()
        method, or the calendar module: 0 is Monday, 1 is Tuesday, etc.
        """

    def removeWeekdays(*weekdays):
        """Mark that all days of week with a number in weekdays within the
        term will be holidays.

        The numbering used is the same as one used by datetime.date.weekday()
        method, or the calendar module: 0 is Monday, 1 is Tuesday, etc.
        """

    def toggleWeekdays(*weekdays):
        """Toggle the state of all days of week with a number in weekdays.

        The numbering used is the same as one used by datetime.date.weekday()
        method, or the calendar module: 0 is Monday, 1 is Tuesday, etc.
        """


class ITermContainer(IContainer, ILocation):
    """A container for terms.

    It stores term calendars for registered term IDs.
    """
    constraints.contains(ITerm)

