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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Unit tests for basic person vocabularies.
"""
import unittest
import doctest

from schooltool.group.interfaces import IGroupContainer
from zope.app.testing import setup
from zope.component import provideAdapter
from zope.interface import implements


def doctest_GroupVocabulary():
    """Tests for GroupVocabulary

    If the context of a vocabulary is not a person, all groups from the
    group container are returned:

        >>> from schooltool.group.interfaces import IGroup
        >>> class GroupStub(object):
        ...     implements(IGroup)
        ...     def __init__(self, title):
        ...         self.title = title
        ...         self.__name__ = title.lower()

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> class STAppStub(dict):
        ...     implements(ISchoolToolApplication)
        ...     def __init__(self, context):
        ...         self['groups'] = {'a': GroupStub('A'),
        ...                           'b': GroupStub('B'),
        ...                           'some-group': GroupStub('Some-Group')}

        >>> provideAdapter(STAppStub, adapts=[None])
        >>> provideAdapter(lambda app: app['groups'],
        ...                adapts=[ISchoolToolApplication],
        ...                provides=IGroupContainer)

        >>> from schooltool.basicperson.vocabularies import GroupVocabulary
        >>> vocabulary = GroupVocabulary(None)
        >>> [group.token for group in vocabulary]
        ['a', 'b', 'some-group']

    If the context of the vocabulary is a person - list all the groups
    he belongs to as possible grade classes:

        >>> class SectionStub(object):
        ...     def __init__(self, name):
        ...         self.__name__ = name

        >>> from schooltool.person.interfaces import IPerson
        >>> class PersonStub(object):
        ...     implements(IPerson)
        ...     def __init__(self):
        ...         self.groups = map(GroupStub, ['A', 'B'])
        ...         self.groups.extend(map(SectionStub, ['s1', 's2']))

        >>> person = PersonStub()
        >>> vocabulary = GroupVocabulary(person)
        >>> [group.token for group in vocabulary]
        ['a', 'b']

    """


def doctest_AdvisorVocabulary():
    """Tests for AdvisorVocabulary

    If the context of a vocabulary is not a person, all groups from the
    group container are returned:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> class GroupStub(object):
        ...     def __init__(self, members):
        ...         self.members = members

        >>> class PersonStub(object):
        ...     def __init__(self, name):
        ...         self.__name__ = self.title = name

        >>> class STAppStub(dict):
        ...     implements(ISchoolToolApplication)
        ...     def __init__(self, context):
        ...         self['groups'] = {}
        ...         members = map(PersonStub, ['john', 'sarrah'])
        ...         self['groups']['teachers'] = GroupStub(members)

        >>> provideAdapter(STAppStub, adapts=[None])
        >>> provideAdapter(lambda app: app['groups'],
        ...                adapts=[ISchoolToolApplication],
        ...                provides=IGroupContainer)

        >>> from schooltool.basicperson.vocabularies import AdvisorVocabulary
        >>> vocabulary = AdvisorVocabulary(None)
        >>> [person.value.__name__ for person in vocabulary]
        ['john', 'sarrah']

    """


def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
