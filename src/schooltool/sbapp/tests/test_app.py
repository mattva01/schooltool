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

from schooltool.testing import setup as sbsetup

def doctest_SchoolToolApplication():
    r"""Tests for SchoolToolApplication.

        >>> app = sbsetup.createSchoolToolApplication()

    We need to register an adapter to make the title attribute available:

        >>> placelesssetup.setUp()
        >>> from schoolbell.app.app import ApplicationPreferences
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> provideAdapter(ApplicationPreferences,
        ...                provides=IApplicationPreferences)

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> verifyObject(ISchoolToolApplication, app)
        True

    Person, group and resource containers are reachable as items of the
    application object.

        >>> from schooltool.person.interfaces import IPersonContainer
        >>> persons = app['persons']
        >>> verifyObject(IPersonContainer, persons)
        True

        >>> from schooltool.group.interfaces import IGroupContainer
        >>> groups = app['groups']
        >>> verifyObject(IGroupContainer, groups)
        True

        >>> from schooltool.resource.interfaces import IResourceContainer
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

    SchoolToolApplication is also a calendar owner:

        >>> setup.setUpAnnotations()
        >>> sbsetup.setupCalendaring()

        >>> from schooltool.app.interfaces import IHaveCalendar
        >>> verifyObject(IHaveCalendar, app)
        True

    and naturally can be adapted to ISchoolToolCalendar:

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> ISchoolToolCalendar(app)
        <schooltool.app.cal.Calendar object at ...

    Cleanup:

        >>> placelesssetup.tearDown()

    """


def doctest_getSchoolToolApplication():
    """Tests for getSchoolToolApplication.

    Let's say we have a SchoolBell app.

      >>> from schooltool.app.app import SchoolToolApplication
      >>> from schooltool.person.person import Person
      >>> from zope.app.component.site import LocalSiteManager
      >>> app = SchoolToolApplication()
      >>> app.setSiteManager(LocalSiteManager(app))

    If site is not a SchoolToolApplication, we get an error

      >>> from schooltool.app.app import getSchoolToolApplication
      >>> getSchoolToolApplication()
      Traceback (most recent call last):
      ...
      ValueError: can't get a SchoolToolApplication

    If current site is a SchoolToolApplication, we get it:

      >>> from zope.app.component.hooks import setSite
      >>> setSite(app)

      >>> getSchoolToolApplication() is app
      True
    """


def doctest_getApplicationPreferences():
    """Tests for getApplicationPreferences.

    We need a SchoolBell application and some setup for Annotations.

      >>> from zope.app.tests import setup
      >>> setup.setUpAnnotations()
      >>> from schooltool.app.app import SchoolToolApplication
      >>> app = SchoolToolApplication()

    Now we can get the preferences object.

      >>> from schoolbell.app.app import getApplicationPreferences
      >>> prefs = getApplicationPreferences(app)
      >>> prefs
      <schoolbell.app.app.ApplicationPreferences...

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schoolbell.app.app'),
                doctest.DocTestSuite('schooltool.app.membership'),
                doctest.DocTestSuite('schooltool.app.overlay'),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
