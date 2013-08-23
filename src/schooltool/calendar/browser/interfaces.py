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
Interfaces for SchoolTool calendar browser views.
"""

import zope.schema
from zope.interface import Interface

from schooltool.calendar.interfaces import ICalendar, ICalendarEvent
from schooltool.common import IDateRange


class IEventForDisplay(ICalendarEvent):
    """A decorated calendar event.

    Calendar views have additional information that is not contained in event
    objects.
    """

    context = zope.schema.Object(
        title=u"The event being decorated",
        schema=ICalendarEvent)

    dtend = zope.schema.Datetime(
        title=u"End",
        readonly=True,
        description=u"""
        Date and time when the event ends.

        dtend == dtstart + duration
        """)

    dtstarttz = zope.schema.Datetime(
        title=u"Start (in user's timezone)",
        readonly=True,
        description=u"""
        Date and time when the event starts, converted to the user's preferred
        timezone.
        """)

    dtendtz = zope.schema.Datetime(
        title=u"End (in user's timezone)",
        readonly=True,
        description=u"""
        Date and time when the event ends, converted to the user's preferred
        timezone.
        """)

    source = zope.schema.Object(
        title=u"Source calendar",
        schema=ICalendar,
        description=u"""
        The calendar the event came from.  A view may display events from
        several overlaid calendars.
        """)

    parent_view_link = zope.schema.TextLine(
        title=u"View link",
        description=u"""Link to the view which displays this event""")

    color1 = zope.schema.TextLine(
        title=u"Color used for display (1)",
        description=u"""
        One of the two colors used to distinguish events coming form
        sources.

        These two colors should contrast enough so that one can be used
        as text color when the other is used as a background color.

        This attribute contains a string usable as a CSS color value.
        """)

    color2 = zope.schema.TextLine(
        title=u"Color used for display (2)",
        description=u"""
        The other of the two colors used to distinguish events coming form
        sources.

        These two colors should contrast enough so that one can be used
        as text color when the other is used as a background color.

        This attribute contains a string usable as a CSS color value.
        """)

    shortTitle = zope.schema.TextLine(
        title=u"Short Title",
        description=u"""The title of the event, ellipsized if necessary.""")

    cssClass = zope.schema.TextLine(
        title=u"CSS Class",
        description=u"""
        Suggested event class name.  Currently it is always 'event'.
        """)


class IHaveEventLegend(Interface):
    """Classes implementing this interface will have an event legend showing."""

    cursor = zope.schema.Date(
        title=u"Cursor",
        readonly=True,
        description=u"Current date",
        required=False)

    cursor_range = zope.schema.Object(
        title=u"Dates the view spans.",
        readonly=True,
        schema=IDateRange,
        required=False)
