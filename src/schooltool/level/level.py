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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Schooltool grade levels.
"""

from persistent import Persistent

import zope.schema
from zope.interface import implements, implementer
from zope.component import adapter
from zope.container.btree import BTreeContainer
from zope.container.ordered import OrderedContainer
from zope.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.app import InitBase, StartUpBase
from schooltool.app.utils import TitledContainerItemVocabulary
from schooltool.relationship import URIObject, RelationshipSchema
from schooltool.relationship import RelationshipProperty
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


# BBB: for evolution
class LevelContainerContainer(BTreeContainer):
    """Container of level containers."""


class LevelContainer(OrderedContainer):
    """Container of levels."""

    implements(interfaces.ILevelContainer, IAttributeAnnotatable)


class Level(Persistent, Contained):
    """A grade level."""

    implements(interfaces.ILevel, interfaces.ILevelContained,
               IAttributeAnnotatable)
    courses = RelationshipProperty(URILevelCourses,
                                   URILevel,
                                   URICourse)

    def __init__(self, title=None):
        self.title = title


class VivifyLevelContainer(object):

    def __call__(self):
        if LEVELS_APP_KEY not in self.app:
            self.app[LEVELS_APP_KEY] = LevelContainer()


class LevelInit(VivifyLevelContainer, InitBase):
    pass


class LevelStartUp(VivifyLevelContainer, StartUpBase):
    pass


@adapter(ISchoolToolApplication)
@implementer(interfaces.ILevelContainer)
def getLevelContainer(app):
    return app[LEVELS_APP_KEY]


class LevelVocabulary(TitledContainerItemVocabulary):
    """Vocabulary of levels."""
    implements(zope.schema.interfaces.IIterableVocabulary)

    @property
    def container(self):
        app = ISchoolToolApplication(None)
        return interfaces.ILevelContainer(app, {})


def levelVocabularyFactory():
    return LevelVocabulary
