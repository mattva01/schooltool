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
Upgrade SchoolTool to generation 5.

This generation converts all the old class paths to their new ones.

1. Make sure that all content components have been loaded at least once,
   so that their class reference is changed to the new one.

2. Fix up all annotation references. This is tough, because we have to
   find all objects that provide IAnnotatable.

   List of annotatable objects in SchoolTool:

   - (all primary content components)
   - schooltool.app.app.SchoolToolApplication
   - schooltool.app.cal.CalendarEvent
   - schooltool.app.cal.Calendar

3. Convert old attributes 'calendar' and 'timetables' to annotations.

4. Update references to objects that were in packages previously located in
   schoolbell, but are now in schooltool. Examples are `relationship` and
   `calendar`.

$Id: evolve2.py 4259 2005-07-21 00:57:30Z tvon $
"""
from zope.app.securitypolicy.securitymap import PersistentSecurityMap

from schooltool.timetable import TIMETABLES_KEY
from schooltool.timetable.interfaces import IHaveTimetables
from schooltool.app.cal import CALENDAR_KEY
from schooltool.app.interfaces import IHaveCalendar


def fixAnnotations(obj):
    if not hasattr(obj, '__annotations__'):
        return
    for key, data in obj.__annotations__.items():
        if key.startswith('schoolbell'):
            obj.__annotations__['schooltool'+key[10:]] = data
            del obj.__annotations__[key]


def fixCalendar(obj):
    if IHaveCalendar.providedBy(obj):
        if hasattr(obj, 'calendar'):
            calendar = obj.calendar
            fixAnnotations(calendar)
            for event in calendar:
                fixAnnotations(event)
            obj.__annotations__[CALENDAR_KEY] = calendar
            del obj.calendar


def fixTimetables(obj):
    if IHaveTimetables.providedBy(obj):
        if hasattr(obj, 'timetables'):
            obj.__annotations__[TIMETABLES_KEY] = obj.timetables
            del obj.timetables


def fixOverlaidCalendars(obj):
    if hasattr(obj, 'overlaid_calendars') and \
           hasattr(obj.overlaid_calendars, 'show_timetables'):
        show_timetables = obj.overlaid_calendars.show_timetables
        IShowTimetables(obj.overlaid_calendars).showTimetables = show_timetables
        del obj.overlaid_calendars.show_timetables


def fixPermissionMap(obj):
    if isinstance(obj, PersistentSecurityMap):
        for pkey, data in obj._byrow.items():
            if pkey.startswith('schoolbell'):
                obj._byrow['schooltool' + pkey[10:]] = data
                del obj._byrow[pkey]

        for key, data in obj._bycol.items():
            for pkey, pdata in data.items():
                if pkey.startswith('schoolbell'):
                    obj._bycol[key]['schooltool' + pkey[10:]] = pdata
                    del obj._bycol[key][pkey]


def evolve(context):
    storage = context.connection._storage
    next_oid = None
    while True:
        oid, tid, data, next_oid = storage.record_iternext(next_oid)
        obj = context.connection.get(oid)
        # Make sure that we tell all objects that they have been changed. Who
        # cares whether it is true! :-)
        obj._p_activate()
        obj._p_changed = True

        # Now fix up other things
        fixAnnotations(obj)
        fixCalendar(obj)
        fixTimetables(obj)
        fixOverlaidCalendars(obj)
        fixPermissionMap(obj)

        if next_oid is None:
            break
