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

$Id: test_app.py 4691 2005-08-12 18:59:44Z srichter $
"""
import unittest

from zope.interface.verify import verifyObject
from zope.testing import doctest

from schoolbell.app.tests.test_app import run_unit_tests

def doctest_ResourceContainer():
    """Tests for ResourceContainer

        >>> from schoolbell.app.resource.interfaces import IResourceContainer
        >>> from schoolbell.app.resource.resource import ResourceContainer
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

        >>> from schoolbell.app.resource.interfaces import IResourceContained
        >>> from schoolbell.app.resource.resource import Resource
        >>> resource = Resource()
        >>> verifyObject(IResourceContained, resource)
        True

    Resources can have titles and descriptions too

        >>> blender = Resource(title='Blender', description="It's broken.")
        >>> blender.title
        'Blender'
        >>> blender.description
        "It's broken."

    Resources can be tagged as locations, the default is false:

        >>> blender.isLocation
        False

    """

def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
