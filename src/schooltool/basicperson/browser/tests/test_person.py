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
Unit tests for basic person views.

$Id$
"""
import unittest

from zope.interface import implements
from zope.component import provideAdapter
from zope.app.testing import setup
from zope.testing import doctest


def doctest_PersonAddFormAdapter():
    """Tests for PersonAddFormAdapter

    PersonAddFormAdapter just wraps a person object but hides
    setPassword method unde a write only password property:

        >>> class PersonStub(object):
        ...     def setPassword(self, new_password):
        ...         print "Setting password to:", new_password

        >>> person = PersonStub()
        >>> person.name = "John"
        >>> person.last_name = "Johnson"

        >>> from schooltool.basicperson.browser.person import PersonAddFormAdapter
        >>> pa = PersonAddFormAdapter(person)
        >>> pa.password = "FooBar3"
        Setting password to: FooBar3

        >>> pa.password is None
        True

        >>> pa.name
        'John'

        >>> pa.surname = "Peterson"
        >>> person.surname
        'Peterson'

    """


def doctest_PersonTerm():
    """Tests for PersonTerm.

    Person term is a title tokenized term that uses the title of a
    person as the title to be displayed:

        >>> class PersonStub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...         self.__name__ = title.lower()

        >>> john = PersonStub('John')

        >>> from schooltool.basicperson.browser.person import PersonTerm
        >>> term = PersonTerm(john)
        >>> term.title
        'John'
        >>> term.token
        'john'
        >>> term.value
        <...test_person.PersonStub object at ...>

    """


def doctest_TermsBase():
    """Tests for TermsBase.

    Let's construct the TermsBase:

        >>> class TermStub(object):
        ...     def __init__(self, value):
        ...         self.value = value
        ...     def __repr__(self):
        ...         return "<TermStub %s>" % self.value

        >>> from schooltool.basicperson.browser.person import TermsBase
        >>> source = ["john"]
        >>> terms = TermsBase(source, None)

    If no term factory is set - NotImplementedError is raised:

        >>> terms.getTerm("john")
        Traceback (most recent call last):
        ...
        NotImplementedError: Term Factory must be provided by inheriting classes.

    If term factory is present it is used to construct the term from
    the given value:

        >>> terms.factory = TermStub

        >>> terms.getTerm("john")
        <TermStub john>

    If there is no such value in the source - we get a lookup error:

        >>> terms.getTerm("peter")
        Traceback (most recent call last):
        ...
        LookupError: peter

    """


def doctest_GroupTerm():
    """Tests for GroupTerm.

    Group term is a title tokenized term that uses the title of a
    group as the title to be displayed:

        >>> class GroupStub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...         self.__name__ = title

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> class STAppStub(dict):
        ...     implements(ISchoolToolApplication)
        ...     def __init__(self, context):
        ...         self['groups'] = {'teachers': GroupStub('Teachers')}

        >>> provideAdapter(STAppStub, adapts=[None])
        >>> from schooltool.group.interfaces import IGroupContainer
        >>> provideAdapter(lambda app: app['groups'], adapts=[ISchoolToolApplication],
        ...                provides=IGroupContainer)

        >>> from schooltool.basicperson.browser.person import GroupTerm
        >>> term = GroupTerm(GroupStub("teachers"))
        >>> term.title
        'teachers'
        >>> term.token
        'teachers'
        >>> term.value
        <schooltool.basicperson.browser.tests.test_person.GroupStub object at ...>

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
