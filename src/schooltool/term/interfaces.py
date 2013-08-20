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
"""Term Interfaces
"""
__docformat__ = 'reStructuredText'

import zope.schema
from zope.container.constraints import contains, containers
from zope.container.interfaces import IContainer
from zope.location.interfaces import ILocation, IContained
from zope.interface import Interface, Attribute

from schooltool.common import SchoolToolMessage as _
from schooltool.common import IDateRange


class ITerm(IDateRange, IContained):
    """A term is a set of school days inside a given date range."""
    containers('.ITermContainer')

    __name__ = zope.schema.TextLine(
        title=_("SchoolTool ID"),
        description=_(
            """An internal identifier of this term."""),
        required=True)

    title = zope.schema.TextLine(
        title=_("Title"))

    def isSchoolday(date):
        """Return whether the date is a schoolday.

        Raises a ValueError if the date is outside of the term covered.
        """


class ITermWrite(Interface):
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
    contains(ITerm)


class IDateManager(Interface):
    """A class that handles dates and time.

    It does so taking the preferred timezone into account.
    """

    today = zope.schema.Date(
        title=u"Today",
        description=u"""The current day.""",
        required=True)

    current_term = Attribute("The active term.")


class TermDateNotInSchoolYear(Exception):

    def __repr__(self):
        return "Dates do not fit in school year!"

    __str__ = __repr__


