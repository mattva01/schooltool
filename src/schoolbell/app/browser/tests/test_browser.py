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
from zope.app.tests import setup, ztapi
from zope.interface import implements, directlyProvides
from zope.app.traversing.interfaces import IContainmentRoot
from zope.publisher.browser import TestRequest


def doctest_getSchoolBellApplication():
    """Tests for ContainerView.

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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
