#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Resource booking in SchoolTool
==============================

Resources are things like projectors, and also locations (e.g. classrooms).  In
SchoolTool, resources are represented as application objects, and therefore can
be organized in groups, can participate in relationships with other object, and
have timetables and calendars.

Resource timetables and calendars indicate when the resource is busy.  When a
person books a resource, a calendar event is added to both the person's
calendar and the resource's calendar to indicate that the resource is busy
during that time.  When a timetable activity with possibly several resources
is added to a person's or a group's timetable, the same activity is also added
to the timetables of each of the resources needed for that activity, to
indicate that the resources are busy during that period.

Timetables
----------

For every timetable activity `act` the following is true:

  - act.owner is not a resource

  - act is present in the following timetables, and only the following
    timetables (not counting composite timetables):
      * a timetable of act.owner (act.timetable, to be precise)
      * timetables of each resource in act.resources (and all those
        timetables have the same key as act.timetable)
      * any composite timetables

  - for all timetables that act is present in, the list of timetable
    exceptions that pertain to act is exactly the same.

This module is responsible for maintaining these invariants.  The invariants
can be broken when an activity is added or removed from a timetable, or when
a timetable exception is added/removed/modified, therefore we have event
handlers watching for those changes and fixing broken invariants.

The event handler is hooked up in schooltool.app.create_application.


Calendaring
-----------

Resource booking creates a calendar event and adds it to two calendars at
once -- to the calendar of the person who booked the resource, and to the
calendar of the resource.

ICalendarEvent contains two attributes that are only defined for these
special resource-booking events:

  - `owner` is a reference to the person who booked the resource

  - `context` is a reference to the resource that was booked

TODO: Add a new type of event, IResourceBookingEvent, that defines those
attributes, and remove them from regular calendar events.

Calendar.removeEvent has special hooks that remove the event from both
calendars if you try to remove it from either of them.

TODO: Move the special code to this module.


$Id$
"""

from zope.interface import implements
from schooltool.interfaces import IEventTarget
from schooltool.interfaces import ITimetableReplacedEvent
from schooltool.interfaces import ITimetableExceptionAddedEvent
from schooltool.interfaces import ITimetableExceptionRemovedEvent

__metaclass__ = type


class TimetableExceptionSynchronizer:
    """Event handler that synchronizes timetable exceptions."""

    implements(IEventTarget)

    def notify(self, event):
        if ITimetableReplacedEvent.providedBy(event):
            self.notifyTimetableReplaced(event)
        elif ITimetableExceptionAddedEvent.providedBy(event):
            self.notifyTimetableExceptionAdded(event)
        elif ITimetableExceptionRemovedEvent.providedBy(event):
            self.notifyTimetableExceptionRemoved(event)

    def notifyTimetableReplaced(self, event):
        if event.old_timetable is not None:
            for exception in event.old_timetable.exceptions:
                self._exceptionRemoved(exception, event.key)
        if event.new_timetable is not None:
            for exception in event.new_timetable.exceptions:
                self._exceptionAdded(exception, event.key)

    def notifyTimetableExceptionAdded(self, event):
        self._exceptionAdded(event.exception, event.timetable.__name__)

    def notifyTimetableExceptionRemoved(self, event):
        self._exceptionRemoved(event.exception, event.timetable.__name__)

    def _exceptionAdded(self, exception, key):
        activity = exception.activity
        for obj in [activity.owner] + list(activity.resources):
            tt = obj.timetables[key]
            if exception not in tt.exceptions:
                # Call extend instead of append to reduce the number of events
                tt.exceptions.extend([exception])

    def _exceptionRemoved(self, exception, key):
        activity = exception.activity
        for obj in [activity.owner] + list(activity.resources):
            tt = obj.timetables.get(key)
            if tt is not None and exception in tt.exceptions:
                # Note that this call causes (unintentional but harmless)
                # recursion.
                tt.exceptions.remove(exception)


# TODO: synchronize timetable activites via event handlers
#       (move synchronization code from TimetableReadWriteView and
#       SchoolTimetableView to this module).

