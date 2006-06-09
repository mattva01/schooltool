#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 14.

Use schooltool.demographics.person.Person instead of
schooltool.person.person.Person

$Id: evolve13.py 5946 2006-04-18 15:47:33Z ignas $
"""
from BTrees.OOBTree import OOBTree

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding
from zope.location import locate, ILocation
from zope.annotation.interfaces import IAnnotations

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.demographics.person import Person

DEPENDABLE_KEY = 'zope.app.dependable.Dependents'

def evolve(context):
    root = context.connection.root()[ZopePublication.root_name]    
    for app in findObjectsProviding(root, ISchoolToolApplication):
        persons = app['persons']
        for name, person in persons.items():
            # wipe out dependency information temporarily
            ann = IAnnotations(person, None)
            if ann is not None:
                dependents = ann.get(DEPENDABLE_KEY)
            else:
                dependents = None
            if dependents is not None:
                IAnnotations(person)[DEPENDABLE_KEY] = ()
            # remove all relationships of this person to reestablish them
            # later
            related = list(person.groups)
            for relation in related:
                person.groups.remove(relation)
            # also remove all overlaid calendars to reestablish them later
            # XXX horrible way to remove calendars; due to some magic
            # in the calendar overlays just removing the items we
            # get when we do list(persons.overlaid_calendar) doesn't work
            cal_infos = list(person.overlaid_calendars)
            for cal_info in cal_infos:
                person.overlaid_calendars.remove(cal_info.calendar)
            new_person = Person(person.username, person.title)
            new_person.photo = person.photo
            new_person._hashed_password = person._hashed_password

            # We create a new __annotations__ dict as it gets modified
            # by del persons[name] (a new schooltool calendar is
            # created on access just to get cleared by the event
            # subscriber). So sharing the same annotation OOBTree
            # might lead to various weird bugs.
            new_person.__annotations__ = OOBTree()
            for key, annotation in person.__annotations__.items():
                new_person.__annotations__[key] = annotation
                if hasattr(annotation, '__parent__') and annotation.__parent__ is person:
                    annotation.__parent__ = new_person

            del persons[name]
            persons[name] = new_person
            # reestablish dependents if they are available
            if dependents is not None:
                IAnnotations(new_person)[DEPENDABLE_KEY] = dependents
            # reestablish relationships
            for relation in related:
                new_person.groups.add(relation)
            for cal_info in cal_infos:
                new_person.overlaid_calendars.add(cal_info.calendar)

