#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Unit tests for the schooltool.timetable.source module.

$Id$
"""
import unittest

from zope.app.testing import setup
from zope.testing import doctest
from schooltool.timetable.tests.test_timetable import ContentStub, Parent
from schooltool.timetable.interfaces import IOwnTimetables


def doctest_RelationshipTimetableSources(object):
    """Tests for RelationshipTimetableSources.

        >>> from schooltool.relationship.tests import setUpRelationships
        >>> site = setup.placefulSetUp(True)
        >>> setup.setUpAnnotations()
        >>> setUpRelationships()

        >>> from schooltool.app.membership import Membership
        >>> o1 = ContentStub()
        >>> o2 = Parent()
        >>> Membership(member=o1, group=o2)
        >>> o3 = Parent()
        >>> Membership(member=o2, group=o3)
        >>> o4 = Parent()
        >>> Membership(member=o2, group=o4)
        >>> o5 = Parent()
        >>> Membership(member=o1, group=o5)

        >>> from schooltool.timetable.interfaces import ITimetableSource
        >>> from zope.component import provideSubscriptionAdapter
        >>> from schooltool.timetable.source import MembershipTimetableSource
        >>> provideSubscriptionAdapter(MembershipTimetableSource,
        ...                            adapts=[None],
        ...                            provides=ITimetableSource)
        >>> from schooltool.timetable.source import OwnedTimetableSource
        >>> provideSubscriptionAdapter(OwnedTimetableSource,
        ...                            adapts=[None],
        ...                            provides=ITimetableSource)

        >>> mts = MembershipTimetableSource(o1)
        >>> l = mts.getTimetableSourceObjects()
        >>> sorted(l) == sorted([o2, o3, o4, o5])
        True

        >>> mts = MembershipTimetableSource(o2)
        >>> l = mts.getTimetableSourceObjects()
        >>> sorted(l) == sorted([o3, o4])
        True

    """


def doctest_OwnedTimetableSource():
    """Tests for OwnedTimetableSource

        >>> from schooltool.timetable.source import OwnedTimetableSource
        >>> from zope.interface import implements
        >>> class Timetables(object):
        ...     timetables = {}

        >>> class TTOwnerStub(object):
        ...     implements(IOwnTimetables)

        >>> owner = TTOwnerStub()
        >>> source = OwnedTimetableSource(owner)
        >>> source.getTimetableSourceObjects() == [owner]
        True

    """


def test_suite():
    return doctest.DocTestSuite(setUp=setup.placelessSetUp,
                                tearDown=setup.placelessTearDown,
                                optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF|
                                            doctest.NORMALIZE_WHITESPACE|
                                            doctest.REPORT_ONLY_FIRST_FAILURE)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
