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
School Level Implementation

$Id$
"""
import persistent
import sets
import zope.interface
import zope.schema
from zope.app import zapi
from zope.app.container import contained, btree

from schooltool import app
from schooltool.level import interfaces

class LevelContainer(btree.BTreeContainer):
    """Container of Level."""

    zope.interface.implements(interfaces.ILevelContainer)

    def validate(self):
        """See schooltool.level.interfaces.ILevelContainer"""
        allseen = sets.Set()

        # Make sure that there are no loops in the level graphs.
        for initial in [level for level in self.values()
                        if level.isInitial]:
            current = initial
            visited = [current]
            while current is not None:
                if current.nextLevel in visited:
                    raise interfaces.LevelLoopError(current)
                visited.append(current)
                current = current.nextLevel
                
            allseen.update(visited)

        # Make sure that all levels are connected in a graph.
        disconnected = [level for level in self.values()
                        if level not in allseen]
        if disconnected:
            raise interfaces.DisconnectedLevelsError(disconnected)


def addLevelContainerToApplication(event):
    event.object['levels'] = LevelContainer()


class Level(persistent.Persistent, contained.Contained):
    """A simple implementation of a school level."""

    zope.interface.implements(interfaces.ILevel, interfaces.ILevelContained)

    def __init__(self, title, isInitial=False, nextLevel=None):
        self.title = title
        self.isInitial = isInitial
        self.nextLevel = nextLevel

    def __repr__(self):
        return "<Level '%s'>" %self.title 


class LevelTerm(object):

    zope.interface.implements(zope.schema.interfaces.ITitledTokenizedTerm)

    def __init__(self, level):
        self.value = level
        self.token = zapi.getName(level)
        self.title = level.title

    def __repr__(self):
        return "<LevelTerm token='%s' title='%s'>" %(self.token, self.title) 


class LevelVocabulary(object):
    """This vocabulary provides a list of all available levels.

    The location must be set, so that the schooltool application can be found.
    """
    zope.interface.implements(zope.schema.interfaces.IVocabularyTokenized)

    def __init__(self, context=None):
        pass

    def __contains__(self, value):
        """See zope.schema.interfaces.IBaseVocabulary"""
        return value in app.getSchoolToolApplication()['levels'].values()

    def getTerm(self, value):
        """See zope.schema.interfaces.IBaseVocabulary"""
        if value not in self:
            raise LookupError(value)
        return LevelTerm(value)

    def getTermByToken(self, token):
        """See zope.schema.interfaces.IVocabularyTokenized"""
        try:
            return LevelTerm(app.getSchoolToolApplication()['levels'][token])
        except KeyError:
            raise LookupError(token)

    def __iter__(self):
        """See zope.schema.interfaces.IIterableVocabulary"""
        return iter(
            [self.getTerm(level)
             for level in app.getSchoolToolApplication()['levels'].values()]
            )

    def __len__(self):
        """See zope.schema.interfaces.IIterableVocabulary"""
        return len(app.getSchoolToolApplication()['levels'])
