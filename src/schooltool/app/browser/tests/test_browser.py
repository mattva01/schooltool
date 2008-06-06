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
Tests for schooltool views.

$Id$
"""
import unittest

from zope.interface import implements
from zope.testing import doctest
from zope.interface.verify import verifyObject
from zope.location.interfaces import ILocation
from zope.app.testing import ztapi, setup
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.dependable.interfaces import IDependable
from zope.i18n import translate
from zope.traversing.interfaces import ITraversable, IPathAdapter

from schooltool.app.browser.testing import setUp, tearDown
from schooltool.testing import setup as sbsetup


class SomeAnnotatable(object):
    implements(IAttributeAnnotatable)


def doctest_SchoolToolAPI():
    r"""Tests for SchoolToolAPI.

        >>> from zope.tales.interfaces import ITALESFunctionNamespace
        >>> from schooltool.app.browser import SchoolToolAPI
        >>> context = object()
        >>> ns = SchoolToolAPI(context)
        >>> verifyObject(ITALESFunctionNamespace, ns)
        True

    """


def doctest_SchoolToolAPI_aap():
    r"""Tests for SchoolToolAPI.app.

    'context/schooltool:app' returns the nearest ISchoolToolApplication

        >>> app = sbsetup.setUpSchoolToolSite()

        >>> from schooltool.app.browser import SchoolToolAPI
        >>> SchoolToolAPI(app['persons']).app is app
        True

    It does so even for objects that do not adapt to ISchoolToolApplication,
    but are sublocations of SchoolToolApplication:

        >>> class Adding:
        ...     implements(ILocation)
        ...     __parent__ = app['persons']
        ...
        >>> adding = Adding()
        >>> SchoolToolAPI(adding).app is app
        True

    """


def doctest_SchoolToolAPI_preferences():
    r"""Tests for SchoolToolAPI.preferences.

        >>> setup.setUpAnnotations()
        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> from schooltool.app.app import getApplicationPreferences
        >>> ztapi.provideAdapter(ISchoolToolApplication,
        ...                      IApplicationPreferences,
        ...                      getApplicationPreferences)

    'context/schooltool:preferences' returns an ApplicationPreferences object
    for the nearest ISchoolToolApplication

        >>> from schooltool.app.browser import SchoolToolAPI
        >>> app = sbsetup.setUpSchoolToolSite()
        >>> preferences = SchoolToolAPI(app).preferences
        >>> preferences.title
        u'Your School'

        >>> preferences is SchoolToolAPI(app['persons']).preferences
        True

    """


def doctest_SchoolToolAPI_person():
    r"""Tests for SchoolToolAPI.person.

    'context/schooltool:person' adapts the context to IPerson:

        >>> from schooltool.app.browser import SchoolToolAPI
        >>> from schooltool.person.person import Person
        >>> p = Person()

        >>> SchoolToolAPI(p).person is p
        True
        >>> SchoolToolAPI(None).person is None
        True

    """


def doctest_SchoolToolAPI_authenticated():
    r"""Tests for SchoolToolAPI.authenticated.

    'context/schooltool:authenticated' checks whether context is an
    authenticated principal

        >>> from zope.app.security.principalregistry \
        ...     import Principal, UnauthenticatedPrincipal
        >>> root = Principal('root', 'Admin', 'Supreme user', 'root', 'secret')
        >>> anonymous = UnauthenticatedPrincipal('anonymous', 'Anonymous',
        ...                             "Anyone who did not bother to log in")

        >>> from schooltool.app.browser import SchoolToolAPI
        >>> SchoolToolAPI(root).authenticated
        True
        >>> SchoolToolAPI(anonymous).authenticated
        False

        >>> from schooltool.person.person import Person
        >>> SchoolToolAPI(Person()).authenticated
        ... # doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS
        Traceback (most recent call last):
          ...
        TypeError: schooltool:authenticated can only be applied to a principal
        but was applied on <schooltool.person.person.Person object at ...>

    """


def doctest_SchoolToolAPI_has_dependents():
    r"""Tests for SchoolToolAPI.has_dependents.

        >>> from schooltool.app.browser import SchoolToolAPI

        >>> obj = object()
        >>> SchoolToolAPI(obj).has_dependents
        False

        >>> obj = SomeAnnotatable()
        >>> SchoolToolAPI(obj).has_dependents
        False

        >>> IDependable(obj).addDependent('foo')
        >>> SchoolToolAPI(obj).has_dependents
        True

    """


def doctest_SortBy():
    """Tests for SortBy adapter.

        >>> from schooltool.app.browser import SortBy
        >>> adapter = SortBy([])

        >>> verifyObject(IPathAdapter, adapter)
        True
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


