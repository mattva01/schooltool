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
from zope.interface import implements
from zope.testing import doctest
from zope.interface.verify import verifyObject
from zope.app.location.interfaces import ILocation


def doctest_SchoolBellAPI():
    r"""Tests for SchoolBellAPI.

        >>> from zope.tales.interfaces import ITALESFunctionNamespace
        >>> from schoolbell.app.browser import SchoolBellAPI
        >>> context = object()
        >>> ns = SchoolBellAPI(context)
        >>> verifyObject(ITALESFunctionNamespace, ns)
        True

    'context/schoolbell:app' returns the nearest ISchoolBellApplication

        >>> from schoolbell.app.app import SchoolBellApplication
        >>> from zope.app.component.hooks import setSite
        >>> from zope.app.component.site import LocalSiteManager
        >>> app = SchoolBellApplication()
        >>> app.setSiteManager(LocalSiteManager(app))
        >>> setSite(app)

        >>> SchoolBellAPI(app['persons']).app is app
        True

    It does so even for objects that do not adapt to
    ISchoolBellApplication, but are sublocations of SchoolBellApplication:

        >>> class Adding:
        ...     implements(ILocation)
        ...     __parent__ = app['persons']
        ...
        >>> adding = Adding()
        >>> SchoolBellAPI(adding).app is app
        True


    'context/schoolbell:person' adapts the context to IPerson:

        >>> from schoolbell.app.app import Person
        >>> p = Person()
        >>> SchoolBellAPI(p).person is p
        True
        >>> SchoolBellAPI(app).person is None
        True


    'context/schoolbell:authenticated' checks whether context is an
    authenticated principal

        >>> from zope.app.security.principalregistry \
        ...     import Principal, UnauthenticatedPrincipal
        >>> root = Principal('root', 'Admin', 'Supreme user', 'root', 'secret')
        >>> anonymous = UnauthenticatedPrincipal('anonymous', 'Anonymous',
        ...                             "Anyone who did not bother to log in")

        >>> SchoolBellAPI(root).authenticated
        True
        >>> SchoolBellAPI(anonymous).authenticated
        False

        >>> SchoolBellAPI(Person()).authenticated
        Traceback (most recent call last):
          ...
        TypeError: schoolbell:authenticated can only be applied to a principal

    """


def doctest_SortBy():
    """Tests for SortBy adapter.

        >>> from schoolbell.app.browser import SortBy
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


def doctest_SortBy_security():
    """Regression test for http://issues.schooltool.org/issue174

        >>> from zope.security.management import newInteraction
        >>> from zope.security.management import endInteraction
        >>> from zope.publisher.browser import TestRequest
        >>> endInteraction()
        >>> newInteraction(TestRequest())

    Fairly standard condition: a security wrapped object.

        >>> class SacredObj:
        ...     title = 'Ribbit!'
        >>> obj = SacredObj()

        >>> from zope.security.checker import NamesChecker
        >>> from zope.security.checker import ProxyFactory
        >>> checker = NamesChecker(['title'], 'schoolbell.View')
        >>> protected_obj = ProxyFactory(obj, checker)
        >>> a_list = [protected_obj]

    When we sort it, we should get Unauthorized for the 'title' attribute (as
    opposed to ForbiddenAttribute for '__getitem__', which will happen if
    hasattr hides the first error).

        >>> from schoolbell.app.browser import SortBy
        >>> list(SortBy(a_list).traverse('title'))  # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        Unauthorized: (<...SacredObj instance...>, 'title', 'schoolbell.View')

    Tear down:

        >>> endInteraction()

    """


def doctest_NavigationView():
    """Unit tests for NavigationView.

    This view works for any ILocatable object within a SchoolBell instance.

      >>> from schoolbell.app.app import SchoolBellApplication, Person
      >>> from zope.app.component.hooks import setSite
      >>> from zope.app.component.site import LocalSiteManager
      >>> app = SchoolBellApplication()
      >>> app.setSiteManager(LocalSiteManager(app))
      >>> setSite(app)
      >>> p = Person('1')
      >>> app['persons']['1'] = p

    It makes the application available as `view.app`:

      >>> from schoolbell.app.browser import NavigationView
      >>> view = NavigationView(p, None)
      >>> view.app is app
      True

    """

def doctest_SchoolBellSized():
    """Unit tests for SchoolBellSized.

      >>> from schoolbell.app.app import SchoolBellApplication, Person
      >>> from schoolbell.app.browser import SchoolBellSized

      >>> app = SchoolBellApplication()
      >>> sized = SchoolBellSized(app)

      >>> sized.sizeForSorting(), sized.sizeForDisplay()
      (0, u'0 persons')

      >>> persons = app['persons']
      >>> persons['gintas'] = Person(u'gintas')

      >>> sized.sizeForSorting(), sized.sizeForDisplay()
      (1, u'1 person')

      >>> persons['ignas'] = Person(u'ignas')
      >>> persons['marius'] = Person(u'marius')

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
