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
Calendar overlays.

This module defines relationships used to remember calendar subscriptions.

    >>> from schoolbell.relationship.tests import setUp, tearDown
    >>> setUp()

We will need some sample persons and groups for the demonstration

    >>> from schoolbell.app.app import Person, Group
    >>> john = Person(title="John")
    >>> smith = Person(title="Smith")
    >>> developers = Group(title="Developers")

Let's say John wants to see the calendars of Smith and the Developers group
overlaid on his own calendar

    >>> john.overlaid_calendars.add(smith.calendar)
    >>> john.overlaid_calendars.add(developers.calendar)

    >>> for calendar in john.overlaid_calendars:
    ...     print calendar.__parent__.title
    Smith
    Developers

Clean up

    >>> tearDown()

"""

from schoolbell.relationship import URIObject


URICalendarSubscription = URIObject(
                "http://schooltool.org/ns/calendar_subscription",
                "Calendar subscription",
                "The calendar subscription relationship.")

URICalendarProvider = URIObject(
                "http://schooltool.org/ns/calendar_subscription/provider",
                "Calendar provider",
                "A role of an object providing a calendar.")

URICalendarSubscriber = URIObject(
                "http://schooltool.org/ns/calendar_subscription/subscriber",
                "Calendar subscriber",
                "A role of an object that subscribes to a calendar.")

