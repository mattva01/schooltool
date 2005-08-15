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
Unit tests for schoolbell.app.app.

$Id$
"""

import unittest

from zope.testing import doctest
from zope.component import provideAdapter
from zope.interface.verify import verifyObject
from zope.interface import directlyProvides
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.testing import setup, placelesssetup


def doctest_SchoolBellApplication():
    r"""Tests for SchoolBellApplication.

        >>> from schoolbell.app.app import SchoolBellApplication
        >>> app = SchoolBellApplication()

        >>> from schoolbell.app.group.group import GroupContainer
        >>> app['groups'] = GroupContainer()
        >>> from schoolbell.app.person.person import PersonContainer
        >>> app['persons'] = PersonContainer()
        >>> from schoolbell.app.resource.resource import ResourceContainer
        >>> app['resources'] = ResourceContainer()

    We need to register an adapter to make the title attribute available:

        >>> placelesssetup.setUp()
        >>> from schoolbell.app.app import ApplicationPreferences
        >>> from schoolbell.app.interfaces import IApplicationPreferences
        >>> provideAdapter(ApplicationPreferences,
        ...                provides=IApplicationPreferences)

        >>> from schoolbell.app.interfaces import ISchoolBellApplication
        >>> verifyObject(ISchoolBellApplication, app)
        True

        >>> placelesssetup.tearDown()

    Person, group and resource containers are reachable as items of the
    application object.

        >>> from schoolbell.app.person.interfaces import IPersonContainer
        >>> persons = app['persons']
        >>> verifyObject(IPersonContainer, persons)
        True

        >>> from schoolbell.app.group.interfaces import IGroupContainer
        >>> groups = app['groups']
        >>> verifyObject(IGroupContainer, groups)
        True

        >>> from schoolbell.app.resource.interfaces import IResourceContainer
        >>> resources = app['resources']
        >>> verifyObject(IResourceContainer, resources)
        True

    For Zopeish reasons these containers must know where they come from

        >>> persons.__parent__ is app
        True
        >>> persons.__name__
        u'persons'

        >>> groups.__parent__ is app
        True
        >>> groups.__name__
        u'groups'

        >>> resources.__parent__ is app
        True
        >>> resources.__name__
        u'resources'

    SchoolBellApplication is also a calendar owner:

        >>> from schoolbell.app.interfaces import ICalendarOwner
        >>> verifyObject(ICalendarOwner, app)
        True

    and naturally has a calendar attribute:

        >>> app.calendar
        <schoolbell.app.cal.Calendar object at ...

    """


def doctest_getSchoolBellApplication():
    """Tests for getSchoolBellApplication.

    Let's say we have a SchoolBell app.

      >>> from schoolbell.app.app import SchoolBellApplication
      >>> from schoolbell.app.person.person import Person
      >>> from zope.app.component.site import LocalSiteManager
      >>> app = SchoolBellApplication()
      >>> app.setSiteManager(LocalSiteManager(app))

    If site is not a SchoolBellApplication, we get an error

      >>> from schoolbell.app.app import getSchoolBellApplication
      >>> getSchoolBellApplication()
      Traceback (most recent call last):
      ...
      ValueError: can't get a SchoolBellApplication

    If current site is a SchoolBellApplication, we get it:

      >>> from zope.app.component.hooks import setSite
      >>> setSite(app)

      >>> getSchoolBellApplication() is app
      True
    """


def doctest_getApplicationPreferences():
    """Tests for getApplicationPreferences.

    We need a SchoolBell application and some setup for Annotations.

      >>> from zope.app.tests import setup
      >>> setup.setUpAnnotations()
      >>> from schoolbell.app.app import SchoolBellApplication
      >>> app = SchoolBellApplication()

    Now we can get the preferences object.

      >>> from schoolbell.app.app import getApplicationPreferences
      >>> prefs = getApplicationPreferences(app)
      >>> prefs
      <schoolbell.app.app.ApplicationPreferences...

    """


def run_unit_tests(testcase):
    r"""Hack to call into unittest from doctests.

        >>> import unittest
        >>> class SampleTestCase(unittest.TestCase):
        ...     def test1(self):
        ...         self.assertEquals(2 + 2, 4)
        >>> run_unit_tests(SampleTestCase)

        >>> class BadTestCase(SampleTestCase):
        ...     def test2(self):
        ...         self.assertEquals(2 * 2, 5)
        >>> run_unit_tests(BadTestCase) # doctest: +REPORT_NDIFF
        .F
        ======================================================================
        FAIL: test2 (schoolbell.app.tests.test_app.BadTestCase)
        ----------------------------------------------------------------------
        Traceback (most recent call last):
        ...
        AssertionError: 4 != 5
        <BLANKLINE>
        ----------------------------------------------------------------------
        Ran 2 tests in ...s
        <BLANKLINE>
        FAILED (failures=1)

    """
    import unittest
    from StringIO import StringIO
    testsuite = unittest.makeSuite(testcase)
    output = StringIO()
    result = unittest.TextTestRunner(output).run(testsuite)
    if not result.wasSuccessful():
        print output.getvalue(),


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schoolbell.app.app'),
                doctest.DocTestSuite('schoolbell.app.membership'),
                doctest.DocTestSuite('schoolbell.app.overlay'),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
