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
Unit tests for schooltool.relationship.annotatable
"""

import unittest
import doctest

from zope.app.testing import setup
from zope.interface import implements
from zope.annotation.interfaces import IAttributeAnnotatable


def doctest_getRelationshipLinks():
    r"""Test for schooltool.relationship.annotatable.getRelationshipLinks.

    We need to set up Zope 3 annotations

        >>> setup.placelessSetUp()
        >>> setup.setUpAnnotations()

    We need to have an annotatable object

        >>> class SomeAnnotatable(object):
        ...     implements(IAttributeAnnotatable)

        >>> obj = SomeAnnotatable()

    Now we can check that a new LinkSet is created automatically

        >>> from schooltool.relationship.annotatable \
        ...         import getRelationshipLinks
        >>> linkset = getRelationshipLinks(obj)

        >>> from schooltool.relationship.interfaces import IRelationshipLinks
        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(IRelationshipLinks, linkset)
        True

    If you do it more than once, you will get the same link set

        >>> linkset is getRelationshipLinks(obj)
        True

    Cleanup

        >>> setup.placelessTearDown()

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
