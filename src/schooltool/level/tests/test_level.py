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
Unit tests for levels.
"""
import unittest
import doctest

from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.testing import setup
from zope.interface import implements, Interface
from zope.interface.verify import verifyObject
from zope.location.pickling import LocationCopyHook
from zope.component import provideAdapter
from zope.component.hooks import getSite, setSite
from zope.site import SiteManagerContainer
from zope.site.folder import rootFolder

from schooltool.testing.setup import ZCMLWrapper
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.relationship.tests import setUpRelationships
from schooltool.relationship.relationship import getRelatedObjects
from schooltool.level.level import URILevelCourses, URILevel


class AppStub(dict, SiteManagerContainer):
    implements(ISchoolToolApplication)


class CourseStub(object):
    implements(IAttributeAnnotatable)
    def __init__(self, title):
        self.title = unicode(title)
    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.title)


def provideApplicationStub():
    app = AppStub()
    provideAdapter(
        lambda ignored: app,
        adapts=(None,),
        provides=ISchoolToolApplication)
    return app


def doctest_LevelContainerContainer():
    """Tests for LevelContainerContainer.

    This is a simple container for different level configurations
    in each schoolyear.

        >>> from schooltool.level.interfaces import ILevelContainerContainer
        >>> from schooltool.level.level import LevelContainerContainer

        >>> root_level_container = LevelContainerContainer()
        >>> verifyObject(ILevelContainerContainer, root_level_container)
        True

        >>> root_level_container[u'2009'] = u'School year 2009 levels'
        >>> sorted(root_level_container.items())
        [(u'2009', u'School year 2009 levels')]

    """


def doctest_LevelContainer():
    """Tests for LevelContainer.

        >>> from schooltool.level.interfaces import ILevelContainer
        >>> from schooltool.level.level import LevelContainer

    A simple ordered container of levels.

        >>> level_container = LevelContainer()
        >>> verifyObject(ILevelContainer, level_container)
        True

        >>> level_container['vienas'] = u'One'
        >>> level_container['du'] = u'Two'
        >>> level_container['trys'] = u'Three'

        >>> level_container.keys()
        ['vienas', 'du', 'trys']

        >>> level_container.values()
        [u'One', u'Two', u'Three']

        >>> level_container.updateOrder(['trys', 'du', 'vienas'])

        >>> level_container.values()
        [u'Three', u'Two', u'One']

    """


def doctest_Level():
    """Tests for Level.

        >>> from schooltool.level.interfaces import ILevel
        >>> from schooltool.level.level import Level

    Level is a very simple object.

        >>> level = Level(u'1')
        >>> verifyObject(ILevel, level)
        True

        >>> print level.title
        1

    It has a courses attribute to control which courses are taught this level.

        >>> course1 = CourseStub('C1')
        >>> level.courses.add(course1)

        >>> course2 = CourseStub('C2')
        >>> level.courses.add(course2)

        >>> print sorted(level.courses, key=lambda l: l.title)
        [<CourseStub u'C1'>, <CourseStub u'C2'>]

    The courses attribute actually manages relationships between the level and
    the course objects.

        >>> print ['Level %r' % l.title
        ...     for l in getRelatedObjects(
        ...         course1, URILevel, rel_type=URILevelCourses)]
        ["Level u'1'"]

    """


def doctest_VivifyLevelContainerContainer():
    """Tests for VivifyLevelContainerContainer.

    This is a simple mixin to ensure the top level container is created.

        >>> from schooltool.level.level import VivifyLevelContainerContainer

        >>> app = ISchoolToolApplication(None)
        >>> mixin = VivifyLevelContainerContainer()

    As a mixin, it expects child classes to set the app attribute.

        >>> mixin.app = app

    Let's check if container is created.

        >>> app.keys()
        []

        >>> mixin()
        >>> app.keys()
        ['schooltool.level.level']

        >>> level_key = app.keys()[0]

        >>> from schooltool.level.interfaces import ILevelContainerContainer
        >>> verifyObject(ILevelContainerContainer, app[level_key])
        True

    Once the container is created, it is not replaced.

        >>> app[level_key]['1'] = u'One'

        >>> mixin = VivifyLevelContainerContainer()
        >>> mixin.app = app
        >>> mixin()

        >>> list(app[level_key].items())
        [(u'1', u'One')]

    """


def doctest_LevelSource():
    """Tests for LevelSource.

    Vocabulary of levels for contexts that can be adapted to ISchoolYear.

        >>> from zope.schema.interfaces import IIterableSource
        >>> from schooltool.level.level import Level
        >>> from schooltool.level.level import LevelSource

        >>> class ContextStub(object):
        ...     implements(Interface)

        >>> context = ContextStub()
        >>> source = LevelSource(context)
        >>> verifyObject(IIterableSource, source)
        True

    When the context cannot be adapted to ISchoolYear, the vocabulary is empty.

        >>> source.levels
        {}

        >>> len(source)
        0

        >>> list(source)
        []

        >>> def expand_term(term):
        ...     return (term.token, term.value, term.title)

        >>> level = Level(u'Basic')
        >>> level.__name__ = 'basic'
        >>> expand_term(source.getTerm(level))
        ('basic-', <schooltool.level.level.Level ...>, u'Basic')

        >>> source.getTermByToken('basic-')
        Traceback (most recent call last):
        ...
        LookupError: basic-

        >>> level in source
        False

    Let's provide the needed adapters.

        >>> from datetime import date
        >>> from schooltool.schoolyear.interfaces import ISchoolYear
        >>> from schooltool.schoolyear.schoolyear import SchoolYear

        >>> schoolyear = SchoolYear(
        ...     "2005", date(2005, 9, 1), date(2005, 12, 30))

        >>> provideAdapter(
        ...     lambda ignored: schoolyear,
        ...     adapts=(ContextStub, ),
        ...     provides=ISchoolYear)

        >>> from schooltool.level.interfaces import ILevelContainer
        >>> from schooltool.level.level import LevelContainer

        >>> levels = LevelContainer()
        >>> levels['basic'] = Level(u'Basic')
        >>> levels['advanced'] = Level(u'Advanced')

        >>> provideAdapter(
        ...     lambda ignored: levels,
        ...     adapts=(ISchoolYear, ),
        ...     provides=ILevelContainer)

    Now we can use the vocabulary.

        >>> source = LevelSource(context)
        >>> verifyObject(IIterableSource, source)
        True

        >>> source.levels
        <schooltool.level.level.LevelContainer ...>

        >>> len(source)
        2

        >>> [expand_term(term) for term in source]
        [('basic-', <schooltool.level.level.Level ...>, u'Basic'),
         ('advanced-', <schooltool.level.level.Level ...>, u'Advanced')]

        >>> expand_term(source.getTerm(levels['basic']))
        ('basic-', <schooltool.level.level.Level ...>, u'Basic')

        >>> levels['basic'] in source
        True

        >>> expand_term(source.getTermByToken('basic-'))
        ('basic-', <schooltool.level.level.Level ...>, u'Basic')

    Note that levels from other schoolyears and so on are not considered
    part of the vocabulary.

        >>> other_level = Level(levels['basic'].title)
        >>> other_level.__name__ = 'basic'
        >>> other_level in source
        False

    """


def setUp(test):
    setup.placefulSetUp()
    setUpRelationships()
    provideApplicationStub()


def tearDown(test):
    setup.placefulTearDown()


def provideStubAdapter(factory, adapts=None, provides=None, name=u''):
    sm = getSite().getSiteManager()
    sm.registerAdapter(factory, required=adapts, provided=provides, name=name)


def unregisterStubAdapter(factory, adapts=None, provides=None, name=u''):
    sm = getSite().getSiteManager()
    sm.unregisterAdapter(factory, required=adapts, provided=provides, name=name)


def setUpIntegration(test):
    setup.placefulSetUp()
    # Workaround: _clear actually sets the Zope's vocabulary registry and
    #             is called on zope.app.schema.vocabularies import (during
    #             zcml parsing, for example).  When running multiple tests
    #             this ingenious idea fails, so we call it manually.
    from zope.app.schema import vocabulary
    vocabulary._clear()

    zcml = ZCMLWrapper()
    zcml.setUp(
        namespaces={"": "http://namespaces.zope.org/zope"},
        i18n_domain='schooltool')
    zcml.include('zope.app.zcmlfiles')
    # We define the default pemissions here, because though widely used,
    # they are currently mangled with other stuff in schooltool.common
    zcml.string('''
      <permission id="schooltool.view" title="View" />
      <permission id="schooltool.edit" title="Edit Info" />
    ''')

    zcml.include('zope.intid')
    zcml.string('''
      <utility
        factory="zope.intid.IntIds"
        provides="zope.intid.interfaces.IIntIds"
      />
      <adapter
          for="persistent.interfaces.IPersistent"
          factory="schooltool.testing.stubs.KeyReferenceStub"
          trusted="y"
          />
    ''')

    zcml.include('schooltool.level', file='level.zcml')
    zcml.include('schooltool.schoolyear', file='schoolyear.zcml')
    zcml.include('schooltool.relationship', file='relationship.zcml')
    provideAdapter(LocationCopyHook)

    root = rootFolder()
    root['app'] = provideApplicationStub()
    setup.createSiteManager(root['app'], setsite=True)
    test.globs.update({
        'zcml': zcml,
        'CourseStub': CourseStub,
        'getRelatedObjects': getRelatedObjects,
        'provideAdapter': provideStubAdapter,
        'unregisterAdapter': unregisterStubAdapter,
        })


def test_suite():
    optionflags = (doctest.NORMALIZE_WHITESPACE |
                   doctest.ELLIPSIS |
                   doctest.REPORT_NDIFF)
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=optionflags),
        doctest.DocFileSuite(
            'level-integration.txt',
            setUp=setUpIntegration, tearDown=tearDown,
            optionflags=optionflags),
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')


