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
Unit tests for schooltool.relationship

This module contains a `setUpRelationships` function that can be used in
unit test setup code to register an IRelationshipLinks adapter for IAnnotatable
objects.  There are also `setUp` and `tearDown` functions that perform the
necessary Zope 3 placeless setup that is needed to make annotations and
relationships work for IAttributeAnnotatable objects.

This module also contains some stub objects for use in tests (SomeObject and
SomeContained).

$Id$
"""

from zope.app.tests import setup
from zope.interface import implements
from zope.app.annotation.interfaces import IAttributeAnnotatable
from zope.app.container.contained import Contained


class SomeObject(object):
    """A simple annotatable object for tests."""

    implements(IAttributeAnnotatable)

    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return self._name


class SomeContained(SomeObject, Contained):
    """A simple annotatable contained object for tests."""


def setUp():
    """Set up for schooltool.relationship doctests.

    Calls Zope's placelessSetUp, sets up annotations and relationships.
    """
    setup.placelessSetUp()
    setup.setUpAnnotations()
    setUpRelationships()


def tearDown():
    """Tear down for schooltool.relationshp doctests."""
    setup.placelessTearDown()


def setUpRelationships():
    """Set up the adapter from IAnnotatable to IRelationshipLinks.

    This function is created for use in unit tests.  You should call
    zope.app.tests.setup.placelessSetUp before calling this function
    (and don't forget to call zope.app.tests.setup.placelessTearDown after
    you're done).  You should also call zope.app.tests.setup.setUpAnnotations
    to get a complete test fixture.
    """
    from zope.app.tests import ztapi
    from zope.app.annotation.interfaces import IAnnotatable
    from schooltool.relationship.interfaces import IRelationshipLinks
    from schooltool.relationship.annotatable import getRelationshipLinks
    ztapi.provideAdapter(IAnnotatable, IRelationshipLinks,
                         getRelationshipLinks)

