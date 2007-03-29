#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Unit tests for lyceum person views.

$Id$
"""
import unittest

from zope.app.testing import setup
from zope.testing import doctest


def doctest_GroupTimetableCalendarViewBase():
    """Tests for GroupTimetableCalendarViewBase.

        >>> from datetime import datetime
        >>> start_dt = datetime(2006, 1, 1, 5, 15)
        >>> end_dt = datetime(2006, 1, 5, 5, 15)
        >>> from lyceum.browser.group_calendar import GroupTimetableCalendarViewBase
        >>> class SomeGroupCalendarView(GroupTimetableCalendarViewBase):
        ...     def __init__(self, context, request):
        ...         self.context, self.request = context, request
        ...         self.timezone = "UTC"

        >>> members = []
        >>> class GroupStub(object):
        ...     @property
        ...     def members(self):
        ...         return members
        >>> class GroupCalendar(object):
        ...     def __init__(self):
        ...         self.__parent__ = GroupStub()
        >>> view = SomeGroupCalendarView(GroupCalendar(), None)

    If there are no memebers in the group - there are no timetable
    calendar events in this calendar:

        >>> list(view.getEvents(start_dt, end_dt))
        []

    Now if there are members, we take timetable source objects of
    these members and display all the events out of timetable source
    object calendars:

        >>> view.eventForDisplayFactory = lambda e: e
        >>> class STCalendarStub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...     def expand(self, start, end):
        ...         return ["%s event %s" % (self.title, i)
        ...                 for i in [start, end]]

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> class TimetableSourceSub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...     def __conform__(self, iface):
        ...         if iface == ISchoolToolCalendar:
        ...             return STCalendarStub(self.title)

        >>> class CTTStub(object):
        ...     def __init__(self, tt_event_sources):
        ...         self.tt_event_sources = tt_event_sources
        ...     def collectTimetableSourceObjects(self):
        ...         return self.tt_event_sources

        >>> from schooltool.timetable.interfaces import ICompositeTimetables
        >>> class MemberStub(object):
        ...     def __init__(self, *tt_event_sources):
        ...         self.composite_timetable = CTTStub(tt_event_sources)
        ...     def __conform__(self, iface):
        ...         if iface == ICompositeTimetables:
        ...             return self.composite_timetable

        >>> tt_sources = map(TimetableSourceSub, ["History", "Art", "English"])
        >>> members = [MemberStub(tt_sources[0], tt_sources[1]),
        ...            MemberStub(tt_sources[1], tt_sources[2])]
        >>> sorted(list(view.getEvents(start_dt, end_dt)))
        ['Art event 2006-01-01 05:15:00',
         'Art event 2006-01-05 05:15:00',
         'English event 2006-01-01 05:15:00',
         'English event 2006-01-05 05:15:00',
         'History event 2006-01-01 05:15:00',
         'History event 2006-01-05 05:15:00']

    """


def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
