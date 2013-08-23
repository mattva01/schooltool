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
Implementation of notes for IAnnotatable objects.

Notes are stored as a PersistentList of Note objects on IAnnotatable objects.
A Note is a simple object that stores a brief note or comment about an object
to be entered by a user.

TODO: It might be a good idea to add some ACL to notes:

    John in Accounting creates an event for the annual employee picnic.  Scott
    from the Cafeteria group needs to note that the cream will go bad if it
    sits outside for more than 4 hours.  Nobody in Accounting should really see
    this, but everyone in the Cafeteria should.

TODO: Notes are basically stupid comments, do we need real discussion items?  A
      note on a note has a fairly visible use-case (say Jane from the Cafeteria
      group notes that a new supply of super-fresh cream is due the day before
      the picnic..)
"""
import datetime
import random

from persistent import Persistent
from persistent.list import PersistentList
from zope.annotation.interfaces import IAnnotations
from zope.interface import implements

from schooltool.note import interfaces
from schooltool.person.interfaces import IPerson
from schooltool.securitypolicy.crowds import Crowd


def getNotes(context):
    """Adapt an IAnnotatable object to INotes."""
    annotations = IAnnotations(context)
    key = 'schooltool.app.Notes'
    try:
        return annotations[key]
    except KeyError:
        annotations[key] = Notes()
        annotations[key].__parent__ = context
        return annotations[key]


class Note(Persistent):
    """A Note.

    Your basic simple content ojbect:

    >>> note = Note(title='Potluck Theme!',
    ...             body="We're going Mexican! Bring tequila and tacos!",
    ...             privacy="private")
    >>> note.title
    'Potluck Theme!'
    >>> note.body
    "We're going Mexican! Bring tequila and tacos!"

    """
    implements(interfaces.INote)

    def __init__(self, title=None, body=None, privacy=None, owner=None):
        self.title = title
        self.body = body
        self.privacy = privacy
        self.owner = owner
        self.unique_id = '%d.%d' %(datetime.datetime.utcnow().microsecond,
                                   random.randrange(10 ** 6, 10 ** 7))

class Notes(Persistent):
    """A list of Note objects.

    Notes are just a container for Note objects

    >>> notes = Notes()

    Add a few notes

    >>> note1 = Note(title="note1")
    >>> note2 = Note(title="note2")
    >>> notes.add(note1)
    >>> notes.add(note2)

    Iterate over the notes

    >>> [n.title for n in notes]
    ['note1', 'note2']

    Remove a note

    >>> notes.remove(note1.unique_id)
    >>> [n.title for n in notes]
    ['note2']

    Remove all the notes

    >>> notes.clear()
    >>> [n for n in notes]
    []

    """
    implements(interfaces.INotes)

    def __init__(self):
        self._notes = PersistentList()

    def __iter__(self):
        return iter(self._notes)

    def add(self, note):
        self._notes.append(note)

    def remove(self, unique_id):
        for note in self._notes:
            if note.unique_id == unique_id:
                self._notes.remove(note)

    def clear(self):
        del self._notes[:]


class NoteCrowd(Crowd):
    def contains(self, principal):
        if self.context.privacy == 'private':
            return IPerson(self.principal) == self.context.owner
        else:
            return True

