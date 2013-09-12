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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Unit tests for groups
"""
import unittest
import doctest

from zope.interface import directlyProvides
from zope.interface.verify import verifyObject
from zope.app.testing import setup
from zope.traversing.interfaces import IContainmentRoot
from zope.interface import implements

from schooltool.testing.util import run_unit_tests
from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IAsset


def doctest_GroupContainer():
    """Tests for GroupContainer

        >>> from schooltool.group.interfaces import IGroupContainer
        >>> from schooltool.group.group import GroupContainer
        >>> c = GroupContainer()
        >>> verifyObject(IGroupContainer, c)
        True

    Let's make sure it acts like a proper container should act

        >>> from zope.container.tests.test_btree import TestBTreeContainer
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


def doctest_GroupInit():
    """Tests for GroupInit

    This test needs annotations, dependencies and traversal

        >>> setup.placelessSetUp()
        >>> setup.setUpAnnotations()
        >>> setup.setUpDependable()
        >>> setup.setUpTraversal()

        >>> from schooltool.group.group import GroupInit
        >>> from schooltool.app.app import SchoolToolApplication
        >>> app = SchoolToolApplication()

    we want app to have a location

        >>> directlyProvides(app, IContainmentRoot)

    When you call the initialization adapter

        >>> plugin = GroupInit(app)
        >>> plugin()

    it adds a container for groups

        >>> app['schooltool.group']
        <schooltool.group.group.GroupContainerContainer object at ...>

    Clean up

        >>> setup.placelessTearDown()

    """


def doctest_GroupCalendarViewersCrowd():
    """Tests for ConfigurableCrowd.

    Some setup:

        >>> setup.placelessSetUp()

        >>> setting = True
        >>> class CustomisationsStub(object):
        ...     implements(IAccessControlCustomisations)
        ...     def get(self, key):
        ...         print 'Getting %s' % key
        ...         return setting

        >>> class PersonsStub(object):
        ...     super_user = None

        >>> class AppStub(object):
        ...     implements(ISchoolToolApplication)
        ...     def __conform__(self, iface):
        ...         if iface == IAccessControlCustomisations:
        ...             return CustomisationsStub()
        ...     def __getitem__(self, name):
        ...         if name == 'persons':
        ...             return PersonsStub()

        >>> from zope.component import provideAdapter
        >>> provideAdapter(lambda context: AppStub(),
        ...                adapts=[None],
        ...                provides=ISchoolToolApplication)

        >>> member_of = ()
        >>> from schooltool.person.interfaces import IPerson
        >>> class PrincipalStub(object):
        ...     def __init__(self, name):
        ...         self.name = name
        ...     def __conform__(self, iface):
        ...         if iface == IPerson: return "IPerson(%s)" % self.name
        ...     class groups(object):
        ...         def __contains__(self, item):
        ...             print "Checking for membership in group %s" % item
        ...             return item in member_of
        ...     groups = groups()

        >>> from schooltool.group.group import GroupCalendarViewersCrowd

    Off we go:

        >>> group_val = True
        >>> leader_val = True
        >>> class GroupStub(object):
        ...     implements(IAsset)
        ...     class members(object):
        ...         def __contains__(self, item):
        ...             print "Checking for membership of %s in a group" % item
        ...             return group_val
        ...     members = members()
        ...     class leaders(object):
        ...         def __contains__(self, item):
        ...             print "Checking for leadership of %s in a group" % item
        ...             return leader_val
        ...     leaders = leaders()

        >>> crowd = GroupCalendarViewersCrowd(GroupStub())
        >>> crowd.contains("Principal")
        Getting everyone_can_view_group_calendar
        True

    If setting is set to False, we should still check for membership:

        >>> setting = False
        >>> crowd.contains(PrincipalStub("Principal"))
        Getting everyone_can_view_group_calendar
        Checking for membership of IPerson(Principal) in a group
        True

    If membership fails, we check leadership:

        >>> group_val = False
        >>> crowd.contains(PrincipalStub("Principal"))
        Getting everyone_can_view_group_calendar
        Checking for membership of IPerson(Principal) in a group
        Checking for leadership of IPerson(Principal) in a group
        True

    If leadership fails, check for membership in system groups

        >>> leader_val = False
        >>> crowd.contains(PrincipalStub("Principal"))
        Getting everyone_can_view_group_calendar
        Checking for membership of IPerson(Principal) in a group
        Checking for leadership of IPerson(Principal) in a group
        Checking for membership in group sb.group.administrators
        Checking for membership in group sb.group.manager
        Checking for membership in group sb.group.clerks
        False

    Add to administrators

        >>> member_of = ['sb.group.administrators']
        >>> crowd.contains(PrincipalStub("Principal"))
        Getting everyone_can_view_group_calendar
        Checking for membership of IPerson(Principal) in a group
        Checking for leadership of IPerson(Principal) in a group
        Checking for membership in group sb.group.administrators
        True

    Clean up

        >>> setup.placelessTearDown()

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
