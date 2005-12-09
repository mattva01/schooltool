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
Unit tests for schooltool.attendance.

$Id$
"""
__docformat__ = 'reStructuredText'


import unittest
import datetime

from persistent import Persistent
from zope.interface import implements
from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.testing import setup
from zope.app.annotation.interfaces import IAnnotations
from zope.app.annotation.interfaces import IAttributeAnnotatable
import zope.component

import schooltool.app # Dead chicken to appease the circle of import gods
from schooltool.person.interfaces import IPerson
from schooltool.attendance.interfaces import ISectionAttendance
from schooltool.attendance.interfaces import ISectionAttendanceRecord
from schooltool.attendance.interfaces import UNKNOWN, PRESENT, ABSENT, TARDY
from schooltool.attendance.interfaces import AttendanceError


def doctest_SectionAttendance():
    """Test for SectionAttendance

        >>> from schooltool.attendance.attendance import SectionAttendance
        >>> sa = SectionAttendance()
        >>> verifyObject(ISectionAttendance, sa)
        True

        >>> isinstance(sa, Persistent)
        True

    """


class SectionStub(object):

    def __init__(self, title=None):
        self.title = title

    def __repr__(self):
        if self.title:
            return 'SectionStub(%r)' % self.title
        else:
            return 'SectionStub()'


def doctest_SectionAttendance_record():
    """Tests for SectionAttendance.record

        >>> from schooltool.attendance.attendance import SectionAttendance
        >>> sa = SectionAttendance()

        >>> len(list(sa))
        0

    Let's record a presence

        >>> section = SectionStub()
        >>> dt = datetime.datetime(2005, 12, 9, 13, 30)
        >>> duration = datetime.timedelta(minutes=45)
        >>> period_id = 'P1'
        >>> sa.record(section, dt, duration, period_id, True)

    We can check that it is there

        >>> len(list(sa))
        1

        >>> ar = sa.get(section, dt)
        >>> ar
        SectionAttendanceRecord(SectionStub(),
                                datetime.datetime(2005, 12, 9, 13, 30),
                                PRESENT)
        >>> ISectionAttendanceRecord.providedBy(ar)
        True

    It has all the data

        >>> ar.section is section
        True
        >>> ar.datetime == dt
        True
        >>> ar.duration == duration
        True
        >>> ar.period_id == period_id
        True
        >>> ar.status == PRESENT
        True

    Let's record an absence for the same section

        >>> dt = datetime.datetime(2005, 12, 9, 14, 30)
        >>> duration = datetime.timedelta(minutes=30)
        >>> period_id = 'P2'
        >>> sa.record(section, dt, duration, period_id, False)

    We can check that it is there

        >>> len(list(sa))
        2

        >>> ar = sa.get(section, dt)
        >>> ar.section is section
        True
        >>> ar.datetime == dt
        True
        >>> ar.duration == duration
        True
        >>> ar.period_id == period_id
        True
        >>> ar.status == ABSENT
        True

    Let's record a presence for another section at the same time

        >>> section2 = SectionStub()
        >>> sa.record(section2, dt, duration, period_id, True)

        >>> len(list(sa))
        3

        >>> ar = sa.get(section2, dt)
        >>> ar.section is section2
        True

    However we cannot override existing records

        >>> sa.record(section2, dt, duration, period_id, True)
        Traceback (most recent call last):
          ...
        AttendanceError: record for SectionStub() at 2005-12-09 14:30:00
                         already exists

    """


def doctest_SectionAttendance_get():
    """Tests for SectionAttendance.get

        >>> from schooltool.attendance.attendance import SectionAttendance
        >>> sa = SectionAttendance()

        >>> section1 = SectionStub()
        >>> section2 = SectionStub()
        >>> dt = datetime.datetime(2005, 12, 9, 13, 30)

    If you try to see the attendance record that has never been recorded, you
    get a "null object".

        >>> ar = sa.get(section1, dt)
        >>> ar
        SectionAttendanceRecord(SectionStub(),
                                datetime.datetime(2005, 12, 9, 13, 30),
                                UNKNOWN)
        >>> ISectionAttendanceRecord.providedBy(ar)
        True
        >>> ar.status == UNKNOWN
        True
        >>> ar.section == section1
        True
        >>> ar.datetime == dt
        True

    Most of the attributes do not make much sense

        >>> ar.duration
        datetime.timedelta(0)
        >>> ar.period_id

    Otherwise you get the correct record for a (section, datetime) pair.

        >>> dt1 = datetime.datetime(2005, 12, 9, 13, 30)
        >>> dt2 = datetime.datetime(2005, 12, 10, 13, 0)
        >>> duration = datetime.timedelta(minutes=50)
        >>> sa.record(section1, dt1, duration, 'P1', True)
        >>> sa.record(section2, dt1, duration, 'P2', False)
        >>> sa.record(section1, dt2, duration, 'P3', False)
        >>> sa.record(section2, dt2, duration, 'P4', True)

        >>> for dt in (dt1, dt2):
        ...     for section in (section1, section2):
        ...         ar = sa.get(section, dt)
        ...         assert ar.section == section
        ...         assert ar.datetime == dt
        ...         print ar.period_id, ar.isPresent()
        P1 True
        P2 False
        P3 False
        P4 True

    """


def doctest_SectionAttendance_getAllForDay():
    """Tests for SectionAttendance.getAllForDay

        >>> from schooltool.attendance.attendance import SectionAttendance
        >>> sa = SectionAttendance()

        >>> section1 = SectionStub('Math')
        >>> section2 = SectionStub('Chem')
        >>> dt1a = datetime.datetime(2005, 12, 5, 13, 30)
        >>> dt1b = datetime.datetime(2005, 12, 5, 15, 30)
        >>> dt2a = datetime.datetime(2005, 12, 7, 13, 30)
        >>> dt2b = datetime.datetime(2005, 12, 7, 15, 30)
        >>> dt3a = datetime.datetime(2005, 12, 9, 13, 30)
        >>> dt3b = datetime.datetime(2005, 12, 9, 15, 30)
        >>> duration = datetime.timedelta(minutes=45)

        >>> sa.record(section1, dt1a, duration, 'A', True)
        >>> sa.record(section1, dt2a, duration, 'A', True)
        >>> sa.record(section2, dt2a, duration, 'A', False)
        >>> sa.record(section1, dt2b, duration, 'B', False)
        >>> sa.record(section2, dt3a, duration, 'A', True)

        >>> def print_for(day):
        ...     def key(ar):
        ...         return (ar.datetime, ar.section.title)
        ...     for ar in sorted(sa.getAllForDay(day), key=key):
        ...         print ar.date, ar.period_id, ar.section.title, ar.isPresent()

        >>> print_for(dt1a.date())
        2005-12-05 A Math True

        >>> print_for(dt2a.date())
        2005-12-07 A Chem False
        2005-12-07 A Math True
        2005-12-07 B Math False

        >>> print_for(dt3a.date())
        2005-12-09 A Chem True

        >>> print_for(datetime.date(2005, 12, 4))

    """


def doctest_SectionAttendance_filter():
    """Tests for SectionAttendance.filter

        >>> from schooltool.attendance.attendance import SectionAttendance
        >>> sa = SectionAttendance()

        >>> section1 = SectionStub('Math')
        >>> section2 = SectionStub('Chem')
        >>> dt1a = datetime.datetime(2005, 12, 5, 13, 30)
        >>> dt1b = datetime.datetime(2005, 12, 5, 15, 30)
        >>> dt2a = datetime.datetime(2005, 12, 7, 13, 30)
        >>> dt2b = datetime.datetime(2005, 12, 7, 15, 30)
        >>> dt3a = datetime.datetime(2005, 12, 9, 13, 30)
        >>> dt3b = datetime.datetime(2005, 12, 9, 15, 30)
        >>> duration = datetime.timedelta(minutes=45)

        >>> sa.record(section1, dt1a, duration, 'A', True)
        >>> sa.record(section1, dt2a, duration, 'A', True)
        >>> sa.record(section2, dt2a, duration, 'A', False)
        >>> sa.record(section1, dt2b, duration, 'B', False)
        >>> sa.record(section2, dt3a, duration, 'A', True)

        >>> def print_for(first, last):
        ...     def key(ar):
        ...         return (ar.datetime, ar.section.title)
        ...     for ar in sorted(sa.filter(first, last), key=key):
        ...         print ar.date, ar.period_id, ar.section.title, ar.isPresent()

        >>> print_for(dt1a.date(), dt1a.date())
        2005-12-05 A Math True

        >>> print_for(dt1a.date(), dt2a.date())
        2005-12-05 A Math True
        2005-12-07 A Chem False
        2005-12-07 A Math True
        2005-12-07 B Math False

        >>> print_for(dt2a.date(), dt3a.date())
        2005-12-07 A Chem False
        2005-12-07 A Math True
        2005-12-07 B Math False
        2005-12-09 A Chem True

        >>> print_for(dt1a.date(), dt3a.date())
        2005-12-05 A Math True
        2005-12-07 A Chem False
        2005-12-07 A Math True
        2005-12-07 B Math False
        2005-12-09 A Chem True

        >>> print_for(dt3a.date(), dt1a.date())

    """


def doctest_SectionAttendanceRecord():
    r"""Tests for SectionAttendanceRecord

        >>> from schooltool.attendance.attendance \
        ...     import SectionAttendanceRecord

    Let's create an UNKNOWN record

        >>> section = SectionStub()
        >>> dt = datetime.datetime(2005, 11, 23, 14, 55)
        >>> ar = SectionAttendanceRecord(section, dt, UNKNOWN)
        >>> verifyObject(ISectionAttendanceRecord, ar)
        True

        >>> isinstance(ar, Persistent)
        True

        >>> ar.status == UNKNOWN
        True
        >>> ar.section == section
        True
        >>> ar.datetime == dt
        True
        >>> ar.date == dt.date()
        True

        >>> ar.duration
        datetime.timedelta(0)
        >>> ar.period_id is None
        True
        >>> ar.late_arrival is None
        True

    Let's create a regular record

        >>> section = SectionStub()
        >>> dt = datetime.datetime(2005, 11, 23, 14, 55)
        >>> duration = datetime.timedelta(minutes=45)
        >>> period_id = 'Period A'
        >>> ar = SectionAttendanceRecord(section, dt, PRESENT, duration,
        ...                              period_id)

        >>> ar.status == PRESENT
        True
        >>> ar.section == section
        True
        >>> ar.datetime == dt
        True
        >>> ar.date == dt.date()
        True
        >>> ar.duration == duration
        True
        >>> ar.period_id == period_id
        True

        >>> ar.late_arrival is None
        True

    """


def doctest_SectionAttendanceRecord_isUnknown_isPresent_isAbsent_isTardy():
    r"""Tests for SectionAttendanceRecord.isSomething functions

        >>> from schooltool.attendance.attendance \
        ...     import SectionAttendanceRecord

        >>> section = SectionStub()
        >>> dt = datetime.datetime(2005, 11, 23, 14, 55)
        >>> for status in (UNKNOWN, PRESENT, ABSENT, TARDY):
        ...     ar = SectionAttendanceRecord(section, dt, status)
        ...     print "%-7s %-5s %-5s %-5s %-5s" % (ar.status,
        ...                 ar.isUnknown(), ar.isPresent(), ar.isAbsent(),
        ...                 ar.isTardy())
        UNKNOWN True  False False False
        PRESENT False True  False False
        ABSENT  False False True  False
        TARDY   False False False True

    """


def doctest_SectionAttendanceRecord_makeTardy():
    r"""Tests for SectionAttendanceRecord.makeTardy

        >>> from schooltool.attendance.attendance \
        ...     import SectionAttendanceRecord

    If you have an absence

        >>> section = SectionStub()
        >>> dt = datetime.datetime(2005, 11, 23, 14, 55)
        >>> ar = SectionAttendanceRecord(section, dt, ABSENT)

    you can convert it to a tardy

        >>> ar.makeTardy(datetime.time(15, 03))

        >>> ar.isTardy()
        True
        >>> ar.late_arrival
        datetime.time(15, 3)

    In all other cases you can't.

        >>> for status in (UNKNOWN, PRESENT, TARDY):
        ...     ar = SectionAttendanceRecord(section, dt, status)
        ...     try:
        ...         ar.makeTardy(datetime.time(15, 03))
        ...     except AttendanceError:
        ...         pass
        ...     else:
        ...         print "no AttendanceError when status=%s" % status

    """


class PersonStub(object):
    implements(IPerson, IAttributeAnnotatable)


def doctest_getSectionAttendance():
    """Tests for getSectionAttendance.

        >>> setup.placelessSetUp()
        >>> setup.setUpAnnotations()
        >>> from schooltool.attendance.attendance import getSectionAttendance
        >>> zope.component.provideAdapter(getSectionAttendance,
        ...                               [IPerson], ISectionAttendance)

    getSectionAttendance lets us get ISectionAttendance for a person

        >>> person = PersonStub()
        >>> attendance = ISectionAttendance(person)
        >>> attendance
        <schooltool.attendance.attendance.SectionAttendance object at ...>

    The attendance object is stored in person's annotations

        >>> annotations = IAnnotations(person)
        >>> attendance is annotations['schooltool.attendance.SectionAttendance']
        True

    If you adapt more than once, you will get the same object

        >>> attendance is ISectionAttendance(person)
        True

        >>> setup.placelessTearDown()

    """


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