def doctest_CanAccess():
    """Tests for CanAccess adapter.

        >>> from schooltool.app.browser import CanAccess
        >>> context = object()

    Let's create the adapter:

        >>> adapter = CanAccess(context)
        >>> adapter.context is context
        True

    The adapter's traverse() method simply calls canAccess on the context.
    Its functionality is tested in functional tests already and is too much
    trouble to unit test, so we just check the interface:

        >>> verifyObject(ITraversable, adapter)
        True
        >>> verifyObject(IPathAdapter, adapter)
        True

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
        >>> checker = NamesChecker(['title'], 'schooltool.View')
        >>> protected_obj = ProxyFactory(obj, checker)
        >>> a_list = [protected_obj]

    When we sort it, we should get Unauthorized for the 'title' attribute (as
    opposed to ForbiddenAttribute for '__getitem__', which will happen if
    hasattr hides the first error).

        >>> from schooltool.app.browser import SortBy
        >>> list(SortBy(a_list).traverse('title'))  # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        Unauthorized: (<...SacredObj instance...>, 'title', 'schooltool.View')

    Tear down:

        >>> endInteraction()

    """

def doctest_SchoolToolSized():
    """Unit tests for SchoolToolSized.

      >>> from schooltool.app.browser import SchoolToolSized
      >>> from schooltool.person.person import Person

      >>> app = sbsetup.setUpSchoolToolSite()
      >>> sized = SchoolToolSized(app)

      >>> sized.sizeForSorting(), translate(sized.sizeForDisplay())
      ((u'Persons', 0), u'0 persons')

      >>> persons = app['persons']
      >>> persons['gintas'] = Person(u'gintas')

      >>> sized.sizeForSorting(), translate(sized.sizeForDisplay())
      ((u'Persons', 1), u'1 person')

      >>> persons['ignas'] = Person(u'ignas')
      >>> persons['marius'] = Person(u'marius')

      >>> sized.sizeForSorting(), translate(sized.sizeForDisplay())
      ((u'Persons', 3), u'3 persons')

    """


def doctest_ViewPrefences():
    r"""Unit tests for ViewPreferences.

        >>> from zope.publisher.browser import TestRequest

        >>> from schooltool.app.browser import ViewPreferences
        >>> from schooltool.person.interfaces import IPerson
        >>> from schooltool.person.interfaces import IPersonPreferences
        >>> import calendar
        >>> class PreferenceStub:
        ...     weekstart = calendar.MONDAY
        ...     timeformat = "%H:%M"
        ...     dateformat = "%Y-%m-%d"
        ...     timezone = 'UTC'
        >>> class PersonStub:
        ...     def __conform__(self, interface):
        ...         if interface is IPersonPreferences:
        ...             return PreferenceStub()
        >>> class PrincipalStub:
        ...     def __conform__(self, interface):
        ...         if interface is IPerson:
        ...             return PersonStub()
        >>> request = TestRequest()
        >>> request.setPrincipal(PrincipalStub())
        >>> prefs = ViewPreferences(request)
        >>> from datetime import datetime
        >>> prefs.timezone.tzname(datetime.utcnow())
        'UTC'
        >>> prefs.timeformat
        '%H:%M'
        >>> prefs.dateformat
        '%Y-%m-%d'
        >>> prefs.first_day_of_week
        0
        >>> from pytz import utc
        >>> prefs.renderDatetime(datetime(2005, 1, 7, 14, 15, tzinfo=utc))
        '2005-01-07 14:15'
        
    We have no principal (anonymous user) and no SchoolTool site (test
    environment):

        >>> request = TestRequest()
        >>> prefs = ViewPreferences(request)
        >>> from datetime import datetime
        >>> prefs.timezone.tzname(datetime.utcnow())
        'UTC'
        >>> prefs.timeformat
        '%H:%M'
        >>> prefs.dateformat
        '%Y-%m-%d'
        >>> prefs.first_day_of_week
        0

    Let's set up a SchoolTool site:

        >>> setup.setUpAnnotations()
        >>> from schooltool.app.app import getApplicationPreferences
        >>> app = sbsetup.setUpSchoolToolSite()
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> ztapi.provideAdapter(ISchoolToolApplication,
        ...                      IApplicationPreferences,
        ...                      getApplicationPreferences)
        >>> aprefs = IApplicationPreferences(app)
        >>> aprefs.timezone = 'Europe/Moscow'
        >>> aprefs.dateformat = '%m/%d/%y'
        >>> aprefs.timeformat = '%I:%M %p'
        >>> aprefs.weekstart = calendar.SUNDAY
        >>> request = TestRequest()
        >>> prefs = ViewPreferences(request)
        >>> prefs.timezone.tzname(datetime.utcnow())
        'MMT'
        >>> prefs.timeformat
        '%I:%M %p'
        >>> prefs.dateformat
        '%m/%d/%y'
        >>> prefs.first_day_of_week
        6
    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown))
    suite.addTest(doctest.DocTestSuite('schooltool.app.browser'))
    suite.addTest(doctest.DocFileSuite('../templates.txt'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
