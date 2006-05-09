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
                
            new_person = Person(person.username, person.title)
            new_person.photo = person.photo
            new_person._hashed_password = person._hashed_password
            new_person.overlaid_calendars = person.overlaid_calendars
            new_person.__annotations = person.__annotations__
            del persons[name]
            persons[name] = new_person
            # reestablish dependents if they are available
            if dependents is not None:
                IAnnotations(new_person)[DEPENDABLE_KEY] = dependents
            # reestablish relationships
            for relation in related:
                new_person.groups.add(relation)
