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
Tests for schoolbell views.

$Id$
"""

import unittest
from zope.testing import doctest
from zope.interface import implements


def doctest_getSchoolBellApplication():
    """Tests for getSchoolBellApplication.

    Let's say we have a SchoolBell app, a persons container and a person.

      >>> from schoolbell.app.app import SchoolBellApplication, Person

      >>> p = Person()
      >>> app = SchoolBellApplication()
      >>> app['persons']['1'] = p

    getSchoolBellApplication returns the app object for all these contexts:

      >>> from schoolbell.app.browser import getSchoolBellApplication
      >>> getSchoolBellApplication(app) is app
      True

      >>> getSchoolBellApplication(app['persons']) is app
      True

      >>> getSchoolBellApplication(p) is app
      True


    However, this function raises an error if the object does not have
    an ISchoolBellApplication among its ancestors:

      >>> from zope.interface import implements
      >>> from zope.app.location.interfaces import ILocation
      >>> class Foo:
      ...     implements(ILocation)
      ...     __parent__ = None
      ...     def __repr__(self):
      ...         return "Foo()"
      ...
      >>> foo = Foo()
      >>> getSchoolBellApplication(foo)
      Traceback (most recent call last):
      ...
      ValueError: can't get a SchoolBellApplication from Foo()

    Also, it raises the same error if the object is not a location:

      >>> getSchoolBellApplication("string")
      Traceback (most recent call last):
      ...
      ValueError: can't get a SchoolBellApplication from 'string'

    """


def doctest_SortBy():
    """Tests for SortBy adapter.

        >>> from schoolbell.app.browser import SortBy
        >>> from zope.interface.verify import verifyObject
        >>> adapter = SortBy([])

        >>> from zope.app.traversing.interfaces import IPathAdapter
        >>> verifyObject(IPathAdapter, adapter)
        True

        >>> from zope.app.traversing.interfaces import ITraversable
        >>> verifyObject(ITraversable, adapter)
        True

    You can sort empty lists

        >>> adapter.traverse('name')
        []

    You can sort lists of dicts

        >>> a_list = [{'id': 42, 'title': 'How to get ahead in navigation'},
        ...           {'id': 11, 'title': 'The ultimate answer: 6 * 9'},
        ...           {'id': 33, 'title': 'Alphabet for beginners'}]
        >>> for item in SortBy(a_list).traverse('title'):
        ...     print item['title']
        Alphabet for beginners
        How to get ahead in navigation
        The ultimate answer: 6 * 9

    You can sort lists of objects by attribute

        >>> class SomeObject:
        ...     def __init__(self, name):
        ...         self.name = name
        >>> another_list = map(SomeObject, ['orange', 'apple', 'pear'])
        >>> for item in SortBy(another_list).traverse('name'):
        ...     print item.name
        apple
        orange
        pear

    You cannot mix and match objects and dicts in the same list, though.
    Also, if you specify the name of a method, SortBy will not call that
    method to get sort keys.

    You can sort arbitrary iterables, in fact:

        >>> import itertools
        >>> iterable = itertools.chain(another_list, another_list)
        >>> for item in SortBy(iterable).traverse('name'):
        ...     print item.name
        apple
        apple
        orange
        orange
        pear
        pear

    """


def doctest_NavigationView():
    """Unit tests for NavigationView.

    This view works for any ILocatable object within a SchoolBell instance.

      >>> from schoolbell.app.app import SchoolBellApplication, Person

      >>> p = Person()
      >>> app = SchoolBellApplication()
      >>> app['persons']['1'] = p

    It makes the application available as `view.app`:

      >>> from schoolbell.app.browser import NavigationView
      >>> view = NavigationView(p, None)
      >>> view.app is app
      True

    """

def doctest_SchoolBellSized():
    """Unit tests for SchoolBellSized.

      >>> from schoolbell.app.app import SchoolBellApplication
      >>> from schoolbell.app.browser import SchoolBellSized

      >>> app = SchoolBellApplication()
      >>> sized = SchoolBellSized(app)

      >>> sized.sizeForSorting(), sized.sizeForDisplay()
      (0, u'0 persons')

      >>> persons = app['persons']
      >>> persons['gintas'] = object()

      >>> sized.sizeForSorting(), sized.sizeForDisplay()
      (1, u'1 person')

      >>> persons['ignas'] = object()
      >>> persons['mg'] = object()

      >>> sized.sizeForSorting(), sized.sizeForDisplay()
      (3, u'3 persons')

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite())
    suite.addTest(doctest.DocTestSuite('schoolbell.app.browser'))
    suite.addTest(doctest.DocFileSuite('../templates.txt'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
