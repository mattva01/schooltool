#
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Schooltool teaching levels.
"""

from persistent import Persistent

import zope.schema
from zope.schema.vocabulary import SimpleTerm
from zope.interface import implements, implementer
from zope.component import adapts, adapter
from zope.component import getUtility
from zope.container.btree import BTreeContainer
from zope.container.ordered import OrderedContainer
from zope.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.intid import addIntIdSubscriber
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent import ObjectAddedEvent
from zope.proxy import sameProxiedObjects

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.app import InitBase, StartUpBase
from schooltool.app.utils import TitledContainerItemVocabulary
from schooltool.schoolyear.interfaces import ISchoolYearContainer, ISchoolYear
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.relationship import URIObject, RelationshipSchema
from schooltool.relationship import RelationshipProperty
from schooltool.table.table import simple_form_key
from schooltool.level import interfaces


URILevelCourses = URIObject(
    'http://schooltool.org/ns/cambodia/levelcourses/',
    'Courses at the level(s).',
    'Courses to be taught at given level(s).')

URICourse = URIObject(
    'http://schooltool.org/ns/cambodia/levelcourses/course',
    'Course',
    'The course to teach.')

URILevel = URIObject(
    'http://schooltool.org/ns/cambodia/levelcourses/level',
    'Level',
    'The teaching level.')


LevelCourses = RelationshipSchema(URILevelCourses,
                                 level=URILevel,
                                 course=URICourse)


LEVELS_APP_KEY = 'schooltool.level.level'


class LevelContainerContainer(BTreeContainer):
    """Container of level containers."""

    implements(interfaces.ILevelContainerContainer,
               IAttributeAnnotatable)


class LevelContainer(OrderedContainer):
    """Container of levels."""

    implements(interfaces.ILevelContainer, IAttributeAnnotatable)


class Level(Persistent, Contained):
    """A teaching level."""

    implements(interfaces.ILevel, interfaces.ILevelContained,
               IAttributeAnnotatable)
    courses = RelationshipProperty(URILevelCourses,
                                   URILevel,
                                   URICourse)

    def __init__(self, title=None):
        self.title = title


class VivifyLevelContainerContainer(object):

    def __call__(self):
        if LEVELS_APP_KEY not in self.app:
            self.app[LEVELS_APP_KEY] = LevelContainerContainer()


class LevelInit(VivifyLevelContainerContainer, InitBase):
    pass


class LevelStartUp(VivifyLevelContainerContainer, StartUpBase):
    pass


@adapter(ISchoolYear)
@implementer(interfaces.ILevelContainer)
def getLevelContainer(sy):
    addIntIdSubscriber(sy, ObjectAddedEvent(sy))
    int_ids = getUtility(IIntIds)
    sy_id = str(int_ids.getId(sy))
    app = ISchoolToolApplication(None)
    lc = app[LEVELS_APP_KEY].get(sy_id, None)
    if lc is None:
        lc = app[LEVELS_APP_KEY][sy_id] = LevelContainer()
    return lc


@adapter(ISchoolToolApplication)
@implementer(interfaces.ILevelContainer)
def getLevelContainerForApp(app):
    syc = ISchoolYearContainer(app, None)
    sy = syc.getActiveSchoolYear()
    if sy is None:
        return None
    return interfaces.ILevelContainer(sy)


@adapter(interfaces.ILevelContainer)
@implementer(ISchoolYear)
def getSchoolYearForLevelContainer(level_container):
    container_id = int(level_container.__name__)
    int_ids = getUtility(IIntIds)
    container = int_ids.getObject(container_id)
    return container


@adapter(interfaces.ILevel)
@implementer(ISchoolYear)
def getSchoolYearForLevel(level):
    level_container = level.__parent__
    return ISchoolYear(level_container)


class RemoveLevelsWhenSchoolYearIsDeleted(ObjectEventAdapterSubscriber):
    adapts(IObjectRemovedEvent, ISchoolYear)

    def __call__(self):
        level_container = interfaces.ILevelContainer(self.object)
        for level_id, level in list(level_container.items()):
            del level_container[level_id]
        app = ISchoolToolApplication(self.object)
        top_level_container = app[LEVELS_APP_KEY]
        del top_level_container[level_container.__name__]


class LevelVocabulary(TitledContainerItemVocabulary):
    """Vocabulary of levels for contexts adaptable to ISchoolYear"""
    implements(zope.schema.interfaces.IIterableVocabulary)

    @property
    def container(self):
        schoolyear = ISchoolYear(self.context, None)
        if schoolyear is None:
            return {}
        return interfaces.ILevelContainer(schoolyear)


def levelVocabularyFactory():
    return LevelVocabulary
