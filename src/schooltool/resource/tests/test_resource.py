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
Unit tests for resources

$Id$
"""
import unittest

from zope.interface.verify import verifyObject
from zope.testing import doctest

from schooltool.testing.util import run_unit_tests

def doctest_ResourceContainer():
    """Tests for ResourceContainer

        >>> from schooltool.resource.interfaces import IResourceContainer
        >>> from schooltool.resource.resource import ResourceContainer
        >>> c = ResourceContainer()
        >>> verifyObject(IResourceContainer, c)
        True

    Let's make sure it acts like a proper container should act

        >>> from zope.app.container.tests.test_btree import TestBTreeContainer
        >>> class Test(TestBTreeContainer):
        ...    def makeTestObject(self):
        ...        return ResourceContainer()
        >>> run_unit_tests(Test)
    """


def doctest_Resource():
    r"""Tests for Resource

        >>> from schooltool.resource.interfaces import IResource
        >>> from schooltool.resource.resource import Resource
        >>> resource = Resource()
        >>> verifyObject(IResource, resource)
        True

    Resources can have titles and descriptions too

        >>> blender = Resource(title='Blender', description="It's broken.")
        >>> blender.title
        'Blender'
        >>> blender.description
        "It's broken."

        >>> blender.notes
        u''

    """

def doctest_Location():
    r"""Test for Location

        >>> from schooltool.resource.interfaces import ILocation
        >>> from schooltool.resource.resource import Location
        >>> room = Location()
        >>> verifyObject(ILocation, room)
        True

    Locations have several standard peices of information associated with
    them:

        >>> room.capacity

    """

def doctest_Equipment():
    r"""Test for Equipment

        >>> from schooltool.resource.interfaces import IEquipment
        >>> from schooltool.resource.resource import Equipment
        >>> projector = Equipment()
        >>> verifyObject(IEquipment, projector)
        True

    In addition to standard attributes, equipment also has the following
    attributes:

        >>> projector.manufacturer
        u''
        >>> projector.model
        u''
        >>> projector.serialNumber
        u''
        >>> projector.purchaseDate
    """

def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
