#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Lyceum journal content classes.

$Id$

"""
from BTrees.OOBTree import OOBTree
from persistent import Persistent

from zope.app.container.btree import BTreeContainer
from zope.interface import implements
from zope.location.interfaces import ILocation

from schooltool.app.interfaces import ISchoolToolApplication

from lyceum.journal.interfaces import ILyceumJournal


class LyceumJournalContainer(BTreeContainer):
    """A container for all the journals in the system."""


class LyceumJournal(Persistent):
    """A journal for a section."""
    implements(ILyceumJournal, ILocation)

    def __init__(self):
        self.__parent__ = None
        self.__name__ = None
        self.__data__ = OOBTree()

    @property
    def section(self):
        app = ISchoolToolApplication(None)
        sections = app['sections']
        return sections[self.__name__]

    def setGrade(self, person, meeting, grade):
        key = (person.__name__, meeting.unique_id)
        grades = self.__data__.get(key, ())
        self.__data__[key] = (grade,) + grades

    def getGrade(self, person, meeting, default=None):
        key = (person.__name__, meeting.unique_id)
        grades = self.__data__.get(key, ())
        if not grades:
            return default
        return grades[0]


def getSectionLyceumJournal(section):
    """Get the journal for the section."""
    app = ISchoolToolApplication(None)
    jc = app['lyceum.journal']
    journal = jc.get(section.__name__, None)
    if journal is None:
        jc[section.__name__] = journal = LyceumJournal()

    return journal


def getEventLyceumJournal(event):
    """Get the journal for a TimetableCalendarEvent."""
    section = event.activity.owner
    return ILyceumJournal(section)
