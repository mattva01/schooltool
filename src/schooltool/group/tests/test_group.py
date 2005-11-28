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
Unit tests for groups

$Id: test_app.py 4691 2005-08-12 18:59:44Z srichter $
"""

import unittest

from zope.interface.verify import verifyObject
from zope.testing import doctest

from schooltool.testing.util import run_unit_tests


def doctest_GroupContainer():
    """Tests for GroupContainer

        >>> from schooltool.group.interfaces import IGroupContainer
        >>> from schooltool.group.group import GroupContainer
        >>> c = GroupContainer()
        >>> verifyObject(IGroupContainer, c)
        True

    Let's make sure it acts like a proper container should act

        >>> from zope.app.container.tests.test_btree import TestBTreeContainer
        >>> class Test(TestBTreeContainer):
        ...    def makeTestObject(self):
        ...        return GroupContainer()
        >>> run_unit_tests(Test)
    """


def doctest_Group():
    r"""Tests for Group

        >>> from schooltool.group.interfaces import IGroupContained
        >>> from schooltool.group.group import Group
        >>> group = Group()
        >>> verifyObject(IGroupContained, group)
        True

    Groups can have titles and descriptions too

        >>> illuminati = Group(title='Illuminati', description='Secret Group')
        >>> illuminati.title
        'Illuminati'
        >>> illuminati.description
        'Secret Group'
    """


def doctest_addGroupContainerToApplication():
    """Tests for addGroupContainerToApplication

        >>> from schooltool.group.group import addGroupContainerToApplication
        >>> from schooltool.app.app import SchoolToolApplication
        >>> from zope.app.container.contained import ObjectAddedEvent
        >>> app = SchoolToolApplication()
        >>> event = ObjectAddedEvent(app)
        >>> addGroupContainerToApplication(event)
        >>> app['groups']
        <schooltool.group.group.GroupContainer object at ...>
        >>> group = app['groups']['manager']
        >>> group.title
        u'Manager'
        >>> group.description
        u'Manager Group.'

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
