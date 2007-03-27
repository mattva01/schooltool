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
Unit tests for lyceum vocabularies.

$Id$
"""
import unittest

from zope.app.testing import setup
from zope.component import provideAdapter
from zope.interface import implements
from zope.testing import doctest


def doctest_GradeClassSource():
    """Tests for GradeClassSource

    If the context of a source is not a person, all groups from the
    group container are returned:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> class STAppStub(dict):
        ...     def __init__(self, context):
        ...         self['groups'] = {'a': None, 'b': None, 'some-group': None}

        >>> provideAdapter(STAppStub, adapts=[None], provides=ISchoolToolApplication)

        >>> from lyceum.vocabularies import GradeClassSource
        >>> source = GradeClassSource(None)
        >>> [group for group in source]
        ['a', 'b', 'some-group']

    If the context of the vocabulary is a person - list all the groups
    he belongs to as possible grade classes:

        >>> from schooltool.group.interfaces import IGroup
        >>> class GroupStub(object):
        ...     implements(IGroup)
        ...     def __init__(self, name):
        ...         self.__name__ = name

        >>> class SectionStub(object):
        ...     def __init__(self, name):
        ...         self.__name__ = name

        >>> from schooltool.person.interfaces import IPerson
        >>> class PersonStub(object):
        ...     implements(IPerson)
        ...     def __init__(self):
        ...         self.groups = map(GroupStub, ['g2', 'g1'])
        ...         self.groups.extend(map(SectionStub, ['s1', 's2']))

        >>> person = PersonStub()
        >>> source = GradeClassSource(person)
        >>> [group for group in source]
        ['g1', 'g2']

    """


def doctest_AdvisorSource():
    """Tests for AdvisorSource

    If the context of a source is not a person, all groups from the
    group container are returned:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> class GroupStub(object):
        ...     def __init__(self, members):
        ...         self.members = members

        >>> class PersonStub(object):
        ...     def __init__(self, name):
        ...         self.__name__ = name

        >>> class STAppStub(dict):
        ...     def __init__(self, context):
        ...         self['groups'] = {}
        ...         members = map(PersonStub, ['john', 'sarrah'])
        ...         self['groups']['teachers'] = GroupStub(members)

        >>> provideAdapter(STAppStub, adapts=[None], provides=ISchoolToolApplication)

        >>> from lyceum.vocabularies import AdvisorSource
        >>> source = AdvisorSource(None)
        >>> [person for person in source]
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
