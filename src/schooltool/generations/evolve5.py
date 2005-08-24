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

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding
from schooltool.app.interfaces import ISchoolToolApplication

from schooltool.note.interfaces import IHaveNotes, INotes
from schooltool.relationship import getRelatedObjects
from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.timetable.interfaces import IHaveTimetables
from schooltool.timetable import TIMETABLES_KEY
from schooltool.app.cal import CALENDAR_KEY
from schooltool.app.interfaces import IHaveCalendar
from schooltool.app.relationships import URIInstruction, URISection


def fixAnnotations(obj):
    if not hasattr(obj, '__annotations__'):
        return
    for key, data in obj.__annotations__.items():
        if key.startswith('schoolbell'):
            obj.__annotations__['schooltool'+key[10:]] = data
            del obj.__annotations__[key]

def fixNotes(obj):
    if IHaveNotes.providedBy(obj):
        notes = INotes(obj)
        notes._p_changed = True
        for note in notes:
            note._p_changed = True

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

def fixRelationships(obj):
    obj.rel_type
    obj.my_role
    obj.other_role
    for link in IRelationshipLinks(obj.this):
        link._p_changed = True

def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name)

    fixAnnotations(root)
    fixNotes(root)
    fixCalendar(root)
    fixTimetables(root)

    # Let's create a new authentication utility, so all old references
    # are fixed.
    from zope.app.component.interfaces.registration import InactiveStatus
    from zope.app.component.interfaces.registration import IRegistered
    from schooltool.app.security import setUpLocalAuth
    auth = root.getSiteManager()['default']['SchoolBellAuth']
    reg = IRegistered(auth).registrations()[0]
    reg.status = InactiveStatus
    reg_name = reg.__name__

    del root.getSiteManager()['default'].registrationManager[reg_name]
    del root.getSiteManager()['default']['SchoolBellAuth']
    setUpLocalAuth(root)

    # Core content components
    for container in root.values():

        fixAnnotations(container)
        fixNotes(container)
        container._p_changed = True

        for entry in container.values():
            fixAnnotations(entry)
            fixNotes(entry)
            fixCalendar(entry)
            fixTimetables(entry)
            entry._p_changed = True

    for person in root['persons'].values():
        if hasattr(person.overlaid_calendars, 'show_timetables'):
            show_timetables = person.overlaid_calendars.show_timetables
            IShowTimetables(person).showTimetables = show_timetables
            del person.overlaid_calendars.show_timetables
        fixRelationships(person.groups)
        getRelatedObjects(person, URISection, rel_type=URIInstruction)

    for group in root['groups'].values():
        fixRelationships(group.members)

    for course in root['courses'].values():
        fixRelationships(course.sections)

    for section in root['sections'].values():
        fixRelationships(section.instructors)
        fixRelationships(section.members)
        fixRelationships(section.courses)

    for schema in root['ttschemas'].values():
        for name, day in schema.items():
            day._p_changed = True

