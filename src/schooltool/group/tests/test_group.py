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

$Id$
"""

import unittest

from zope.interface import directlyProvides
from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.testing import setup, ztapi
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

    When you call the subscriber

        >>> plugin = GroupInit(app)
        >>> plugin()

    it adds a container for groups

        >>> app['groups']
        <schooltool.group.group.GroupContainer object at ...>

    and a few built-in groups

        >>> for name, group in sorted(app['groups'].items()):
        ...     print '%-15s %-25s %s' % (name, group.title, group.description)
        administrators  School Administrators     School Administrators.
        clerks          Clerks                    Clerks.
        manager         Site Managers             Manager Group.
        students        Students                  Students.
        teachers        Teachers                  Teachers.

    These new groups are required for the application to function properly.  To
    express that requirement we add explicit dependencies:

        >>> from zope.app.dependable.interfaces import IDependable
        >>> for group in app['groups'].values():
        ...     assert IDependable(group).dependents() == (u'/groups/',)

    Clean up

        >>> setup.placelessTearDown()

    """


def doctest_GroupInstructorsCrowd():
    """Tests for GroupInstructorsCrowd.

        >>> from schooltool.group.group import GroupInstructorsCrowd
        >>> from schooltool.person.interfaces import IPerson
        >>> from schooltool.relationship.interfaces import IRelationshipLinks
        >>> class SectionStub(object):
        ...     members = ['good_group']
        >>> section = SectionStub()
        >>> class PersonLinksStub(object): 
        ...     def getTargetsByRole(self, role, rel_type):
        ...         print 'Relation: %s of type %s' % (role, rel_type)
        ...         return [section] # person is instructor of the 'section'
        >>> class PersonStub(object):
        ...     def __conform__(self, it):
        ...         if it is IRelationshipLinks:
        ...             return PersonLinksStub()
        >>> class PrincipalStub(object):
        ...     def __conform__(self, it):
        ...         if it is IPerson:
        ...             return PersonStub()
        >>> principal = PrincipalStub()
        >>> gic = GroupInstructorsCrowd('bad_group')
        >>> gic.contains(principal)
        Relation: <URIObject Section> of type <URIObject Instruction>
        False
        >>> gic = GroupInstructorsCrowd('good_group')
        >>> gic.contains(principal)
        Relation: <URIObject Section> of type <URIObject Instruction>
        True
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

        >>> class AppStub(object):
        ...     implements(ISchoolToolApplication)
        ...     def __conform__(self, iface):
        ...         if iface == IAccessControlCustomisations:
        ...             return CustomisationsStub()

        >>> from zope.component import provideAdapter
        >>> provideAdapter(lambda context: AppStub(),
        ...                adapts=[None],
        ...                provides=ISchoolToolApplication)

        >>> from schooltool.group.group import GroupCalendarViewersCrowd

    Off we go:

        >>> group_val = True
        >>> leader_val = False
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

        >>> from schooltool.person.interfaces import IPerson
        >>> class PrincipalStub(object):
        ...     def __init__(self, name):
        ...         self.name = name
        ...     def __conform__(self, iface):
        ...         if iface == IPerson: return "IPerson(%s)" % self.name

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
        False

        >>> leader_val = True
        >>> crowd.contains(PrincipalStub("Principal"))
        Getting everyone_can_view_group_calendar
        Checking for membership of IPerson(Principal) in a group
        Checking for leadership of IPerson(Principal) in a group
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
