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
Unit tests for schooltool.generations.evolve16

$Id$
"""

import unittest

from zope.app.testing.setup import setUpAnnotations
from zope.annotation.interfaces import IAnnotatable
from zope.app.testing import setup
from zope.testing import doctest
from zope.interface import implements

from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.relationship.tests import setUpRelationships
from schooltool.person.person import Person
from schooltool.group.group import Group


class AppStub(dict):
    implements(ISchoolToolApplication, IAnnotatable)

    def __init__(self):
        groups = self['groups'] = {}
        groups['manager'] = Group('Managers')
        self['persons'] = {}


def doctest_evolve():
    r"""Doctest for evolution to generation 16.

    Create context:

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()
        >>> manager_group = app['groups']['manager']
        >>> print list(manager_group.members)
        []

    No effect if we have no manager user (for some reason...):

        >>> from schooltool.generations.evolve16 import evolve
        >>> evolve(context)
        >>> print list(manager_group.members)
        []

        >>> app['persons']['manager'] = manager = Person('manager')
        >>> evolve(context)
        >>> manager in manager_group.members
        True
    """


def setUp(test):
    setup.placelessSetUp()
    setUpAnnotations()
    setUpRelationships()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
