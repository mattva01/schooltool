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
Unit tests for schooltool.generations.evolve18

$Id$
"""

import unittest

from zope.app.testing import setup
from zope.app.component.interfaces import ISite
from zope.location.interfaces import ILocation
from zope.testing import doctest
from zope.interface import implements, directlyProvides

from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication


class AppStub(object):
    implements(ISchoolToolApplication, ILocation)
    __parent__ = None
    __name__ = None


def doctest_evolve():
    r"""Doctest for evolution to generation 18.

      >>> context = ContextStub()
      >>> context.root_folder['app'] = app = AppStub()
      >>> from zope.traversing.interfaces import IContainmentRoot
      >>> from zope.app.component.interfaces import ISite
      >>> directlyProvides(app, IContainmentRoot, ISite)

      >>> from schooltool.generations.evolve18 import evolve
      >>> evolve(context)

      >>> IContainmentRoot.providedBy(app)
      False

      >>> ISite.providedBy(app)
      True

    """

def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()

def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
