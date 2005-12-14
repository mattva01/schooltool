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
Interfaces for SchoolTool calendar browser views.

$Id$
"""

from zope.schema import Object, Datetime, TextLine

from schooltool.calendar.interfaces import ICalendar, ICalendarEvent


class IEventForDisplay(ICalendarEvent):
    """A decorated calendar event.

    Calendar views have additional information that is not contained in event
    objects.
    """

    context = Object(
        title=u"The event being decorated",
        schema=ICalendarEvent)

    dtend = Datetime(
        title=u"End",
        readonly=True,
        description=u"""
        Date and time when the event ends.

        dtend == dtstart + duration
        """)

    dtstarttz = Datetime(
        title=u"Start (in user's timezone)",
        readonly=True,
        description=u"""
        Date and time when the event starts, converted to the user's preferred
        timezone.
        """)

    dtendtz = Datetime(
        title=u"End (in user's timezone)",
        readonly=True,
        description=u"""
        Date and time when the event ends, converted to the user's preferred
        timezone.
        """)

    source = Object(
        title=u"Source calendar",
        schema=ICalendar,
        description=u"""
        The calendar the event came from.  A view may display events from
        several overlaid calendars.
        """)

    color1 = TextLine(
        title=u"Color used for display (1)",
        description=u"""
        One of the two colors used to distinguish events coming form 
        sources.

        These two colors should contrast enough so that one can be used
        as text color when the other is used as a background color.

        This attribute contains a string usable as a CSS color value.
        """)

    color2 = TextLine(
        title=u"Color used for display (2)",
        description=u"""
        The other of the two colors used to distinguish events coming form
        sources.

        These two colors should contrast enough so that one can be used
        as text color when the other is used as a background color.

        This attribute contains a string usable as a CSS color value.
        """)

    shortTitle = TextLine(
        title=u"Short Title",
        description=u"""The title of the event, ellipsized if necessary.""")

    cssClass = TextLine(
        title=u"CSS Class",
        description=u"""
        Suggested event class name.  Currently it is always 'event'.
        """)

